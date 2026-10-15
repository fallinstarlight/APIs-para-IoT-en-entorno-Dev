from fastapi import APIRouter, status

from ..database import call_procedure, call_procedure_no_result
from ..schemas import HistoryEntry, HistoryRegister

router = APIRouter(prefix="/history", tags=["History"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="spRegisterHistory")
def register_history(payload: HistoryRegister):
    call_procedure_no_result(
        "spRegisterHistory",
        [payload.vehicleId, payload.commandId, payload.source],
    )
    return {"status": "ok"}


@router.get("/{vehicle_id}", response_model=list[HistoryEntry],
            summary="spGetHistory")
def get_history(vehicle_id: int):
    return call_procedure("spGetHistory", [vehicle_id])