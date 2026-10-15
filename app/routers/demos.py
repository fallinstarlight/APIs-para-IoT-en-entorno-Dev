import asyncio
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from ..database import call_procedure, call_procedure_no_result
from ..schemas import (
    Demo,
    DemoCreate,
    DemoMovement,
    DemoMovementCreate,
    DemoMovementUpdate,
    DemoUpdate,
)
from ..websocket_manager import manager

router = APIRouter(prefix="/demos", tags=["Demos"])


# ------------------ CRUD ------------------
@router.post("", status_code=status.HTTP_201_CREATED, summary="spCreateDemo")
def create_demo(payload: DemoCreate):
    rows = call_procedure(
        "spCreateDemo", [payload.vehicleId, payload.name, payload.description]
    )
    if not rows:
        raise HTTPException(status_code=500, detail="Demo could not be created")
    return rows[0]


@router.get("/vehicle/{vehicle_id}", response_model=list[Demo],
            summary="spGetDemos")
def list_demos(vehicle_id: int):
    return call_procedure("spGetDemos", [vehicle_id])


@router.put("/{demo_id}", summary="spUpdateDemo")
def update_demo(demo_id: int, payload: DemoUpdate):
    call_procedure_no_result(
        "spUpdateDemo",
        [demo_id, payload.name, payload.description, payload.isActive],
    )
    return {"status": "ok", "demoId": demo_id}


@router.delete("/{demo_id}", summary="spDeleteDemo")
def delete_demo(demo_id: int):
    call_procedure_no_result("spDeleteDemo", [demo_id])
    return {"status": "ok", "demoId": demo_id}


# ------------------ Movements ------------------
@router.post("/movements", status_code=status.HTTP_201_CREATED,
             summary="spAddDemoMovement")
def add_demo_movement(payload: DemoMovementCreate):
    call_procedure_no_result(
        "spAddDemoMovement",
        [payload.demoId, payload.commandId, payload.sortOrder,
         payload.durationMs, payload.pauseMs],
    )
    return {"status": "ok"}


@router.get("/{demo_id}/movements", response_model=list[DemoMovement],
            summary="spGetDemoMovements")
def get_demo_movements(demo_id: int):
    return call_procedure("spGetDemoMovements", [demo_id])


@router.put("/movements/{movement_id}", summary="spUpdateDemoMovement")
def update_demo_movement(movement_id: int, payload: DemoMovementUpdate):
    call_procedure_no_result(
        "spUpdateDemoMovement",
        [movement_id, payload.commandId, payload.sortOrder,
         payload.durationMs, payload.pauseMs],
    )
    return {"status": "ok", "demoMovementId": movement_id}


@router.delete("/movements/{movement_id}", summary="spDeleteDemoMovement")
def delete_demo_movement(movement_id: int):
    call_procedure_no_result("spDeleteDemoMovement", [movement_id])
    return {"status": "ok", "demoMovementId": movement_id}


# ------------------ Run Demo (WebSocket) ------------------
@router.websocket("/{demo_id}/run")
async def run_demo(ws: WebSocket, demo_id: int):
    """
    Execute a demo sequence.

    1. Loads all movements via `spGetDemoMovements`.
    2. Streams each movement to the client over the WebSocket, one by one.
    3. For each movement it calls `spUpdateStatus` (no history entry),
       so the hardware/observer sees the current command during the
       movement's duration.
    4. Sleeps `durationMs` and then `pauseMs` before moving on.
    """
    channel = f"demo:{demo_id}"
    await manager.connect(channel, ws)

    try:
        movements = call_procedure("spGetDemoMovements", [demo_id])

        # We need the vehicle id: derive it from the demo row.
        # `spGetDemos` returns demos for a vehicle, but here we only have demoId.
        # A tiny helper: query it directly via a dedicated procedure is not
        # available, so we fetch the demo via the demoId using the existing
        # `spGetDemos` on the parent vehicle. Instead, we just accept it as
        # a query parameter for the WS, but to keep the spec simple we look it
        # up with a lightweight inline procedure call.
        vehicle_rows = call_procedure("spGetDemoVehicleId", [demo_id]) \
            if _procedure_exists("spGetDemoVehicleId") else []
        vehicle_id = vehicle_rows[0]["vehicleId"] if vehicle_rows else None

        await ws.send_json({
            "event": "demo_start",
            "demoId": demo_id,
            "totalMovements": len(movements),
            "vehicleId": vehicle_id,
        })

        for mv in movements:
            await ws.send_json({"event": "movement", **mv})

            if vehicle_id is not None:
                # No history entry for demo movements.
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

            await asyncio.sleep(mv["durationMs"] / 1000.0)

            if mv["pauseMs"]:
                await ws.send_json({
                    "event": "pause",
                    "demoMovementId": mv["demoMovementId"],
                    "pauseMs": mv["pauseMs"],
                })
                await asyncio.sleep(mv["pauseMs"] / 1000.0)

        await ws.send_json({"event": "demo_end", "demoId": demo_id})

    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        try:
            await ws.send_json({"event": "error", "detail": str(exc)})
        except Exception:  # noqa: BLE001
            pass
    finally:
        manager.disconnect(channel, ws)


def _procedure_exists(name: str) -> bool:
    """Check if a stored procedure exists (used to keep backward compat)."""
    from ..database import get_connection
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.ROUTINES "
                "WHERE ROUTINE_SCHEMA = DATABASE() AND ROUTINE_NAME = %s",
                (name,),
            )
            (count,) = cur.fetchone()
            cur.close()
            return count > 0
    except Exception:  # noqa: BLE001
        return False