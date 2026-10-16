import logging

from fastapi import APIRouter, status

from ..database import call_procedure, call_procedure_no_result
from ..demo_runner import (
    DemoAlreadyRunning,
    DemoNotFound,
    start_demo,
)
from ..errors import BadRequest, Conflict, ResourceNotFound
from ..schemas import (
    Demo,
    DemoCreate,
    DemoMovement,
    DemoMovementCreate,
    DemoMovementUpdate,
    DemoUpdate,
)

logger = logging.getLogger("iotvehicule.demos")

router = APIRouter(prefix="/demos", tags=["Demos"])


# ------------------------------ CRUD -------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict,
             summary="spCreateDemo")
def create_demo(payload: DemoCreate):
    rows = call_procedure(
        "spCreateDemo", [payload.vehicleId, payload.name, payload.description]
    )
    if not rows or "demoId" not in rows[0]:
        raise Conflict("Demo could not be created")
    return rows[0]


@router.get("/vehicle/{vehicle_id}", response_model=list[Demo],
            summary="spGetDemos")
def list_demos(vehicle_id: int):
    if vehicle_id <= 0:
        raise BadRequest("vehicle_id must be a positive integer")
    return call_procedure("spGetDemos", [vehicle_id])


@router.put("/{demo_id}", summary="spUpdateDemo")
def update_demo(demo_id: int, payload: DemoUpdate):
    if demo_id <= 0:
        raise BadRequest("demo_id must be a positive integer")
    call_procedure_no_result(
        "spUpdateDemo",
        [demo_id, payload.name, payload.description, payload.isActive],
    )
    return {"status": "ok", "demoId": demo_id}


@router.delete("/{demo_id}", summary="spDeleteDemo")
def delete_demo(demo_id: int):
    if demo_id <= 0:
        raise BadRequest("demo_id must be a positive integer")
    call_procedure_no_result("spDeleteDemo", [demo_id])
    return {"status": "ok", "demoId": demo_id}


# ------------------------------ Movements --------------------------------
@router.post("/movements", status_code=status.HTTP_201_CREATED,
             summary="spAddDemoMovement")
def add_demo_movement(payload: DemoMovementCreate):
    call_procedure_no_result(
        "spAddDemoMovement",
        [payload.demoId, payload.commandId, payload.sortOrder,
         payload.durationMs, payload.pauseMs],
    )
    return {"status": "ok"}


@router.get("/{demo_id}/movements", response_model=list[DemoMovement],
            summary="spGetDemoMovements")
def get_demo_movements(demo_id: int):
    if demo_id <= 0:
        raise BadRequest("demo_id must be a positive integer")
    return call_procedure("spGetDemoMovements", [demo_id])


@router.put("/movements/{movement_id}", summary="spUpdateDemoMovement")
def update_demo_movement(movement_id: int, payload: DemoMovementUpdate):
    if movement_id <= 0:
        raise BadRequest("movement_id must be a positive integer")
    call_procedure_no_result(
        "spUpdateDemoMovement",
        [movement_id, payload.commandId, payload.sortOrder,
         payload.durationMs, payload.pauseMs],
    )
    return {"status": "ok", "demoMovementId": movement_id}


@router.delete("/movements/{movement_id}", summary="spDeleteDemoMovement")
def delete_demo_movement(movement_id: int):
    if movement_id <= 0:
        raise BadRequest("movement_id must be a positive integer")
    call_procedure_no_result("spDeleteDemoMovement", [movement_id])
    return {"status": "ok", "demoMovementId": movement_id}


# ------------------------------ Start demo --------------------------------
@router.post(
    "/{demo_id}/run",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a demo run in the background",
)
async def run_demo_endpoint(demo_id: int):
    if demo_id <= 0:
        raise BadRequest("demo_id must be a positive integer")
    try:
        return await start_demo(demo_id)
    except DemoAlreadyRunning as exc:
        raise Conflict(str(exc))
    except DemoNotFound as exc:
        raise ResourceNotFound(str(exc))