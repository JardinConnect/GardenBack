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
    MQTT_BROKER: str = "127.0.0.1"
    MQTT_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_TOPIC: str = "garden/analytics"
    MQTT_USERNAME: Optional[str] = "mqtt_user"
    MQTT_PASSWORD: Optional[str] = "mqtt_password"

    NETWORK_PROVIDER: str = "linux"

    _retention = os.environ.get("ACTION_LOGS_RETENTION_DAYS")
    ACTION_LOGS_RETENTION_DAYS: Optional[int] = (
        int(_retention) if _retention and str(_retention).isdigit() else None
    )

    class Config:
        env_file = ".env" 

settings = Settings()
