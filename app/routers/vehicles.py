from fastapi import APIRouter, status

from ..database import call_procedure, call_procedure_no_result
from ..errors import BadRequest, Conflict, ResourceNotFound
from ..schemas import Vehicle, VehicleCreate, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    summary="spCreateVehicle",
)
def create_vehicle(payload: VehicleCreate):
    rows = call_procedure(
        "spCreateVehicle",
        [payload.name, payload.model, payload.description, payload.microcontroller],
    )
    if not rows or "vehicleId" not in rows[0]:
        raise Conflict("Vehicle could not be created")
    return rows[0]


@router.get("", response_model=list[Vehicle], summary="spGetVehicles")
def list_vehicles():
    return call_procedure("spGetVehicles")


@router.get("/{vehicle_id}", response_model=Vehicle, summary="spGetVehicle")
def get_vehicle(vehicle_id: int):
    if vehicle_id <= 0:
        raise BadRequest("vehicle_id must be a positive integer")
    rows = call_procedure("spGetVehicle", [vehicle_id])
    if not rows:
        raise ResourceNotFound(f"Vehicle {vehicle_id} not found")
    return rows[0]


@router.put("/{vehicle_id}", summary="spUpdateVehicle")
def update_vehicle(vehicle_id: int, payload: VehicleUpdate):
    if vehicle_id <= 0:
        raise BadRequest("vehicle_id must be a positive integer")
    call_procedure_no_result(
        "spUpdateVehicle",
        [
            vehicle_id,
            payload.name,
            payload.model,
            payload.description,
            payload.microcontroller,
            payload.isActive,
        ],
    )
    return {"status": "ok", "vehicleId": vehicle_id}


@router.delete("/{vehicle_id}", summary="spDeleteVehicle")
def delete_vehicle(vehicle_id: int):
    if vehicle_id <= 0:
        raise BadRequest("vehicle_id must be a positive integer")
    call_procedure_no_result("spDeleteVehicle", [vehicle_id])
    return {"status": "ok", "vehicleId": vehicle_id}