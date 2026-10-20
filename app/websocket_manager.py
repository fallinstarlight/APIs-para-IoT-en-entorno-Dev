"""WebSocket connection registry.

Constraints enforced here:
  - At most one socket per channel (per vehicle).
  - At most MAX_TOTAL_SOCKETS sockets across all channels (2).

Broadcasts on a channel only reach that channel's subscriber, so two
vehicles never see each other's traffic.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger("iotvehicule.ws")

MAX_TOTAL_SOCKETS = 2

# Application-defined close codes (4000–4999).
WS_CLOSE_CHANNEL_BUSY = 4001     # a socket is already attached to this channel
WS_CLOSE_CAPACITY = 4002         # global socket limit reached
WS_CLOSE_INTERNAL = 4010         # server-side error


class ChannelBusyError(Exception):
    """A socket is already attached to this channel."""


class CapacityError(Exception):
    """The global socket limit has been reached."""


class WebSocketManager:
    def __init__(self, max_total: int = MAX_TOTAL_SOCKETS) -> None:
        self._channels: dict[str, WebSocket] = {}
        self._max_total = max_total
        self._guard = asyncio.Lock()

    # ------------------------------------------------------------------ info
    def channel_count(self) -> int:
        return len(self._channels)

    def is_channel_active(self, channel: str) -> bool:
        return channel in self._channels

    # ---------------------------------------------------------------- lifecycle
    async def connect(self, channel: str, ws: WebSocket) -> None:
        """
        Accept the socket and bind it to `channel`.

        Raises ChannelBusyError if the channel is occupied, CapacityError if
        the global cap has been reached. In both cases the socket is closed
        with a meaningful close code before the exception is raised.
        """
        # Accept first, otherwise we can't send a close frame / reason.
        await ws.accept()

        async with self._guard:
            if channel in self._channels:
                await ws.close(code=WS_CLOSE_CHANNEL_BUSY,
                               reason="vehicle already has an active client")
                raise ChannelBusyError(f"Channel {channel} is already in use")

            if len(self._channels) >= self._max_total:
                await ws.close(code=WS_CLOSE_CAPACITY,
                               reason="maximum number of connections reached")
                raise CapacityError("Global socket limit reached")

            self._channels[channel] = ws

        logger.info("WS connected channel=%s total=%d",
                    channel, len(self._channels))

    async def disconnect(self, channel: str, ws: WebSocket | None = None) -> None:
        async with self._guard:
            current = self._channels.get(channel)
            if current is None:
                return
            if ws is not None and current is not ws:
                return
            self._channels.pop(channel, None)

        logger.info("WS disconnected channel=%s total=%d",
                    channel, len(self._channels))

    async def broadcast(self, channel: str, message: dict) -> None:
        """Send to the single subscriber of `channel`, if any."""
        async with self._guard:
            ws = self._channels.get(channel)
        if ws is None:
            return
        try:
            await ws.send_json(message)
        except Exception:
            logger.warning("WS send failed channel=%s", channel, exc_info=True)
            await self.disconnect(channel, ws)


manager = WebSocketManager()