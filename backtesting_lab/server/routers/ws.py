"""
WebSocket Manager — Real-time streaming for live updates.
"""
import asyncio
import json
from datetime import datetime
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts."""

    def __init__(self):
        self._active: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._active.add(websocket)
        logger.info(f"WS client connected. Total: {len(self._active)}")

    def disconnect(self, websocket: WebSocket):
        self._active.discard(websocket)
        logger.info(f"WS client disconnected. Total: {len(self._active)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self._active:
            return

        payload = json.dumps(message, default=str)
        disconnected = set()

        for ws in self._active.copy():
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            self._active.discard(ws)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception:
            self._active.discard(websocket)

    @property
    def client_count(self) -> int:
        return len(self._active)


# Singleton instance
ws_manager = ConnectionManager()


async def broadcast_price(price_data: dict):
    """Broadcast price update to all clients."""
    await ws_manager.broadcast({
        "type": "price",
        "data": price_data,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_signal(signal_data: dict):
    """Broadcast trading signal to all clients."""
    await ws_manager.broadcast({
        "type": "signal",
        "data": signal_data,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_trade(trade_data: dict):
    """Broadcast trade execution to all clients."""
    await ws_manager.broadcast({
        "type": "trade",
        "data": trade_data,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_heartbeat(status: dict):
    """Broadcast system heartbeat."""
    await ws_manager.broadcast({
        "type": "heartbeat",
        "data": status,
        "timestamp": datetime.now().isoformat()
    })
