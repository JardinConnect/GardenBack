import time
from unittest.mock import patch
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
        time.sleep(0.1)
    client.disconnect()


@patch.object(mqtt.Client, "connect", return_value=0)
@patch.object(mqtt.Client, "subscribe", return_value=(0, 1))
@patch.object(mqtt.Client, "publish", return_value=(0, 1))
@patch.object(mqtt.Client, "disconnect", return_value=0)
@patch.object(mqtt.Client, "loop_forever", return_value=None)
def test_mqtt_pub_sub(mock_loop, mock_disconnect, mock_publish, mock_subscribe, mock_connect):
    """Test mocké MQTT sans broker réel"""
    # On simule une exécution de subscriber sans thread ni boucle
    client = mqtt.Client()
    client.on_connect = lambda c, u, f, r: c.subscribe(TOPIC)
    client.connect(BROKER, PORT, 60)
    client.on_connect(client, None, None, 0)

    # On exécute le publisher
    publisher()

    # ✅ Vérifications
    mock_connect.assert_called()
    mock_subscribe.assert_called_with(TOPIC)
    assert mock_publish.call_count == 3
    mock_disconnect.assert_called_once()

    print("✅ Test MQTT mocké passé avec succès !")
