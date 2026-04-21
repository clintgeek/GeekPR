import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.config import router as config_router
from app.api.jobs import router as jobs_router
from app.api.reviews import router as reviews_router
from app.api.webhook import router as webhook_router
from app.api.ws import redis_listener, router as ws_router
from app.core.auth import require_basegeek_user
from app.core.config import settings

logger = logging.getLogger(__name__)


def _enforce_auth_config() -> None:
    """Refuse to start unless BASEGEEK_AUTH_ENABLED is explicitly set.

    Tri-state by design — we never want the service to silently come up
    without auth just because someone forgot to set an env var.
    """
    mode = settings.basegeek_auth_enabled
    if mode is None:
        sys.stderr.write(
            "FATAL: BASEGEEK_AUTH_ENABLED is not set. Choose one:\n"
            "  BASEGEEK_AUTH_ENABLED=true  — enforce basegeek SSO on every route\n"
            "  BASEGEEK_AUTH_ENABLED=false — run without auth (operator protects upstream)\n"
            "Aborting startup.\n"
        )
        raise SystemExit(1)

    if mode not in ("true", "false"):
        sys.stderr.write(
            f"FATAL: BASEGEEK_AUTH_ENABLED must be 'true' or 'false', got {mode!r}.\n"
        )
        raise SystemExit(1)

    if mode == "false":
        logger.warning(
            "⚠️  BASEGEEK_AUTH_ENABLED=false — geekPR is running with NO in-process "
            "auth. This service MUST be protected by something upstream "
            "(nginx basic auth, VPN, mTLS, IP allowlist). Do not expose directly "
            "to the public internet in this mode."
        )
    else:
        logger.info(
            "basegeek SSO enabled — session verification via %s/api/users/me",
            settings.basegeek_base_url.rstrip("/"),
        )


_enforce_auth_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(redis_listener())
    yield
    task.cancel()


app = FastAPI(
    title="geekPR",
    description="The Autonomous Code Reviewer",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: when SSO is on, lock to the known frontend origin so stray
# browsers can't hit the API cross-origin even with a stolen cookie.
# In bypass mode, keep it permissive (the operator's upstream layer
# is already the security boundary).
_cors_origins = (
    ["https://geekpr.clintgeek.com", "http://localhost:3001", "http://localhost:3000"]
    if settings.basegeek_auth_enabled == "true"
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Webhook is unauthenticated at the session level — GitHub can't carry a
# basegeek cookie. Its HMAC signature check (app/core/security.py) is its
# auth. Everything else requires a valid basegeek user.
app.include_router(webhook_router, prefix="/api/webhook", tags=["webhook"])

_protected = [Depends(require_basegeek_user)]
app.include_router(auth_router, prefix="/api/auth", tags=["auth"], dependencies=_protected)
app.include_router(reviews_router, prefix="/api/reviews", tags=["reviews"], dependencies=_protected)
app.include_router(config_router, prefix="/api/config", tags=["config"], dependencies=_protected)
app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"], dependencies=_protected)

# WebSocket auth is handled inline — FastAPI Depends doesn't run for
# WebSocket routes the same way. See app/api/ws.py.
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
def health_check():
    """Unauthenticated liveness probe for docker-compose / kubernetes."""
    return {"status": "ok", "service": "geekpr-backend"}
