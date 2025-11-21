import paho.mqtt.client as mqtt
from settings import settings
from datetime import datetime
from db.database import SessionLocal
from services.analytics.repository import create_analytic as create_analytic_repo
from db.models import Node
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

        _, _, timestamp_str, node_uid, datas_str, _ = parts
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")

        sensor_datas = datas_str.split(';')

        db = SessionLocal()
        try:
            # On cherche le noeud correspondant à l'UID
            node = db.query(Node).filter(Node.uid == node_uid).first()
            if not node or node.id is None:
                print(f"[MQTT] Erreur: Noeud avec UID '{node_uid}' non trouvé. Message ignoré.")
                return
            
            node_id = node.id

            for data in sensor_datas:
                # NUMCAPTEUR + INITIALS + VALEUR
                # ex: 1TA32 -> num=1, initials=TA, value=32
                sensor_num = data[0]
                sensor_initials = data[1:3] if data[1:3].isalpha() else data[1:2]
                value_str = data[len(sensor_num) + len(sensor_initials):]

                # Le sensor_code est local au noeud
                sensor_code = f"{sensor_initials}-{sensor_num}"
                value = float(value_str)

                analytic_data = AnalyticCreate(
                    sensor_code=sensor_code,
                    value=value,
                    timestamp=timestamp,
                    node_id=node_id
                )
                # On passe le node_id à la fonction de création
                create_analytic_repo(db, analytic_data)
                print(f"[MQTT] Donnée analytique créée: {analytic_data.model_dump_json()}")
        finally:
            db.close()

    except Exception as e:
        print(f"[MQTT] Erreur lors du traitement du message: {e}")

def on_connect(client, userdata, flags, reason_code, properties):
    if not reason_code.is_failure:
        print("[MQTT] Connecté au broker")
        client.subscribe(settings.MQTT_TOPIC)
    else:
        print(f"[MQTT] Échec de connexion, code: {reason_code}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[MQTT] Message reçu -> Topic: {msg.topic}, Payload: {payload}")
    
    if payload.startswith("B|D|"):
        process_data_message(payload)

def connect_mqtt():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, settings.MQTT_KEEPALIVE)
    mqtt_client.loop_start()  # Lance le thread en arrière-plan

def publish_message(topic: str, message: str):
    result = mqtt_client.publish(topic, message)
    status = result.rc
    if status == 0:
        print(f"[MQTT] Message envoyé -> Topic: {topic}, Message: {message}")
    else:
        print(f"[MQTT] Échec envoi -> Topic: {topic}")
