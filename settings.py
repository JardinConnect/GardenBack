import os

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

    class Config:
        env_file = ".env" 

settings = Settings()
