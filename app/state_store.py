"""In-memory, per-vehicle runtime state, published on a global bus."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

from .database import call_procedure
from .websocket_manager import manager

logger = logging.getLogger("iotvehicule.state")

GLOBAL_CHANNEL = "status:all"
vehicle_channel = lambda vid: f"vehicle:{vid}"  # noqa: E731


@dataclass
class VehicleState:
    vehicleId: int
    commandId: Optional[int] = None
    commandName: Optional[str] = None
    code: Optional[int] = None
    isConnected: bool = False
    source: str = "SYSTEM"
    lastUpdate: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VehicleStateStore:
    def __init__(self) -> None:
        self._states: dict[int, VehicleState] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def _lock_for(self, vehicle_id: int) -> asyncio.Lock:
        async with self._guard:
            lock = self._locks.get(vehicle_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[vehicle_id] = lock
            return lock

    # ------------------------------------------------------------------ read
    def get_cached(self, vehicle_id: int) -> Optional[VehicleState]:
        return self._states.get(vehicle_id)

    def snapshot(self) -> list[dict]:
        return [s.to_dict() for s in self._states.values()]

    def get_or_hydrate(self, vehicle_id: int) -> VehicleState:
        cached = self._states.get(vehicle_id)
        if cached is not None:
            return cached

        try:
            rows = call_procedure("spGetStatus", [vehicle_id])
        except Exception:
            logger.warning("Could not hydrate vehicle %s", vehicle_id,
                           exc_info=True)
            rows = []

        if rows:
            r = rows[0]
            state = VehicleState(
                vehicleId=vehicle_id,
                commandId=r.get("commandId"),
                commandName=r.get("commandName"),
                code=r.get("code"),
                isConnected=bool(r.get("isConnected", False)),
                source="SYSTEM",
                lastUpdate=r.get("lastUpdate")
                or datetime.now(timezone.utc).isoformat(),
            )
        else:
            state = VehicleState(vehicleId=vehicle_id)

        self._states[vehicle_id] = state
        return state

    # ----------------------------------------------------------------- write
    async def set(
        self,
        vehicle_id: int,
        *,
        commandId: Optional[int],
        commandName: Optional[str] = None,
        code: Optional[int] = None,
        isConnected: bool,
        source: str,
    ) -> VehicleState:
        lock = await self._lock_for(vehicle_id)
        async with lock:
            state = VehicleState(
                vehicleId=vehicle_id,
                commandId=commandId,
                commandName=commandName,
                code=code,
                isConnected=isConnected,
                source=source,
                lastUpdate=datetime.now(timezone.utc).isoformat(),
            )
            self._states[vehicle_id] = state

        payload = {"event": "state", **state.to_dict()}
        await manager.broadcast(GLOBAL_CHANNEL, payload)
        await manager.broadcast(vehicle_channel(vehicle_id), payload)
        return state


store = VehicleStateStore()