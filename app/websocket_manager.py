"""WebSocket connection registry that enforces one client per channel."""
from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger("iotvehicule.ws")

# Custom close codes (application-defined range 4000–4999)
WS_CLOSE_BUSY = 4001          # channel already in use
WS_CLOSE_INTERNAL = 4010      # server error while running
WS_CLOSE_TIMEOUT = 4011       # idle too long
WS_CLOSE_REPLACED = 4012      # superseded by a new connection


class ChannelBusyError(Exception):
    """Raised when a channel already has an active socket."""


class WebSocketManager:
    """Tracks one active WebSocket per channel, with concurrency guards."""

    def __init__(self) -> None:
        self._channels: dict[str, WebSocket] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def _lock_for(self, channel: str) -> asyncio.Lock:
        async with self._guard:
            lock = self._locks.get(channel)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[channel] = lock
            return lock

    async def connect(self, channel: str, ws: WebSocket) -> None:
        """
        Accept the socket and register it. Raises ChannelBusyError if the
        channel is already occupied. The caller is responsible for closing.
        """
        lock = await self._lock_for(channel)
        async with lock:
            existing = self._channels.get(channel)
            if existing is not None:
                # Politely refuse: close the *new* socket.
                await ws.accept()
                await ws.close(code=WS_CLOSE_BUSY, reason="channel busy")
                raise ChannelBusyError(f"Channel {channel} is already in use")
            await ws.accept()
            self._channels[channel] = ws
            logger.info("WS connected channel=%s", channel)

    async def disconnect(self, channel: str, ws: WebSocket | None = None) -> None:
        lock = await self._lock_for(channel)
        async with lock:
            current = self._channels.get(channel)
            if current is None:
                return
            if ws is not None and current is not ws:
                return
            self._channels.pop(channel, None)
            self._locks.pop(channel, None)
            logger.info("WS disconnected channel=%s", channel)

    def is_active(self, channel: str) -> bool:
        return channel in self._channels

    async def send_json(self, channel: str, message: dict) -> bool:
        ws = self._channels.get(channel)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception:
            logger.warning("WS send failed on channel=%s", channel, exc_info=True)
            await self.disconnect(channel, ws)
            return False


manager = WebSocketManager()