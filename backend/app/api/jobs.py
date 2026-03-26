from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.job import Job

router = APIRouter()


@router.get("/")
def list_jobs(
    repo: str | None = None,
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List jobs with optional filters."""
    query = db.query(Job).order_by(Job.created_at.desc())

    if repo:
        query = query.filter(Job.repo_full_name == repo)
    if status:
        query = query.filter(Job.status == status)

    total = query.count()
    jobs = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "jobs": [
            {
                "id": j.id,
                "celery_task_id": j.celery_task_id,
                "repo": j.repo_full_name,
                "pr_number": j.pr_number,
                "status": j.status,
                "error_message": j.error_message,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ],
    }
