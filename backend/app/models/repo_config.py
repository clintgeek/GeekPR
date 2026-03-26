from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func

from app.models.database import Base


class RepoConfig(Base):
    __tablename__ = "repo_configs"

    id = Column(Integer, primary_key=True, index=True)
    repo_full_name = Column(String, unique=True, index=True)
    cc_threshold = Column(Integer, default=10)
    bandit_enabled = Column(Boolean, default=True)
    llm_provider = Column(String, default="ollama")    # "openai" or "ollama"
    llm_model = Column(String, default="codellama")
    auto_post = Column(Boolean, default=True)
    exclude_patterns = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
