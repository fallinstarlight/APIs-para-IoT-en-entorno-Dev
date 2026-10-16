from fastapi import APIRouter

from ..database import call_procedure, call_procedure_no_result
from ..errors import BadRequest, ResourceNotFound
from ..schemas import Status, StatusUpdate
from ..state_store import store

router = APIRouter(prefix="/status", tags=["Status"])


@router.post("", summary="spUpdateStatus (+ spRegisterHistory)")
async def update_status(payload: StatusUpdate):
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

    # Look up the command's name/code so the broadcast is self-describing.
    command_name = None
    code = None
    if payload.commandId is not None:
        try:
            for c in call_procedure("spGetVehicleCommands", [payload.vehicleId]):
                if c.get("commandId") == payload.commandId:
                    command_name = c.get("name")
                    code = c.get("code")
                    break
        except Exception:
            pass

    await store.set(
        payload.vehicleId,
        commandId=payload.commandId,
        commandName=command_name,
        code=code,
        isConnected=payload.isConnected,
        source=payload.source,
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