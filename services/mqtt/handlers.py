import json

from db.database import SessionLocal
from services.analytics.repository import create_analytic as create_analytic_repo
from services.analytics.schemas import AnalyticCreate
from db.models import Sensor, Alert, AlertEvent, Cell, SeverityEnum
from services.mqtt.pending_acks import resolve_ack
from services.area.service import get_full_location_path_for_cell


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
    if "event" in message and "data" not in message:
        print(f"[MQTT][handler] Événement reçu (ack): {message}")
        return

    uid = message.get("uid")
    timestamp_str = message.get("timestamp")
    data = message.get("data")

    if not uid or not timestamp_str or not data:
        print(f"[MQTT][handler] Message incomplet, ignoré: {message}")
        return

    db = SessionLocal()
    try:
        cell = db.query(Cell).filter(Cell.deviceID == uid).first()
        if not cell or cell.id is None:
            print(f"[MQTT][handler] Cellule avec UID '{uid}' non trouvée. Message ignoré.")
            return
        sensors = db.query(Sensor).filter(Sensor.cell_id == cell.id).all()
        if not sensors or len(sensors) == 0:
            print(f"[MQTT][handler] Capteurs avec cell_id '{cell.id}' non trouvés. Message ignoré.")
            return

        for sensor_code, value in data.items():
            sensor = next((s for s in sensors if s.sensor_id == sensor_code.upper()), None)
            if not sensor:
                print(f"[MQTT][handler] Capteur avec code '{sensor_code}' non trouvé. Message ignoré.")
                continue
            analytic_data = AnalyticCreate(
                sensor_code=sensor.sensor_id,
                value=float(value),
                timestamp=timestamp_str,
                sensor_id=sensor.id,
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


def handle_config_ack(topic: str, raw_payload: str):
    """
    Handler pour les acquittements de configuration envoyés par le device.

    Format attendu :
        {
            "ack_id": "<correlation-id>",
            "status": "ok" | "error",
            "message": "..."          (optionnel)
        }

    Résout l'asyncio.Event correspondant dans le registre pending_acks
    pour débloquer le générateur SSE qui attend la confirmation.
    """
    try:
        message = json.loads(raw_payload)
    except (json.JSONDecodeError, TypeError):
        print(f"[MQTT][handler] Config ack non-JSON ignoré: {raw_payload}")
        return

    # ack_id = message.get("ack_id")
    # if not ack_id:
    #     print(f"[MQTT][handler] Config ack sans ack_id, ignoré: {message}")
    #     return

    # resolved = resolve_ack(ack_id, message)
    resolve = message.get("status") == "received"
    if resolve:
        print(f"[MQTT][handler] Config ack résolu: {resolve}")
    else:
        print(f"[MQTT][handler] Config ack orphelin (pas de requête en attente): {message}")


def handle_pairing_ack(topic: str, raw_payload: str):
    """
    Handler pour les acquittements de pairing envoyés par le device.

    Format attendu :
        {
            "ack_id": "<correlation-id>",
            "status": "ok" | "error",
            "device_id": "...",
            "message": "..."          (optionnel)
        }

    Résout l'asyncio.Event correspondant dans le registre pending_acks
    pour débloquer le générateur SSE de pairing.
    """
    try:
        message = json.loads(raw_payload)
    except (json.JSONDecodeError, TypeError):
        print(f"[MQTT][handler] Pairing ack non-JSON ignoré: {raw_payload}")
        return

    ack_id = message.get("ack_id")
    if not ack_id:
        print(f"[MQTT][handler] Pairing ack sans ack_id, ignoré: {message}")
        return

    resolved = resolve_ack(ack_id, message)
    if resolved:
        print(f"[MQTT][handler] Pairing ack résolu: {ack_id} -> {message.get('status')}")
    else:
        print(f"[MQTT][handler] Pairing ack orphelin (pas de requête en attente): {ack_id}")


def handle_alert_trigger(topic: str, raw_payload: str):
    """
    Handler pour les triggers d'alertes envoyés par le device.

    Le device détecte un dépassement de seuil et publie sur garden/alerts/trigger.
    Ce handler crée un AlertEvent en base de données.

    Format attendu :
        {
            "alert_id": "<uuid>",
            "cell_uid": "004b1235062c",
            "sensor_type": "HA",
            "sensor_index": 1,
            "value": 54.3,
            "trigger_type": "W" | "C",
            "timestamp": "2026-03-30T18:00:00Z"
        }
    """
    try:
        message = json.loads(raw_payload)
    except (json.JSONDecodeError, TypeError):
        print(f"[MQTT][handler] Alert trigger non-JSON ignoré: {raw_payload}")
        return

    alert_id = message.get("alert_id")
    cell_uid = message.get("cell_uid")
    sensor_type = message.get("sensor_type")
    sensor_index = message.get("sensor_index")
    value = message.get("value")
    trigger_type = message.get("trigger_type")
    timestamp_str = message.get("timestamp")

    if not all([alert_id, cell_uid, sensor_type, value is not None, trigger_type, timestamp_str]):
        print(f"[MQTT][handler] Alert trigger incomplet, ignoré: {message}")
        return

    # Mapper trigger_type vers SeverityEnum
    severity_map = {"C": SeverityEnum.CRITICAL, "W": SeverityEnum.WARNING}
    severity = severity_map.get(trigger_type)
    if not severity:
        print(f"[MQTT][handler] trigger_type inconnu '{trigger_type}', ignoré.")
        return

    db = SessionLocal()
    try:
        # Récupérer l'alerte
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            print(f"[MQTT][handler] Alerte '{alert_id}' non trouvée. Trigger ignoré.")
            return

        # Récupérer la cellule via son deviceID
        cell = db.query(Cell).filter(Cell.deviceID == cell_uid).first()
        if not cell:
            print(f"[MQTT][handler] Cellule avec deviceID '{cell_uid}' non trouvée. Trigger ignoré.")
            return

        # Extraire les seuils depuis la config de l'alerte
        threshold_min = 0.0
        threshold_max = 0.0
        for s in (alert.sensors or []):
            if s.get("type") == sensor_type and s.get("index") == sensor_index:
                if trigger_type == "C" and "criticalRange" in s:
                    threshold_min = s["criticalRange"].get("min", 0.0)
                    threshold_max = s["criticalRange"].get("max", 0.0)
                elif trigger_type == "W" and s.get("warningRange"):
                    threshold_min = s["warningRange"].get("min", 0.0)
                    threshold_max = s["warningRange"].get("max", 0.0)
                break

        # Construire le chemin de localisation
        cell_location = get_full_location_path_for_cell(cell)

        # Créer l'AlertEvent
        event = AlertEvent(
            alert_id=alert.id,
            alert_title=alert.title,
            cell_id=cell.id,
            cell_name=cell.name,
            cell_location=cell_location or "",
            sensor_type=sensor_type,
            severity=severity,
            value=float(value),
            threshold_min=threshold_min,
            threshold_max=threshold_max,
        )
        db.add(event)
        db.commit()
        print(f"[MQTT][handler] AlertEvent créé: alert={alert.title}, cell={cell.name}, "
              f"type={sensor_type}, severity={severity.value}, value={value}")

    except Exception as e:
        print(f"[MQTT][handler] Erreur traitement alert trigger: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
