from fastapi import APIRouter, HTTPException, status

from ..database import call_procedure, call_procedure_no_result
from ..schemas import Command, CommandCreate, CommandUpdate

router = APIRouter(prefix="/commands", tags=["Commands"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="spCreateCommand")
def create_command(payload: CommandCreate):
    rows = call_procedure(
        "spCreateCommand",
        [payload.vehicleId, payload.name, payload.code, payload.description],
    )
    if not rows:
        raise HTTPException(status_code=500, detail="Command could not be created")
    return rows[0]


@router.get("/vehicle/{vehicle_id}", response_model=list[Command],
            summary="spGetVehicleCommands")
def list_vehicle_commands(vehicle_id: int):
    return call_procedure("spGetVehicleCommands", [vehicle_id])


@router.put("/{command_id}", summary="spUpdateCommand")
def update_command(command_id: int, payload: CommandUpdate):
    call_procedure_no_result(
        "spUpdateCommand",
        [command_id, payload.name, payload.code, payload.description, payload.isActive],
    )
    return {"status": "ok", "commandId": command_id}


@router.delete("/{command_id}", summary="spDeleteCommand")
def delete_command(command_id: int):
    call_procedure_no_result("spDeleteCommand", [command_id])
    return {"status": "ok", "commandId": command_id}