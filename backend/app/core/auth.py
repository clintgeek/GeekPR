"""
basegeek SSO integration — FastAPI dependency that validates an incoming
request's session against basegeek's /api/users/me endpoint.

Three operating modes, controlled by settings.basegeek_auth_enabled:

  "true"   — Enforce. Every protected route requires a valid geek_token
             cookie (or Authorization: Bearer header). Invalid/missing → 401.

  "false"  — Bypass. The dependency is a no-op and every request carries
             a synthetic anonymous "user" on request.state.user. The
             operator is responsible for upstream protection (nginx auth,
             VPN, etc.). main.py logs a loud warning at startup.

  None     — Refused at startup. See main.py's startup gate. We never
             want to accidentally ship a public API.

Successful /me responses are cached per-token for a short TTL (default
60s) so we're not roundtripping to basegeek on every single API call.
The cache is keyed by the full token string — when a token is refreshed
upstream, the new one misses the cache and re-validates, which is what
we want.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings


@dataclass
class CachedSession:
    user: dict[str, Any]
    expires_at: float


_SESSION_CACHE: dict[str, CachedSession] = {}


def _extract_token(request: Request) -> str | None:
    """Pull the session token from either the cookie or the Authorization
    header. Cookie wins if both are present (matches basegeek's own
    precedence)."""
    cookie_token = request.cookies.get(settings.basegeek_session_cookie)
    if cookie_token:
        return cookie_token
    header = request.headers.get("authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return None


def _get_cached(token: str) -> dict[str, Any] | None:
    entry = _SESSION_CACHE.get(token)
    if entry is None:
        return None
    if entry.expires_at < time.monotonic():
        _SESSION_CACHE.pop(token, None)
        return None
    return entry.user


def _set_cached(token: str, user: dict[str, Any]) -> None:
    _SESSION_CACHE[token] = CachedSession(
        user=user,
        expires_at=time.monotonic() + settings.basegeek_session_cache_ttl,
    )


async def _verify_with_basegeek(token: str) -> dict[str, Any]:
    """Call GET {basegeek}/api/users/me and return the user object on
    success. Raise HTTPException(401) on any non-200 response."""
    url = f"{settings.basegeek_base_url.rstrip('/')}/api/users/me"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError:
        # basegeek is unreachable — fail closed rather than hand out access.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    payload = response.json()
    user = payload.get("user")
    if not user or not isinstance(user, dict):
        # Unexpected shape from basegeek — treat as auth failure.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed session response from basegeek",
        )
    return user


async def require_basegeek_user(request: Request) -> dict[str, Any]:
    """FastAPI dependency: enforce a valid basegeek session.

    Respects settings.basegeek_auth_enabled:
      - "true"  → verify (cache hit or fresh call)
      - "false" → return a synthetic anonymous user; never raises
    """
    if settings.basegeek_auth_enabled != "true":
        # Bypass mode. Operator protects upstream; we surface a stable
        # synthetic identity so route handlers can still read
        # request.state.user without None checks.
        anon = {"id": None, "username": "anonymous", "email": None, "auth": "bypass"}
        request.state.user = anon
        return anon

    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    cached = _get_cached(token)
    if cached is not None:
        request.state.user = cached
        return cached

    user = await _verify_with_basegeek(token)
    _set_cached(token, user)
    request.state.user = user
    return user


# Convenience alias so route modules read naturally: Depends(RequireUser)
RequireUser = Depends(require_basegeek_user)
