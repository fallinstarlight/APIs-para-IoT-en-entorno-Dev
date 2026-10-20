"""Background demo executor.

Demo events are broadcast on the vehicle's own channel, so only the
client watching that vehicle sees them.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .database import call_procedure, call_procedure_no_result
from .state_store import store, vehicle_channel
from .websocket_manager import manager

logger = logging.getLogger("iotvehicule.demo_runner")

_running: dict[int, asyncio.Task] = {}
_running_lock = asyncio.Lock()


class DemoAlreadyRunning(Exception):
    pass


class DemoNotFound(Exception):
    pass


async def start_demo(demo_id: int) -> dict:
    async with _running_lock:
        existing = _running.get(demo_id)
        if existing is not None and not existing.done():
            raise DemoAlreadyRunning(f"Demo {demo_id} is already running")

        vehicle_id, movements = _prepare(demo_id)
        task = asyncio.create_task(_run(demo_id, vehicle_id, movements))
        _running[demo_id] = task
        task.add_done_callback(lambda _t, d=demo_id: _running.pop(d, None))

    return {
        "demoId": demo_id,
        "vehicleId": vehicle_id,
        "totalMovements": len(movements),
        "status": "started",
    }


def is_running(demo_id: int) -> bool:
    task = _running.get(demo_id)
    return task is not None and not task.done()


def _resolve_vehicle_id(demo_id: int) -> Optional[int]:
    try:
        rows = call_procedure("spGetDemoVehicleId", [demo_id])
        if rows and "vehicleId" in rows[0]:
            return int(rows[0]["vehicleId"])
    except Exception:
        pass
    try:
        for v in call_procedure("spGetVehicles"):
            vid = v.get("vehicleId")
            if vid is None:
                continue
            for d in call_procedure("spGetDemos", [vid]):
                if d.get("demoId") == demo_id:
                    return int(vid)
    except Exception:
        logger.warning("Vehicle lookup failed for demo %s", demo_id,
                       exc_info=True)
    return None


def _prepare(demo_id: int) -> tuple[int, list[dict]]:
    vehicle_id = _resolve_vehicle_id(demo_id)
    if vehicle_id is None:
        raise DemoNotFound(f"Demo {demo_id} has no resolvable vehicle")
    movements = call_procedure("spGetDemoMovements", [demo_id])
    if not movements:
        raise DemoNotFound(f"Demo {demo_id} has no movements")
    for mv in movements:
        if "commandId" not in mv or "durationMs" not in mv:
            raise DemoNotFound(f"Demo {demo_id} has a malformed movement")
    return vehicle_id, movements


async def _run(demo_id: int, vehicle_id: int, movements: list[dict]) -> None:
    chan = vehicle_channel(vehicle_id)
    try:
        await manager.broadcast(chan, {
            "event": "demo_start",
            "demoId": demo_id,
            "vehicleId": vehicle_id,
            "totalMovements": len(movements),
        })

        for mv in movements:
            await manager.broadcast(chan, {
                "event": "movement",
                "demoId": demo_id,
                "vehicleId": vehicle_id,
                **mv,
            })

            call_procedure_no_result(
                "spUpdateStatus",
                [vehicle_id, mv["commandId"], True],
            )
            await store.set(
                vehicle_id,
                commandId=mv["commandId"],
                commandName=mv.get("commandName"),
                code=mv.get("code"),
                isConnected=True,
                source="DEMO",
            )

            await asyncio.sleep(max(mv["durationMs"], 0) / 1000.0)

            pause = mv.get("pauseMs") or 0
            if pause:
                await manager.broadcast(chan, {
                    "event": "pause",
                    "demoId": demo_id,
                    "vehicleId": vehicle_id,
                    "demoMovementId": mv.get("demoMovementId"),
                    "pauseMs": pause,
                })
                await asyncio.sleep(pause / 1000.0)

        await manager.broadcast(chan, {
            "event": "demo_end",
            "demoId": demo_id,
            "vehicleId": vehicle_id,
        })

    except asyncio.CancelledError:
        await manager.broadcast(chan, {
            "event": "demo_end",
            "demoId": demo_id,
            "vehicleId": vehicle_id,
            "cancelled": True,
        })
        raise
    except Exception as exc:
        logger.exception("Demo %s failed", demo_id)
        await manager.broadcast(chan, {
            "event": "demo_error",
            "demoId": demo_id,
            "vehicleId": vehicle_id,
            "detail": str(exc),
        })