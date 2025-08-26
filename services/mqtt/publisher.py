import paho.mqtt.client as mqtt
import time

BROKER = "localhost"
PORT = 1883
TOPIC = "test/topic"

client = mqtt.Client()
client.connect(BROKER, PORT, 60)

for i in range(5):
    message = f"Hello MQTT {i}"
    print(f"[PUBLISHER] Publication: {message}")
    client.publish(TOPIC, message)
    time.sleep(1)

client.disconnect()
print("[PUBLISHER] Déconnecté")
