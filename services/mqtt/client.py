import paho.mqtt.client as mqtt
from settings import settings
from datetime import datetime
from db.database import SessionLocal
from services.analytics.repository import create_analytic as create_analytic_repo
from db.models import Sensor
from services.analytics.schemas import AnalyticCreate

# Client MQTT global
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def process_data_message(payload: str):
    """Traite un message de données MQTT et l'enregistre en base de données."""
    try:
        parts = payload.split('|')
        if len(parts) != 6 or parts[0] != 'B' or parts[5] != 'E' or parts[1] != 'D':
            print(f"[MQTT] Format de message invalide: {payload}")
            return

        _, _, timestamp_str, sensor_uid, datas_str, _ = parts
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")

        sensor_datas = datas_str.split(';')

        db = SessionLocal()
        try:
            # On cherche le capteur correspondant à l'UID
            # sensor_uid peut être par exemple "TC-A-TEMP-01"
            sensor = db.query(Sensor).filter(Sensor.sensor_id == sensor_uid, Sensor.deleted_at.is_(None)).first()
            if not sensor or sensor.id is None:
                print(f"[MQTT] Erreur: Capteur avec UID '{sensor_uid}' non trouvé. Message ignoré.")
                return
            
            sensor_id = sensor.id

            for data in sensor_datas:
                # NUMCAPTEUR + INITIALS + VALEUR
                # ex: 1TA32 -> num=1, initials=TA, value=32
                sensor_num = data[0]
                sensor_initials = data[1:3] if len(data) > 2 and data[1:3].isalpha() else data[1:2]
                value_str = data[len(sensor_num) + len(sensor_initials):]

                # Le sensor_code est maintenant l'ID complet du capteur
                sensor_code = sensor.sensor_id
                
                try:
                    value = float(value_str)
                except ValueError:
                    print(f"[MQTT] Valeur invalide pour le capteur {sensor_code}: {value_str}")
                    continue

                analytic_data = AnalyticCreate(
                    sensor_code=sensor_code,
                    value=value,
                    timestamp=timestamp,
                    sensor_id=sensor_id # Le champ est déjà correct ici, mais on vérifie
                )
                
                try:
                    # On passe le sensor_id à la fonction de création
                    create_analytic_repo(db, analytic_data)
                    print(f"[MQTT] Donnée analytique créée: {analytic_data.model_dump_json()}")
                except Exception as e_create:
                    print(f"[MQTT] Erreur lors de la création de l'analytique pour {sensor_code}: {e_create}")

        finally:
            db.close()

    except Exception as e:
        print(f"[MQTT] Erreur lors du traitement du message: {e}")
        import traceback
        traceback.print_exc()

def on_connect(client, userdata, flags, reason_code, properties):
    if not reason_code.is_failure:
        print("[MQTT] Connecté au broker")
        client.subscribe(settings.MQTT_TOPIC)
        print(f"[MQTT] Abonné au topic: {settings.MQTT_TOPIC}")
    else:
        print(f"[MQTT] Échec de connexion, code: {reason_code}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[MQTT] Message reçu -> Topic: {msg.topic}, Payload: {payload}")
    
    if payload.startswith("B|D|"):
        process_data_message(payload)

def connect_mqtt():
    """Initialise et connecte le client MQTT."""
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, settings.MQTT_KEEPALIVE)
        mqtt_client.loop_start()  # Lance le thread en arrière-plan
        print(f"[MQTT] Connexion au broker {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
    except Exception as e:
        print(f"[MQTT] Erreur de connexion au broker: {e}")

def publish_message(topic: str, message: str):
    """Publie un message sur un topic MQTT."""
    result = mqtt_client.publish(topic, message)
    status = result.rc
    if status == 0:
        print(f"[MQTT] Message envoyé -> Topic: {topic}, Message: {message}")
    else:
        print(f"[MQTT] Échec envoi -> Topic: {topic}, Code: {status}")

def disconnect_mqtt():
    """Déconnecte proprement le client MQTT."""
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print("[MQTT] Déconnecté du broker")