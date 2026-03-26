from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func

from app.models.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    repo_full_name = Column(String, index=True)
    pr_number = Column(Integer)
    pr_title = Column(String)
    function_name = Column(String)
    file_path = Column(String)
    line_number = Column(Integer)
    complexity_score = Column(Float)
    suggestion = Column(Text)
    priority = Column(String, default="Medium")
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
