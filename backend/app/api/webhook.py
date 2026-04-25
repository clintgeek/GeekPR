import json
import uuid

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.security import verify_webhook_signature
from app.tasks.analyze_pr import analyze_pr_task
from app.models.database import get_db
from app.models.job import Job

router = APIRouter()


@router.post("/github")
async def handle_github_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receives GitHub webhook events for pull_request actions.
    Validates the signature, enqueues the analysis task, and returns 202.
    """
    # 1. Verify signature
    payload_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_webhook_signature(payload_body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 2. Parse payload
    payload = json.loads(payload_body)

    # Only process opened or synchronized (new commits pushed) PRs
    action = payload.get("action")
    if action not in ("opened", "synchronize"):
        return {"message": f"Ignored action: {action}"}

    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    installation = payload.get("installation", {})

    repo_full_name = repo.get("full_name")
    pr_number = pr.get("number")
    pr_title = pr.get("title", "")
    installation_id = installation.get("id")

    if not all([repo_full_name, pr_number, installation_id]):
        raise HTTPException(status_code=400, detail="Missing required payload fields")

    # 3. Pre-generate a task ID so we can persist the Job record
    #    BEFORE the Celery task is enqueued.  This eliminates a race
    #    condition where the worker picks up the task before the DB
    #    row is visible, causing the task to run but never update
    #    job.status.
    task_id = str(uuid.uuid4())

    job = Job(
        celery_task_id=task_id,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        status="queued",
    )
    db.add(job)
    db.commit()

    # 4. Enqueue the Celery task with the known ID
    analyze_pr_task.apply_async(
        task_id=task_id,
        kwargs={
            "installation_id": installation_id,
            "repo_full_name": repo_full_name,
            "pr_number": pr_number,
            "pr_title": pr_title,
        },
    )

    # 5. Return immediately
    return {"message": "Analysis enqueued", "task_id": task_id}
