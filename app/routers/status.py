from fastapi import APIRouter, HTTPException

from ..database import call_procedure, call_procedure_no_result
from ..schemas import Status, StatusUpdate

router = APIRouter(prefix="/status", tags=["Status"])


@router.post("", summary="spUpdateStatus (+ spRegisterHistory)")
def update_status(payload: StatusUpdate):
    """
    Updates the vehicle status via `spUpdateStatus`.

    After a successful update, this endpoint also calls `spRegisterHistory`
    so every status change leaves a trail (unless `source` is `DEMO`).
    """
    call_procedure_no_result(
        "spUpdateStatus",
        [payload.vehicleId, payload.commandId, payload.isConnected],
    )

    # Mirror the status change into history (unless the caller is a demo).
    if payload.source.upper() != "DEMO":
        call_procedure_no_result(
            "spRegisterHistory",
            [payload.vehicleId, payload.commandId, payload.source],
        )

    return {
        "status": "ok",
        "vehicleId": payload.vehicleId,
        "commandId": payload.commandId,
        "isConnected": payload.isConnected,
        "historyRegistered": payload.source.upper() != "DEMO",
    }


@router.get("/{vehicle_id}", response_model=list[Status], summary="spGetStatus")
def get_status(vehicle_id: int):
    rows = call_procedure("spGetStatus", [vehicle_id])
    if not rows:
        raise HTTPException(status_code=404, detail="Status not found")
    return rows