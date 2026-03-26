from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.review import Review

router = APIRouter()


@router.get("/")
def list_reviews(
    repo: str | None = None,
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List reviews with optional filters."""
    query = db.query(Review).order_by(Review.created_at.desc())

    if repo:
        query = query.filter(Review.repo_full_name == repo)
    if status:
        query = query.filter(Review.status == status)

    total = query.count()
    reviews = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "reviews": [
            {
                "id": r.id,
                "repo": r.repo_full_name,
                "pr_number": r.pr_number,
                "pr_title": r.pr_title,
                "function_name": r.function_name,
                "file_path": r.file_path,
                "line_number": r.line_number,
                "complexity_score": r.complexity_score,
                "suggestion": r.suggestion,
                "priority": r.priority,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews
        ],
    }


@router.get("/{review_id}")
def get_review(review_id: int, db: Session = Depends(get_db)):
    """Get a single review by ID."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return {
        "id": review.id,
        "repo": review.repo_full_name,
        "pr_number": review.pr_number,
        "pr_title": review.pr_title,
        "function_name": review.function_name,
        "file_path": review.file_path,
        "line_number": review.line_number,
        "complexity_score": review.complexity_score,
        "suggestion": review.suggestion,
        "priority": review.priority,
        "status": review.status,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }
