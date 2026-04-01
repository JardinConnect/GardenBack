import paho.mqtt.client as mqtt
from settings import settings
from datetime import datetime
from db.database import SessionLocal
from services.analytics.repository import create_analytic as create_analytic_repo
from db.models import Sensor
from services.analytics.schemas import AnalyticCreate

# Client MQTT global
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def process_data_message(message: dict):
    """Traite un message de données MQTT et l'enregistre en base de données."""
    try:
        print(f"[MQTT] Traitement du message de données: {message}")
        db = SessionLocal()
        try:
            uid = message.get("uid")
            timestamp_str = message.get("timestamp")
            payload = message.get("payload")
            sensor = db.query(Sensor).filter(Sensor.sensor_id == uid).first()
            if not sensor or sensor.id is None:
                print(f"[MQTT] Erreur: Capteur avec UID '{uid}' non trouvé. Message ignoré.")
                return
            
            sensor_id = sensor.id

            for key, value in payload.items():
                # Le sensor_code est maintenant l'ID complet du capteur
                sensor_code = sensor.sensor_id

                analytic_data = AnalyticCreate(
                    sensor_code=key,
                    value=value,
                    timestamp=timestamp_str,
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
        # mqtt_client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
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

def initialize_topic(topic: str):
    """Publie un message de test pour initialiser un topic MQTT."""
    test_message = "Test de connexion au topic"
    publish_message(topic, test_message)

def disconnect_mqtt():
    """Déconnecte proprement le client MQTT."""
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print("[MQTT] Déconnecté du broker")