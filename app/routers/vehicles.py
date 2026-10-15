from fastapi import APIRouter, HTTPException, status

from ..database import call_procedure, call_procedure_no_result
from ..schemas import Vehicle, VehicleCreate, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED,
             summary="spCreateVehicle")
def create_vehicle(payload: VehicleCreate):
    rows = call_procedure(
        "spCreateVehicle",
        [payload.name, payload.model, payload.description, payload.microcontroller],
    )
    if not rows:
        raise HTTPException(status_code=500, detail="Vehicle could not be created")
    return rows[0]


@router.get("", response_model=list[Vehicle], summary="spGetVehicles")
def list_vehicles():
    return call_procedure("spGetVehicles")


@router.get("/{vehicle_id}", response_model=list[Vehicle], summary="spGetVehicle")
def get_vehicle(vehicle_id: int):
    rows = call_procedure("spGetVehicle", [vehicle_id])
    if not rows:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return rows


@router.put("/{vehicle_id}", summary="spUpdateVehicle")
def update_vehicle(vehicle_id: int, payload: VehicleUpdate):
    call_procedure_no_result(
        "spUpdateVehicle",
        [vehicle_id, payload.name, payload.model, payload.description,
         payload.microcontroller, payload.isActive],
    )
    return {"status": "ok", "vehicleId": vehicle_id}


@router.delete("/{vehicle_id}", summary="spDeleteVehicle")
def delete_vehicle(vehicle_id: int):
    call_procedure_no_result("spDeleteVehicle", [vehicle_id])
    return {"status": "ok", "vehicleId": vehicle_id}