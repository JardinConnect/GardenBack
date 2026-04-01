import json

from db.database import SessionLocal
from services.analytics.repository import create_analytic as create_analytic_repo
from services.analytics.schemas import AnalyticCreate
from db.models import Sensor


def handle_sensor_data(topic: str, raw_payload: str):
    """
    Handler pour les messages de données capteurs au format JSON.

    Format attendu :
        {
            "uid": "TA-SENSOR-01",
            "timestamp": "2025-11-20T18:32:41Z",
            "payload": { "TA-01": 25.0, "HS-01": 60.0 }
        }

    Un message contenant uniquement "event" (acquittement) est ignoré.
    """
    try:
        message = json.loads(raw_payload)
    except (json.JSONDecodeError, TypeError):
        print(f"[MQTT][handler] Payload non-JSON ignoré: {raw_payload}")
        return

    # Ignorer les acquittements / événements simples
    if "event" in message and "payload" not in message:
        print(f"[MQTT][handler] Événement reçu (ack): {message}")
        return

    uid = message.get("uid")
    timestamp_str = message.get("timestamp")
    data = message.get("payload")

    if not uid or not timestamp_str or not data:
        print(f"[MQTT][handler] Message incomplet, ignoré: {message}")
        return

    db = SessionLocal()
    try:
        sensor = db.query(Sensor).filter(Sensor.sensor_id == uid).first()
        if not sensor or sensor.id is None:
            print(f"[MQTT][handler] Capteur avec UID '{uid}' non trouvé. Message ignoré.")
            return

        sensor_id = sensor.id

        for sensor_code, value in data.items():
            analytic_data = AnalyticCreate(
                sensor_code=sensor_code,
                value=float(value),
                timestamp=timestamp_str,
                sensor_id=sensor_id,
            )
            try:
                create_analytic_repo(db, analytic_data)
                print(f"[MQTT][handler] Analytique créée: {sensor_code}={value}")
            except Exception as e:
                print(f"[MQTT][handler] Erreur création analytique pour {sensor_code}: {e}")

    except Exception as e:
        print(f"[MQTT][handler] Erreur traitement message: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
