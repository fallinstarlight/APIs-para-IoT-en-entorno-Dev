from fastapi import WebSocket


class WebSocketManager:
    """Tracks active WebSocket connections, keyed by an arbitrary channel id."""

    def __init__(self) -> None:
        # channel -> list of websockets
        self._channels: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self._channels.setdefault(channel, []).append(ws)

    def disconnect(self, channel: str, ws: WebSocket):
        conns = self._channels.get(channel)
        if not conns:
            return
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._channels.pop(channel, None)

    async def broadcast(self, channel: str, message: dict):
        conns = list(self._channels.get(channel, []))
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)


manager = WebSocketManager()