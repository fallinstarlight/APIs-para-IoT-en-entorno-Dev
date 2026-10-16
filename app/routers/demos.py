import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from ..database import call_procedure, call_procedure_no_result, procedure_exists
from ..errors import BadRequest, Conflict, ResourceNotFound
from ..schemas import (
    Demo,
    DemoCreate,
    DemoMovement,
    DemoMovementCreate,
    DemoMovementUpdate,
    DemoUpdate,
)
from ..websocket_manager import (
    WS_CLOSE_INTERNAL,
    ChannelBusyError,
    manager,
)

logger = logging.getLogger("iotvehicule.demos")

router = APIRouter(prefix="/demos", tags=["Demos"])

# The optional procedure used by the WS runner to resolve the parent vehicle.
_HAS_GET_DEMO_VEHICLE = procedure_exists("spGetDemoVehicleId")


# --------------------------- CRUD: demos ----------------------------------
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    summary="spCreateDemo",
)
def create_demo(payload: DemoCreate):
    rows = call_procedure(
        "spCreateDemo", [payload.vehicleId, payload.name, payload.description]
    )
    if not rows or "demoId" not in rows[0]:
        raise Conflict("Demo could not be created")
    return rows[0]


@router.get(
    "/vehicle/{vehicle_id}",
    response_model=list[Demo],
    summary="spGetDemos",
)
def list_demos(vehicle_id: int):
    if vehicle_id <= 0:
        raise BadRequest("vehicle_id must be a positive integer")
    return call_procedure("spGetDemos", [vehicle_id])


@router.put("/{demo_id}", summary="spUpdateDemo")
def update_demo(demo_id: int, payload: DemoUpdate):
    if demo_id <= 0:
        raise BadRequest("demo_id must be a positive integer")
    call_procedure_no_result(
        "spUpdateDemo",
        [demo_id, payload.name, payload.description, payload.isActive],
    )
    return {"status": "ok", "demoId": demo_id}


@router.delete("/{demo_id}", summary="spDeleteDemo")
def delete_demo(demo_id: int):
    if demo_id <= 0:
        raise BadRequest("demo_id must be a positive integer")
    call_procedure_no_result("spDeleteDemo", [demo_id])
    return {"status": "ok", "demoId": demo_id}


# --------------------------- CRUD: movements ------------------------------
@router.post(
    "/movements",
    status_code=status.HTTP_201_CREATED,
    summary="spAddDemoMovement",
)
def add_demo_movement(payload: DemoMovementCreate):
    call_procedure_no_result(
        "spAddDemoMovement",
        [
            payload.demoId,
            payload.commandId,
            payload.sortOrder,
            payload.durationMs,
            payload.pauseMs,
        ],
    )
    return {"status": "ok"}


@router.get(
    "/{demo_id}/movements",
    response_model=list[DemoMovement],
    summary="spGetDemoMovements",
)
def get_demo_movements(demo_id: int):
    if demo_id <= 0:
        raise BadRequest("demo_id must be a positive integer")
    return call_procedure("spGetDemoMovements", [demo_id])


@router.put("/movements/{movement_id}", summary="spUpdateDemoMovement")
def update_demo_movement(movement_id: int, payload: DemoMovementUpdate):
    if movement_id <= 0:
        raise BadRequest("movement_id must be a positive integer")
    call_procedure_no_result(
        "spUpdateDemoMovement",
        [
            movement_id,
            payload.commandId,
            payload.sortOrder,
            payload.durationMs,
            payload.pauseMs,
        ],
    )
    return {"status": "ok", "demoMovementId": movement_id}


@router.delete("/movements/{movement_id}", summary="spDeleteDemoMovement")
def delete_demo_movement(movement_id: int):
    if movement_id <= 0:
        raise BadRequest("movement_id must be a positive integer")
    call_procedure_no_result("spDeleteDemoMovement", [movement_id])
    return {"status": "ok", "demoMovementId": movement_id}


# --------------------------- WS runner ------------------------------------
def _resolve_vehicle_id(demo_id: int) -> int | None:
    """Resolve the parent vehicle of a demo, if possible."""
    if _HAS_GET_DEMO_VEHICLE:
        rows = call_procedure("spGetDemoVehicleId", [demo_id])
        if rows and "vehicleId" in rows[0]:
            return int(rows[0]["vehicleId"])
    # Fallback: scan all vehicles' demos.
    try:
        vehicles = call_procedure("spGetVehicles")
        for v in vehicles:
            v_id = v.get("vehicleId")
            if v_id is None:
                continue
            demos = call_procedure("spGetDemos", [v_id])
            if any(d.get("demoId") == demo_id for d in demos):
                return int(v_id)
    except Exception:
        logger.warning("Fallback vehicle lookup failed for demo %s", demo_id,
                       exc_info=True)
    return None


@router.websocket("/{demo_id}/run")
async def run_demo(ws: WebSocket, demo_id: int):
    """
    Execute a demo sequence over WebSocket. Only one client per demo is
    allowed at a time; concurrent connections are rejected with code 4001.
    """
    if demo_id <= 0:
        await ws.accept()
        await ws.close(code=WS_CLOSE_INTERNAL, reason="invalid demo id")
        return

    channel = f"demo:{demo_id}"
    try:
        await manager.connect(channel, ws)
    except ChannelBusyError:
        return  # socket already closed by manager

    try:
        # Validate the demo exists.
        movements = call_procedure("spGetDemoMovements", [demo_id])
        vehicle_id = _resolve_vehicle_id(demo_id)

        if vehicle_id is None:
            # Can't drive status updates without a vehicle.
            await ws.send_json({
                "event": "error",
                "detail": f"Demo {demo_id} has no resolvable vehicle",
            })
            await ws.close(code=WS_CLOSE_INTERNAL,
                           reason="demo has no vehicle")
            return

        await ws.send_json({
            "event": "demo_start",
            "demoId": demo_id,
            "totalMovements": len(movements),
            "vehicleId": vehicle_id,
        })

        for mv in movements:
            # Defensive: procedures should return these keys.
            if "commandId" not in mv or "durationMs" not in mv:
                raise RuntimeError(
                    f"Malformed movement for demo {demo_id}: {mv!r}"
                )

            await ws.send_json({"event": "movement", **mv})

            call_procedure_no_result(
                "spUpdateStatus",
                [vehicle_id, mv["commandId"], True],
            )
            await ws.send_json({
                "event": "status_updated",
                "vehicleId": vehicle_id,
                "commandId": mv["commandId"],
                "isConnected": True,
            })

            await asyncio.sleep(max(mv["durationMs"], 0) / 1000.0)

            pause = mv.get("pauseMs") or 0
            if pause:
                await ws.send_json({
                    "event": "pause",
                    "demoMovementId": mv.get("demoMovementId"),
                    "pauseMs": pause,
                })
                await asyncio.sleep(pause / 1000.0)

        await ws.send_json({"event": "demo_end", "demoId": demo_id})

    except WebSocketDisconnect:
        logger.info("Demo %s client disconnected", demo_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Demo %s run failed", demo_id)
        try:
            await ws.send_json({"event": "error", "detail": str(exc)})
        except Exception:
            pass
        try:
            await ws.close(code=WS_CLOSE_INTERNAL, reason="run failed")
        except Exception:
            pass
    finally:
        await manager.disconnect(channel, ws)