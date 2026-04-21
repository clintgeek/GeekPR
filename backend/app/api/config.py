from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.repo_config import RepoConfig

router = APIRouter()


class RepoConfigUpdate(BaseModel):
    cc_threshold: int | None = None
    bandit_enabled: bool | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    auto_post: bool | None = None
    post_all_clear: bool | None = None
    exclude_patterns: str | None = None


@router.get("/{repo_owner}/{repo_name}")
def get_repo_config(repo_owner: str, repo_name: str, db: Session = Depends(get_db)):
    """Get configuration for a specific repo."""
    full_name = f"{repo_owner}/{repo_name}"
    config = db.query(RepoConfig).filter_by(repo_full_name=full_name).first()

    if not config:
        # Return defaults
        return {
            "repo": full_name,
            "cc_threshold": 15,
            "bandit_enabled": True,
            "llm_provider": "aigeek",
            "llm_model": "anthropic/claude-sonnet-4-6",
            "auto_post": True,
            "post_all_clear": True,
            "exclude_patterns": "",
        }

    return {
        "repo": config.repo_full_name,
        "cc_threshold": config.cc_threshold,
        "bandit_enabled": config.bandit_enabled,
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
        "auto_post": config.auto_post,
        "post_all_clear": config.post_all_clear,
        "exclude_patterns": config.exclude_patterns,
    }


@router.put("/{repo_owner}/{repo_name}")
def update_repo_config(
    repo_owner: str,
    repo_name: str,
    update: RepoConfigUpdate,
    db: Session = Depends(get_db),
):
    """Create or update configuration for a repo."""
    full_name = f"{repo_owner}/{repo_name}"
    config = db.query(RepoConfig).filter_by(repo_full_name=full_name).first()

    if not config:
        config = RepoConfig(repo_full_name=full_name)
        db.add(config)

    if update.cc_threshold is not None:
        config.cc_threshold = update.cc_threshold
    if update.bandit_enabled is not None:
        config.bandit_enabled = update.bandit_enabled
    if update.llm_provider is not None:
        config.llm_provider = update.llm_provider
    if update.llm_model is not None:
        config.llm_model = update.llm_model
    if update.auto_post is not None:
        config.auto_post = update.auto_post
    if update.post_all_clear is not None:
        config.post_all_clear = update.post_all_clear
    if update.exclude_patterns is not None:
        config.exclude_patterns = update.exclude_patterns

    db.commit()
    return {"message": "Config updated", "repo": full_name}
