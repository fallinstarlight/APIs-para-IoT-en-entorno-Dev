"""Fan out status events to all subscribers of a vehicle."""
import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger("iotvehicule.ws")
WS_CLOSE_INTERNAL = 4010


class WebSocketManager:
    def __init__(self):
        self._channels: dict[str, set[WebSocket]] = {}

    async def connect(self, channel, ws):
        await ws.accept()
        self._channels.setdefault(channel, set()).add(ws)

    async def disconnect(self, channel, ws):
        subscribers = self._channels.get(channel)
        if subscribers:
            subscribers.discard(ws)
            if not subscribers:
                del self._channels[channel]

    async def broadcast(self, channel, message):
        async def send(ws):
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("Subscriber disconnected from %s", channel)
                await self.disconnect(channel, ws)

        await asyncio.gather(*(send(ws) for ws in tuple(self._channels.get(channel, ()))))


manager = WebSocketManager()
