import json
import asyncio
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

from app.core.config import settings

router = APIRouter()


async def _ws_authorize(websocket: WebSocket) -> bool:
    """Validate the connecting client's basegeek session before we accept
    the WebSocket.

    FastAPI's Depends(require_basegeek_user) doesn't run on WebSocket
    routes the same way HTTP dependencies do, so we reuse the cookie-read
    + /api/users/me verification inline here. Bypass mode lets everyone
    through (the operator's upstream layer is the security boundary).
    """
    if settings.basegeek_auth_enabled != "true":
        return True

    token = websocket.cookies.get(settings.basegeek_session_cookie)
    if not token:
        # Also allow ?token=... as a fallback — some WS clients can't
        # send cookies on cross-origin handshakes.
        token = websocket.query_params.get("token")
    if not token:
        return False

    url = f"{settings.basegeek_base_url.rstrip('/')}/api/users/me"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError:
        return False
    return response.status_code == 200

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass


manager = ConnectionManager()

# Background task to listen to Redis
async def redis_listener():
    try:
        redis = await aioredis.from_url(settings.redis_url)
        pubsub = redis.pubsub()
        await pubsub.subscribe("reviews_updates")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"].decode("utf-8")
                await manager.broadcast(data)
    except Exception as e:
        print(f"Redis listener error: {e}")


@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    if not await _ws_authorize(websocket):
        # 4001 is an application-level "unauthorized" code (1008 policy
        # violation is also common but 4xxx is reserved for app use).
        await websocket.close(code=4001, reason="Unauthorized")
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
