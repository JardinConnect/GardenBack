import paho.mqtt.client as mqtt
from settings import settings

# Client MQTT global
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Connecté au broker")
        client.subscribe(settings.MQTT_TOPIC)
    else:
        print(f"[MQTT] Échec de connexion, code: {rc}")

def on_message(client, userdata, msg):
    print(f"[MQTT] Message reçu -> Topic: {msg.topic}, Payload: {msg.payload.decode()}")

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
