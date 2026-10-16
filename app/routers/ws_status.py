"""Single global status WebSocket: WS /ws/status."""
from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..state_store import GLOBAL_CHANNEL, store
from ..websocket_manager import manager

logger = logging.getLogger("iotvehicule.ws_status")

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/status")
async def ws_status(ws: WebSocket):
    await manager.connect(GLOBAL_CHANNEL, ws)
    try:
        await ws.send_json({
            "event": "snapshot",
            "vehicles": store.snapshot(),
        })
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_json({"event": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Global WS error")
    finally:
        await manager.disconnect(GLOBAL_CHANNEL, ws)