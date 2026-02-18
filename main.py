from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from services.alert.router import router as alert_router
from services.auth.router import router as auth_router
from services.auth.bearer import JWTBearer
from services.analytics.router import router as data_router
from services.area.router import router as area_router
from services.mqtt.router import router as mqtt_router
from services.user.router import router as user_router
from services.farm_state.router import router as farm_state_router
from services.cell.router import router as cell_router
from services.network.router import router as network_router
from services.mqtt.client import connect_mqtt


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[FASTAPI] Démarrage de l'application...")
    connect_mqtt()
    yield


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


auth_dependency = Depends(JWTBearer())
app.include_router(auth_router, tags=["Authentication"])
app.include_router(alert_router, prefix="/alert", tags=["Alert"], dependencies=[auth_dependency])
app.include_router(data_router, prefix="/data", tags=["Data"], dependencies=[auth_dependency])
app.include_router(area_router, prefix="/area", tags=["Area"], dependencies=[auth_dependency])
app.include_router(user_router, tags=["User"], dependencies=[auth_dependency])
app.include_router(farm_state_router, prefix="/farm-stats", tags=["Farm Stats"], dependencies=[auth_dependency])
app.include_router(cell_router, prefix="/cell", tags=["Cell"], dependencies=[auth_dependency])
app.include_router(network_router, prefix="/network", tags=["Network"], dependencies=[auth_dependency])
app.include_router(mqtt_router, tags=["MQTT"])