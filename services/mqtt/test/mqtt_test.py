import threading
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "test/topic"

def subscriber():
    def on_connect(client, userdata, flags, rc):
        print("[TEST SUB] Connecté")
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        print(f"[TEST SUB] {msg.topic}: {msg.payload.decode()}")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

def publisher():
    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)
    for i in range(3):
        message = f"Test message {i}"
        print(f"[TEST PUB] Publication: {message}")
        client.publish(TOPIC, message)
        time.sleep(1)
    client.disconnect()

# Lancer le subscriber dans un thread
threading.Thread(target=subscriber, daemon=True).start()
time.sleep(2)  # Attendre que le subscriber soit prêt
publisher()
time.sleep(2)
