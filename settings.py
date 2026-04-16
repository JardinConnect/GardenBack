import os
from typing import Optional

class Settings():
    # Infos API
    PROJECT_NAME: str = "Modular Monolith API"
    VERSION: str = "1.0.0"

    # Base de données
    DATABASE_FILE_NAME: str = "database.db"
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT: str = os.path.dirname(BASE_DIR)
    DATABASE_PATH: str = os.path.join(PROJECT_ROOT, DATABASE_FILE_NAME)
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"

    # MQTT
    MQTT_BROKER: str = "mosquitto"
    MQTT_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_TOPIC: str = "test/topic"

    NETWORK_PROVIDER: str = "linux"

    _retention = os.environ.get("ACTION_LOGS_RETENTION_DAYS")
    ACTION_LOGS_RETENTION_DAYS: Optional[int] = (
        int(_retention) if _retention and str(_retention).isdigit() else None
    )

    _sse_max = os.environ.get("SSE_MAX_CONNECTIONS")
    SSE_MAX_CONNECTIONS: int = int(_sse_max) if _sse_max and str(_sse_max).isdigit() else 100
    _sse_hb = os.environ.get("SSE_HEARTBEAT_INTERVAL_SECONDS")
    try:
        SSE_HEARTBEAT_INTERVAL_SECONDS: float = float(_sse_hb) if _sse_hb is not None else 20.0
    except ValueError:
        SSE_HEARTBEAT_INTERVAL_SECONDS = 20.0

    class Config:
        env_file = ".env" 

settings = Settings()
