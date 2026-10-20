"""Per-vehicle status WebSocket: WS /ws/status/{vehicle_id}."""
from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..database import call_procedure
from ..state_store import store, vehicle_channel
from ..websocket_manager import (
    CapacityError,
    ChannelBusyError,
    WS_CLOSE_INTERNAL,
    manager,
)

logger = logging.getLogger("iotvehicule.ws_status")

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/status/{vehicle_id}")
async def ws_status(ws: WebSocket, vehicle_id: int):
    # Invalid id — close before registering anything.
    if vehicle_id <= 0:
        await ws.accept()
        await ws.close(code=WS_CLOSE_INTERNAL, reason="invalid vehicle id")
        return

    # Reject up-front if the vehicle doesn't exist (best effort).
    try:
        rows = call_procedure("spGetVehicle", [vehicle_id])
        if not rows:
            await ws.accept()
            await ws.close(code=WS_CLOSE_INTERNAL,
                           reason="vehicle not found")
            return
    except Exception:
        logger.warning("Vehicle existence check failed for %s",
                       vehicle_id, exc_info=True)

    channel = vehicle_channel(vehicle_id)

    try:
        await manager.connect(channel, ws)
    except (ChannelBusyError, CapacityError):
        return  # manager already closed the socket with a meaningful code

    try:
        # Initial snapshot for this vehicle only.
        state = store.get_or_hydrate(vehicle_id)
        await ws.send_json({"event": "state", **state.to_dict()})

        # Keep the socket alive; drop on disconnect or any inbound error.
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_json({"event": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WS error channel=%s", channel)
    finally:
        await manager.disconnect(channel, ws)