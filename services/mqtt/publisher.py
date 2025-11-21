import paho.mqtt.client as mqtt
import time
from datetime import datetime

BROKER = "localhost"
PORT = 1883
TOPIC = "test/topic"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

try:
    client.connect(BROKER, PORT, 60)
    timestamp = datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z')
    message = f"B|D|{timestamp}|TEST01|1TA25;1HS60;1B99|E"
    print(f"[PUBLISHER] Publication du message de test sur le topic '{TOPIC}': {message}")
    client.publish(TOPIC, message)
finally:
    client.disconnect()
    print("[PUBLISHER] Déconnecté")

client.disconnect()
print("[PUBLISHER] Déconnecté")
