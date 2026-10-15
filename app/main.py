from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import commands, demos, history, status, vehicles

app = FastAPI(
    title="IoT Vehicle API",
    description=(
        "REST + WebSocket API exposing the `IotVehicle` MySQL stored procedures.\n\n"
        "### Endpoints\n"
        "- **Vehicles** – CRUD via `spCreateVehicle`, `spGetVehicles`, "
        "`spGetVehicle`, `spUpdateVehicle`, `spDeleteVehicle`.\n"
        "- **Commands** – CRUD via `spCreateCommand`, `spGetVehicleCommands`, "
        "`spUpdateCommand`, `spDeleteCommand`.\n"
        "- **Status** – `spUpdateStatus` (also writes to history unless "
        "`source == 'DEMO'`) and `spGetStatus`.\n"
        "- **History** – `spRegisterHistory` and `spGetHistory`.\n"
        "- **Demos** – `spCreateDemo`, `spGetDemos`, `spUpdateDemo`, "
        "`spDeleteDemo`, plus movement CRUD and a WebSocket runner at "
        "`/demos/{demoId}/run`.\n\n"
        "### Demo WebSocket protocol\n"
        "Connect to `ws://<host>/demos/{demoId}/run`. The server emits:\n"
        "- `demo_start` – `{ demoId, totalMovements, vehicleId }`\n"
        "- `movement` – one per movement (id, command, durations)\n"
        "- `status_updated` – after each `spUpdateStatus` (no history written)\n"
        "- `pause` – before the inter-movement pause\n"
        "- `demo_end` / `error`\n"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehicles.router)
app.include_router(commands.router)
app.include_router(status.router)
app.include_router(history.router)
app.include_router(demos.router)


@app.get("/", tags=["Health"], summary="Service health check")
def root():
    return {"status": "ok", "service": "IoT Vehicle API"}