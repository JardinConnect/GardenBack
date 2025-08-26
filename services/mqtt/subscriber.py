import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "test/topic"

def on_connect(client, userdata, flags, rc):
    print(f"[SUBSCRIBER] Connecté avec le code {rc}")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    print(f"[SUBSCRIBER] Message reçu -> {msg.topic}: {msg.payload.decode()}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
print(f"[SUBSCRIBER] En écoute sur {TOPIC}...")
client.loop_forever()
