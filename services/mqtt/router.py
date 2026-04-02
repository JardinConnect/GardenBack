from fastapi import APIRouter
from services.mqtt.client import publish as mqtt_publish
from settings import settings

router = APIRouter()

@router.post("/publish/")
def publish(topic: str = settings.MQTT_TOPIC, message: str = "Hello MQTT"):
    """
    Publie un message sur un topic MQTT.
    """
    mqtt_publish(topic, message)
    return {"status": "ok", "topic": topic, "message": message}
