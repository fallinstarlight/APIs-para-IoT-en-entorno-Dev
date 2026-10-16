import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .errors import register_exception_handlers
from .routers import commands, demos, history, status, vehicles, ws_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger("iotvehicule")

app = FastAPI(
    title="IoT Vehicle API",
    description=(
        "REST + WebSocket API exposing the `IotVehicle` MySQL stored "
        "procedures. All validation is enforced server-side."
    ),
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(vehicles.router)
app.include_router(commands.router)
app.include_router(status.router)
app.include_router(history.router)
app.include_router(demos.router)
app.include_router(ws_status.router)


@app.get("/", tags=["Health"], summary="Service health check")
def root():
    return {"status": "ok", "service": "IoT Vehicle API"}