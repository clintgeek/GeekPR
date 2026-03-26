from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.models.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    celery_task_id = Column(String, unique=True, index=True)
    repo_full_name = Column(String, index=True)
    pr_number = Column(Integer)
    status = Column(String, default="queued")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
