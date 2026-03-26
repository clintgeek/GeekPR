import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

from app.core.config import settings

router = APIRouter()

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
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
