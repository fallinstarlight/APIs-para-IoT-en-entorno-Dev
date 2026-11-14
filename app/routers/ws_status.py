"""Per-vehicle status WebSocket: WS /ws/status/{vehicle_id}."""
from __future__ import annotations

import logging
from asyncio import to_thread

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..database import call_procedure
from ..state_store import VehicleState, store, vehicle_channel
from ..websocket_manager import WS_CLOSE_INTERNAL, manager
from ..demo_runner import vehicle_demo_active

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
        rows = await to_thread(call_procedure, "spGetVehicle", [vehicle_id])
        if not rows:
            await ws.accept()
            await ws.close(code=WS_CLOSE_INTERNAL,
                           reason="vehicle not found")
            return
    except Exception:
        logger.warning("Vehicle existence check failed for %s",
                       vehicle_id, exc_info=True)

    await to_thread(store.get_or_hydrate, vehicle_id)
    channel = vehicle_channel(vehicle_id)

    await manager.connect(channel, ws)

    try:
        # Initial snapshot for this vehicle only.
        state = store.get_cached(vehicle_id) or VehicleState(vehicleId=vehicle_id)
        await ws.send_json({"event": "state", "snapshot": True, "demoActive": vehicle_demo_active(vehicle_id), **state.to_dict()})

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