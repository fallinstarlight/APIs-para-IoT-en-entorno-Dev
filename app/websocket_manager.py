"""WebSocket connection registry.

Multiple clients may subscribe to the same channel (observer model).
Broadcasts are best-effort; dead sockets are pruned on failure.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger("iotvehicule.ws")


class WebSocketManager:
    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = {}
        self._guard = asyncio.Lock()

    async def connect(self, channel: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._guard:
            self._channels.setdefault(channel, set()).add(ws)
        logger.info("WS connected channel=%s", channel)

    async def disconnect(self, channel: str, ws: WebSocket) -> None:
        async with self._guard:
            conns = self._channels.get(channel)
            if not conns:
                return
            conns.discard(ws)
            if not conns:
                self._channels.pop(channel, None)
        logger.info("WS disconnected channel=%s", channel)

    async def broadcast(self, channel: str, message: dict) -> None:
        async with self._guard:
            conns = list(self._channels.get(channel, ()))
        if not conns:
            return
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(channel, ws)


manager = WebSocketManager()