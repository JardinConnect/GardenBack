import time
from unittest.mock import patch
import paho.mqtt.client as mqtt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, Analytic, Node, Space
from services.mqtt.client import process_data_message
 
BROKER = "localhost"
PORT = 1883
TOPIC = "test/topic"


def subscriber():
    def on_connect(client, userdata, flags, rc):
        print("[TEST SUB] Connecté")
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        print(f"[TEST SUB] {msg.topic}: {msg.payload.decode()}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()


@pytest.fixture(scope="function")
def db_session():
    """Crée une base de données SQLite en mémoire pour un test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def publisher():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
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
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
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


def test_process_data_message_success(db_session):
    """
    Teste le traitement d'un message MQTT valide et la création des entrées en base de données.
    """
    # 1. Préparation
    # Message MQTT valide
    node_uid_test = "4C01"
    payload = f"B|D|2025-11-20T18:32:41Z|{node_uid_test}|1TA32;1HS45;1L200;1B97|E"

    # On doit créer un noeud dans la DB de test pour que la fonction le trouve
    test_space = Space(name="Test Space")
    db_session.add(test_space)
    db_session.commit()
    test_node = Node(uid=node_uid_test, space_id=test_space.id)
    db_session.add(test_node)
    db_session.commit()
    test_node_id = test_node.id  # On récupère l'ID avant que la session ne soit fermée

    # 2. Action
    # On injecte la session de test dans la fonction qui crée la session
    with patch('services.mqtt.client.SessionLocal', return_value=db_session):
        process_data_message(payload)

    # 3. Vérification
    # On vérifie que les 4 entrées analytiques ont été créées
    analytics = db_session.query(Analytic).all()
    assert len(analytics) == 4

    # On vérifie les données pour chaque capteur
    data_map = {analytic.sensor_code: analytic for analytic in analytics}

    assert "TA-1" in data_map
    assert data_map["TA-1"].value == 32.0
    assert data_map["TA-1"].node_id == test_node_id

    assert "HS-1" in data_map
    assert data_map["HS-1"].value == 45.0

    assert "L-1" in data_map
    assert data_map["L-1"].value == 200.0

    assert "B-1" in data_map
    assert data_map["B-1"].value == 97.0

    print("✅ Test de traitement du message de données passé avec succès !")
