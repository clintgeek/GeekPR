from dataclasses import dataclass

import httpx
from github import Github, GithubIntegration

from app.core.config import settings


@dataclass
class GitHubAuth:
    """A PyGithub client plus the raw installation token.

    The token is kept alongside the client because fetching diffs via
    PyGithub requires raw httpx calls with an Authorization header —
    we can't coax it out of the client afterwards without poking at
    private attributes.
    """
    client: Github
    token: str


def get_github_client(installation_id: int) -> GitHubAuth:
    """
    Authenticate as a GitHub App installation.

    Returns both a PyGithub client and the raw installation access token;
    the token is needed for the REST diff endpoint which PyGithub doesn't
    wrap.
    """
    with open(settings.github_private_key_path, "r") as f:
        private_key = f.read()

    integration = GithubIntegration(
        integration_id=settings.github_app_id,
        private_key=private_key,
    )

    access_token = integration.get_access_token(installation_id).token
    return GitHubAuth(client=Github(access_token), token=access_token)


def get_pr_diff(auth: GitHubAuth, repo_full_name: str, pr_number: int) -> str:
    """
    Fetch the unified diff for a pull request via the REST API.

    Uses the `Accept: application/vnd.github.v3.diff` header against the
    PR's API URL, which returns the diff body directly under the
    installation token's auth. This works for both public and private
    repos. The previous implementation hit pr.diff_url, which is the
    public github.com URL — that returns a 302 to an S3 signed URL AND
    is unauthenticated, so private repos 404 and public repos return
    an empty body when follow_redirects isn't set.
    """
    pr = auth.client.get_repo(repo_full_name).get_pull(pr_number)
    response = httpx.get(
        pr.url,
        headers={
            "Accept": "application/vnd.github.v3.diff",
            "Authorization": f"Bearer {auth.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        follow_redirects=True,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.text


def post_review_comment(
    auth: GitHubAuth,
    repo_full_name: str,
    pr_number: int,
    file_path: str,
    line: int,
    body: str,
) -> None:
    """Post a review comment on a specific line of a PR."""
    pr = auth.client.get_repo(repo_full_name).get_pull(pr_number)
    commit = pr.get_commits().reversed[0]

    pr.create_review_comment(
        body=body,
        commit=commit,
        path=file_path,
        line=line,
    )


def format_review_comment(
    function_name: str,
    language: str,
    severity: str,
    issue_type: str,
    summary: str,
    suggested_fix: str | None,
    explanation: str,
    security_issues: list[str] | None = None,
) -> str:
    """Build a production-risk flag comment for the PR."""
    severity_emoji = {"critical": "🚨", "high": "🔴"}.get(severity.lower(), "🟡")
    issue_label = issue_type.replace("_", " ").title()

    comment = f"""## {severity_emoji} geekPR — {issue_label} ({severity.upper()})

**Function**: `{function_name}`

### What could go wrong
{summary}

### Why
{explanation}
"""

    if suggested_fix:
        comment += f"\n### Suggested fix\n```{language}\n{suggested_fix}\n```\n"

    if security_issues:
        comment += "\n### Static scanner flags\n"
        for issue in security_issues:
            comment += f"- {issue}\n"

    comment += "\n---\n*geekPR triages production risks only — style and complexity feedback is intentionally filtered out.*"
    return comment


# Marker embedded in every top-level geekPR comment so we can find and
# delete previous ones when a PR gets re-analyzed. Keeps the PR
# conversation to one current "all clear" instead of a stack per push.
ALL_CLEAR_MARKER = "<!-- geekpr:all-clear -->"


def format_all_clear_comment(
    analyzed_count: int,
    language_breakdown: dict[str, int],
) -> str:
    """Build the 'nothing to worry about' PR-level acknowledgement."""
    if language_breakdown:
        parts = ", ".join(f"{lang}: {n}" for lang, n in sorted(language_breakdown.items()))
        breakdown = f" ({parts})"
    else:
        breakdown = ""

    noun = "function" if analyzed_count == 1 else "functions"
    return (
        f"{ALL_CLEAR_MARKER}\n"
        f"## ✓ geekPR — No production risks found\n\n"
        f"Reviewed {analyzed_count} {noun}{breakdown}. All within acceptable "
        f"complexity, no security / crash / data-loss / concurrency / "
        f"correctness concerns flagged.\n\n"
        f"---\n"
        f"*geekPR flags only production-risk findings; style and complexity "
        f"feedback is intentionally filtered out. Disable per-repo in Settings "
        f"if the acknowledgement is noise.*"
    )


def clear_previous_all_clear_comments(
    auth: GitHubAuth,
    repo_full_name: str,
    pr_number: int,
) -> int:
    """Delete any prior 'all clear' comments we posted on this PR.

    Called before posting a fresh one so the PR conversation shows one
    current acknowledgement per push instead of a stacked history.
    Returns the number of comments deleted (useful for logging / tests).
    """
    issue = auth.client.get_repo(repo_full_name).get_issue(pr_number)
    deleted = 0
    for comment in issue.get_comments():
        if ALL_CLEAR_MARKER in (comment.body or ""):
            comment.delete()
            deleted += 1
    return deleted


def post_all_clear_comment(
    auth: GitHubAuth,
    repo_full_name: str,
    pr_number: int,
    analyzed_count: int,
    language_breakdown: dict[str, int],
) -> None:
    """Post a top-level 'no production risks found' comment.

    Top-level = issue comment (attached to the PR conversation), not a
    review comment (which lives on a specific line of a specific file).
    The all-clear is about the PR as a whole, so it belongs in the
    conversation.
    """
    clear_previous_all_clear_comments(auth, repo_full_name, pr_number)
    body = format_all_clear_comment(analyzed_count, language_breakdown)
    issue = auth.client.get_repo(repo_full_name).get_issue(pr_number)
    issue.create_comment(body)
