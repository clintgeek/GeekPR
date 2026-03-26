from app.tasks.celery_app import celery_app
from app.services.diff_analyzer import extract_changed_functions
from app.services.complexity import analyze_complexity
from app.services.security_scan import run_bandit_scan
from app.services.llm import request_refactor
from app.services.github_service import (
    get_github_client,
    get_pr_diff,
    post_review_comment,
    format_review_comment,
)
from app.models.database import SessionLocal
from app.models.review import Review
from app.models.repo_config import RepoConfig
from app.models.job import Job


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def analyze_pr_task(self, installation_id: int, repo_full_name: str, pr_number: int, pr_title: str):
    """
    The main Celery task. Runs the full pipeline:
    1. Fetch diff
    2. Extract functions
    3. Check complexity
    4. Run security scan
    5. Call LLM for flagged functions
    6. Post review comments
    7. Save results to DB
    """
    db = SessionLocal()

    try:
        # Update job status
        job = db.query(Job).filter_by(celery_task_id=self.request.id).first()
        if job:
            job.status = "processing"
            db.commit()

        # Load repo-specific config (or use defaults)
        repo_config = db.query(RepoConfig).filter_by(repo_full_name=repo_full_name).first()
        cc_threshold = repo_config.cc_threshold if repo_config else 10
        bandit_enabled = repo_config.bandit_enabled if repo_config else True
        llm_provider = repo_config.llm_provider if repo_config else None
        llm_model = repo_config.llm_model if repo_config else None
        auto_post = repo_config.auto_post if repo_config else True

        # 1. Get the diff from GitHub
        gh = get_github_client(installation_id)
        diff_text = get_pr_diff(gh, repo_full_name, pr_number)

        # 2. Extract changed functions
        functions = extract_changed_functions(diff_text)

        if not functions:
            if job:
                job.status = "complete"
                db.commit()
            return {"message": "No Python functions changed", "reviews": 0}

        reviews_posted = 0

        for func in functions:
            # 3. Check complexity
            complexity_results = analyze_complexity(func.source_code, threshold=cc_threshold)
            flagged = [r for r in complexity_results if r.is_flagged]

            if not flagged:
                continue

            # 4. Security scan (optional)
            security_issues = []
            if bandit_enabled:
                issues = run_bandit_scan(func.source_code)
                security_issues = [f"[{i.test_id}] {i.description} (severity: {i.severity})" for i in issues]

            # 5. Call the LLM
            for result in flagged:
                suggestion = request_refactor(
                    function_source=func.source_code,
                    complexity_score=result.score,
                    function_name=result.function_name,
                    provider=llm_provider,
                    model=llm_model,
                )

                # 6. Format and post comment
                comment_body = format_review_comment(
                    function_name=result.function_name,
                    complexity_score=result.score,
                    suggestion_summary=suggestion.summary,
                    refactored_code=suggestion.refactored_code,
                    explanation=suggestion.explanation,
                    priority=suggestion.priority,
                    security_issues=security_issues if security_issues else None,
                )

                if auto_post:
                    post_review_comment(
                        github_client=gh,
                        repo_full_name=repo_full_name,
                        pr_number=pr_number,
                        file_path=func.file_path,
                        line=func.start_line,
                        body=comment_body,
                    )

                # 7. Save to database
                review = Review(
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    pr_title=pr_title,
                    function_name=result.function_name,
                    file_path=func.file_path,
                    line_number=func.start_line,
                    complexity_score=result.score,
                    suggestion=comment_body,
                    priority=suggestion.priority,
                    status="posted" if auto_post else "pending",
                )
                db.add(review)
                reviews_posted += 1

        db.commit()

        # Update job status
        if job:
            job.status = "complete"
            db.commit()

        return {"message": f"Analyzed {len(functions)} functions", "reviews": reviews_posted}

    except Exception as exc:
        db.rollback()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)

    finally:
        db.close()
