"""
Auth endpoints geekPR exposes to its own frontend.

Thin wrappers over basegeek's SSO — we don't proxy login/logout (the
frontend's middleware redirects to basegeek for those). This module
exists so the dashboard can ask "who am I logged in as?" without
knowing basegeek's URL directly.
"""

from fastapi import APIRouter, Depends

from app.core.auth import require_basegeek_user
from app.core.config import settings

router = APIRouter()


@router.get("/me")
async def get_current_user(user: dict = Depends(require_basegeek_user)) -> dict:
    """Return the currently-authenticated basegeek user (or the synthetic
    anonymous user in bypass mode). Frontend hits this on load to decide
    whether to render the dashboard or redirect to login."""
    return {
        "user": user,
        "auth_mode": settings.basegeek_auth_enabled or "unset",
    }


@router.get("/login-url")
def get_login_url(redirect: str | None = None) -> dict:
    """Return the basegeek login URL the frontend should redirect to on 401.
    Kept on the backend so the basegeek host isn't baked into the frontend
    bundle — change the env var, no frontend rebuild."""
    base = settings.basegeek_login_url.rstrip("/")
    query = "?app=geekpr"
    if redirect:
        query += f"&redirect={redirect}"
    return {"url": f"{base}/{query}"}
