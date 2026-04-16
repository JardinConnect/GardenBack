import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from services.alerts.router import router as alert_router
from services.audit.router import router as audit_router
from services.audit.purge import create_purge_task, cancel_purge_task
from services.auth.router import router as auth_router
from services.auth.bearer import JWTBearer
from services.analytics.router import router as data_router
from services.area.router import router as area_router
from services.user.router import router as user_router
from services.farm_state.router import public_router as farm_public_router, router as farm_state_router
from services.cell.router import router as cell_router
from services.network.router import router as network_router
from services.mqtt.client import connect_mqtt, register_handler
from services.sse.manager import SSEConnectionManager
from services.sse.runtime import clear_sse_runtime, configure_sse_runtime
from services.sse.router import router as sse_router
from services.mqtt.handlers import handle_sensor_data, handle_config_ack, handle_alert_trigger, handle_pairing_ack
from settings import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[FASTAPI] Démarrage de l'application...")
    register_handler(settings.MQTT_TOPIC_ANALYTICS, handle_sensor_data)
    register_handler(settings.MQTT_TOPIC_ALERTS_CONFIG_ACK, handle_config_ack)
    register_handler(settings.MQTT_TOPIC_PAIRING_ACK, handle_pairing_ack)
    register_handler(settings.MQTT_TOPIC_ALERTS_TRIGGER, handle_alert_trigger)
    connect_mqtt()
    loop = asyncio.get_running_loop()
    sse_manager = SSEConnectionManager(settings.SSE_MAX_CONNECTIONS)
    configure_sse_runtime(loop, sse_manager)
    app.state.sse_manager = sse_manager
    purge_task = create_purge_task()
    try:
        yield
    finally:
        clear_sse_runtime()
        await cancel_purge_task(purge_task)


app = FastAPI(title="GardenConnect API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status": exc.status_code,
                "method": request.method,
                "url": str(request.url)
            }
        },
    )

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
# The farm setup endpoint is public and should not require authentication.
app.include_router(farm_public_router, prefix="/api/farm", tags=["Farm State"])
app.include_router(network_router, prefix="/api/network", tags=["Network"])

# All routes below this line are protected by JWT authentication.
auth_dependency = Depends(JWTBearer())
app.include_router(alert_router, prefix="/api/alert", tags=["Alert"], dependencies=[auth_dependency])
app.include_router(audit_router, prefix="/api/action-logs", tags=["Audit"], dependencies=[auth_dependency])
app.include_router(data_router, prefix="/api/data", tags=["Data"], dependencies=[auth_dependency])
app.include_router(area_router, prefix="/api/area", tags=["Area"], dependencies=[auth_dependency])
app.include_router(user_router, prefix="/api/user", tags=["User"], dependencies=[auth_dependency])
app.include_router(farm_state_router, prefix="/api/farm", tags=["Farm State"], dependencies=[auth_dependency])
app.include_router(cell_router, prefix="/api/cell", tags=["Cell"], dependencies=[auth_dependency])
app.include_router(sse_router, prefix="/api/sse", tags=["SSE"])