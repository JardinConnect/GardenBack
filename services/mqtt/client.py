import paho.mqtt.client as mqtt
from typing import Callable, Dict, List
from settings import settings

# Client MQTT global
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Registre : topic_pattern → liste de callbacks
_handlers: Dict[str, List[Callable[[str, str], None]]] = {}


def register_handler(topic: str, handler: Callable[[str, str], None]):
    """
    Enregistre un handler pour un topic MQTT.
    Le handler recevra (topic, payload) en arguments.
    Doit être appelé AVANT connect_mqtt().
    """
    if topic not in _handlers:
        _handlers[topic] = []
    _handlers[topic].append(handler)
    print(f"[MQTT] Handler enregistré pour le topic: {topic}")


def on_connect(client, userdata, flags, reason_code, properties):
    if not reason_code.is_failure:
        print("[MQTT] Connecté au broker")
        for topic in _handlers:
            client.subscribe(topic)
            print(f"[MQTT] Abonné au topic: {topic}")
    else:
        print(f"[MQTT] Échec de connexion, code: {reason_code}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[MQTT] Message reçu -> Topic: {msg.topic}, Payload: {payload}")

    for topic_pattern, handlers in _handlers.items():
        if mqtt.topic_matches_sub(topic_pattern, msg.topic):
            for handler in handlers:
                try:
                    handler(msg.topic, payload)
                except Exception as e:
                    print(f"[MQTT] Erreur handler sur {topic_pattern}: {e}")
                    import traceback
                    traceback.print_exc()


def connect_mqtt():
    """Initialise et connecte le client MQTT."""
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, settings.MQTT_KEEPALIVE)
        mqtt_client.loop_start()
        print(f"[MQTT] Connexion au broker {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
    except Exception as e:
        print(f"[MQTT] Erreur de connexion au broker: {e}")


def publish(topic: str, message: str):
    """Publie un message sur un topic MQTT. Peut être appelé par n'importe quel service."""
    result = mqtt_client.publish(topic, message)
    status = result.rc
    if status == 0:
        print(f"[MQTT] Message envoyé -> Topic: {topic}")
    else:
        print(f"[MQTT] Échec envoi -> Topic: {topic}, Code: {status}")


def disconnect_mqtt():
    """Déconnecte proprement le client MQTT."""
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print("[MQTT] Déconnecté du broker")