from fastapi import APIRouter

from ..database import call_procedure, call_procedure_no_result
from ..errors import BadRequest, ResourceNotFound
from ..schemas import Status, StatusUpdate

router = APIRouter(prefix="/status", tags=["Status"])


@router.post("", summary="spUpdateStatus (+ spRegisterHistory)")
def update_status(payload: StatusUpdate):
    if payload.vehicleId <= 0:
        raise BadRequest("vehicleId must be a positive integer")
    if payload.commandId is not None and payload.commandId <= 0:
        raise BadRequest("commandId must be a positive integer when provided")

    call_procedure_no_result(
        "spUpdateStatus",
        [payload.vehicleId, payload.commandId, payload.isConnected],
    )

    history_registered = payload.source != "DEMO"
    if history_registered:
        call_procedure_no_result(
            "spRegisterHistory",
            [payload.vehicleId, payload.commandId, payload.source],
        )

    return {
        "status": "ok",
        "vehicleId": payload.vehicleId,
        "commandId": payload.commandId,
        "isConnected": payload.isConnected,
        "historyRegistered": history_registered,
    }


@router.get("/{vehicle_id}", response_model=Status, summary="spGetStatus")
def get_status(vehicle_id: int):
    if vehicle_id <= 0:
        raise BadRequest("vehicle_id must be a positive integer")
    rows = call_procedure("spGetStatus", [vehicle_id])
    if not rows:
        raise ResourceNotFound(f"Status for vehicle {vehicle_id} not found")
    return rows[0]