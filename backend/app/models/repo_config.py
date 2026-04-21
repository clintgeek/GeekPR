from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func

from app.models.database import Base


class RepoConfig(Base):
    __tablename__ = "repo_configs"

    id = Column(Integer, primary_key=True, index=True)
    repo_full_name = Column(String, unique=True, index=True)
    cc_threshold = Column(Integer, default=10)
    bandit_enabled = Column(Boolean, default=True)
    # "aigeek" (default, routes through baseGeek proxy), "openai", or "ollama"
    llm_provider = Column(String, default="aigeek")
    # For aigeek, "<provider>/<model>" pins a specific backend. Default
    # anthropic/claude-sonnet-4-6 gives consistent structured output.
    llm_model = Column(String, default="anthropic/claude-sonnet-4-6")
    auto_post = Column(Boolean, default=True)
    exclude_patterns = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
