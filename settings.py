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
    # MQTT_BROKER: str = "mosquitto"
    MQTT_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_TOPIC_ANALYTICS: str = "garden/analytics"
    MQTT_TOPIC_ALERTS_CONFIG: str = "garden/alerts/config"
    MQTT_TOPIC_PAIRING_ACK: str = "garden/pairing/ack"
    MQTT_TOPIC_PAIRING: str = "garden/pairing/request"
    MQTT_TOPIC_ALERTS_TRIGGER: str = "garden/alerts/trigger"
    MQTT_TOPIC_COMMAND_ACK: str = "garden/devices/command/ack"
    MQTT_TOPIC_ALERTS_CONFIG_ACK: str = "garden/alerts/config/ack"
    MQTT_TOPIC_DEVICES_COMMAND: str = "garden/devices/command"
    MQTT_TOPIC_DEVICES_SETTINGS: str = "garden/devices/settings"
    
    MQTT_USERNAME: Optional[str] = "mqtt_user"
    MQTT_PASSWORD: Optional[str] = "mqtt_password"

    # Mock MQTT
    # Lit la variable d'environnement MOCK_MQTT. Par défaut à 'False' si non définie.
    _mock_mqtt_str: str = os.environ.get("MOCK_MQTT", "False")
    MOCK_MQTT: bool = _mock_mqtt_str.lower() in ('true')

    NETWORK_PROVIDER: str = "linux"

    # Tailscale LocalAPI (socket Unix sur Linux / Raspberry Pi OS)
    TAILSCALE_SOCKET: str = os.environ.get(
        "TAILSCALE_SOCKET", "/var/run/tailscale/tailscaled.sock"
    )
    _mock_tailscale_str: str = os.environ.get("MOCK_TAILSCALE", "False")
    MOCK_TAILSCALE: bool = _mock_tailscale_str.lower() in ("true", "1", "yes")

    _retention = os.environ.get("ACTION_LOGS_RETENTION_DAYS")
    ACTION_LOGS_RETENTION_DAYS: Optional[int] = (
        int(_retention) if _retention and str(_retention).isdigit() else None
    )

    class Config:
        env_file = ".env" 

settings = Settings()
