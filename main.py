from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.alert.router import router as alert_router
from services.api_gateway.router import router as gateway_router
from services.auth.router import router as auth_router
from services.auth.bearer import JWTBearer
from services.analytics.router import router as data_router
from services.lora_gpio.router import router as lora_router
from services.area.router import router as area_router
from services.mqtt.router import router as mqtt_router
from services.user.router import router as user_router
from services.farm_state.router import router as farm_state_router

# Import du client MQTT
from services.mqtt.client import connect_mqtt


app = FastAPI(title="GardenConnect API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


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


# --- Routers ---

# Routeur public pour l'authentification (pas de protection ici)
app.include_router(auth_router, tags=["Authentication"])

# Routeurs protégés par JWT
auth_dependency = Depends(JWTBearer())
app.include_router(alert_router, prefix="/alert", tags=["Alert"], dependencies=[auth_dependency])
app.include_router(gateway_router, prefix="/gateway", tags=["API Gateway"], dependencies=[auth_dependency])
app.include_router(data_router, prefix="/data", tags=["Data"], dependencies=[auth_dependency])
app.include_router(lora_router, prefix="/lora", tags=["Lora GPIO"], dependencies=[auth_dependency])
app.include_router(area_router, prefix="/area", tags=["Area"], dependencies=[auth_dependency])
app.include_router(user_router, tags=["User"], dependencies=[auth_dependency])
app.include_router(farm_state_router, prefix="/farm-stats", tags=["Farm Stats"], dependencies=[auth_dependency])

# Autres routeurs (par exemple, pour des webhooks internes)
app.include_router(mqtt_router, tags=["MQTT"])


@app.on_event("startup")
def startup_event():
    print("[FASTAPI] Démarrage de l'application...")
    connect_mqtt()