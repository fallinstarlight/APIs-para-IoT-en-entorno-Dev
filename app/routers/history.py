from fastapi import APIRouter, status

from ..database import call_procedure, call_procedure_no_result
from ..errors import BadRequest
from ..schemas import HistoryEntry, HistoryRegister

router = APIRouter(prefix="/history", tags=["History"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="spRegisterHistory",
)
def register_history(payload: HistoryRegister):
    if payload.vehicleId <= 0:
        raise BadRequest("vehicleId must be a positive integer")
    if payload.commandId is not None and payload.commandId <= 0:
        raise BadRequest("commandId must be a positive integer when provided")
    call_procedure_no_result(
        "spRegisterHistory",
        [payload.vehicleId, payload.commandId, payload.source],
    )
    return {"status": "ok"}


@router.get(
    "/{vehicle_id}",
    response_model=list[HistoryEntry],
    summary="spGetHistory",
)
def get_history(vehicle_id: int):
    if vehicle_id <= 0:
        raise BadRequest("vehicle_id must be a positive integer")
    return call_procedure("spGetHistory", [vehicle_id])