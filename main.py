from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.alert.router import router as alert_router
from services.api_gateway.router import router as gateway_router
from services.auth.router import router as auth_router
from services.data.router import router as data_router
from services.lora_gpio.router import router as lora_router
from services.mqtt.router import router as mqtt_router
from services.user.router import router as user_router

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


# Register routers
app.include_router(alert_router, prefix="/alert", tags=["Alert"])
app.include_router(gateway_router, prefix="/gateway", tags=["API Gateway"])
app.include_router(auth_router, tags=["Authentication"])
app.include_router(data_router, prefix="/data", tags=["Data"])
app.include_router(lora_router, prefix="/lora", tags=["Lora GPIO"])
app.include_router(mqtt_router, tags=["MQTT"])
app.include_router(user_router, tags=["User"])


@app.on_event("startup")
def startup_event():
    """
    Actions à effectuer au démarrage de l'application.
    """
    print("[FASTAPI] Démarrage de l'application...")
    connect_mqtt()  # Démarre le client MQTT en background
