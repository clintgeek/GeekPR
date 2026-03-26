from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReviewBase(BaseModel):
    id: int
    repo: str
    pr_number: int
    pr_title: str
    function_name: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    complexity_score: Optional[int] = None
    suggestion: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None

class ReviewListResponse(BaseModel):
    total: int
    reviews: list[ReviewBase]

class ReviewResponse(ReviewBase):
    pass
