import json
import time
from unittest.mock import patch
import paho.mqtt.client as mqtt
import pytest
from db.models import Analytic, Area, Cell, Sensor
from services.mqtt.handlers import handle_sensor_data

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
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = lambda c, u, f, r: c.subscribe(TOPIC)
    client.connect(BROKER, PORT, 60)
    client.on_connect(client, None, None, 0)

    publisher()

    mock_connect.assert_called()
    mock_subscribe.assert_called_with(TOPIC)
    assert mock_publish.call_count == 3
    mock_disconnect.assert_called_once()

    print("✅ Test MQTT mocké passé avec succès !")


def test_handle_sensor_data_success(db_session, capsys):
    """
    Teste le traitement d'un message MQTT JSON valide et la création des entrées en base de données.
    """
    # 1. Préparation de la structure : Area -> Cell -> Sensor
    test_area = Area(name="Test Area", color="#FFFFFF")
    db_session.add(test_area)
    db_session.commit()

    test_cell = Cell(name="Test Cell", area_id=test_area.id, deviceID="TEST-DEVICE-001")
    db_session.add(test_cell)
    db_session.commit()

    # Create sensors that match the payload keys
    sensor_codes = ["TA-01", "HS-01", "L-01", "SB-01"]
    for code in sensor_codes:
        sensor = Sensor(
            sensor_id=code,
            sensor_type="generic",
            cell_id=test_cell.id
        )
        db_session.add(sensor)
    db_session.commit()

    # Message MQTT au format JSON
    payload = json.dumps({
        "uid": test_cell.deviceID,
        "timestamp": "2025-11-20T18:32:41Z",
        "payload": {
            "TA-01": 32.0,
            "HS-01": 45.0,
            "L-01": 200.0,
            "SB-01": 97.0
        }
    })

    # 2. Action
    def mock_session_local():
        return db_session

    with patch('services.mqtt.handlers.SessionLocal', mock_session_local):
        handle_sensor_data("test/topic", payload)

    captured = capsys.readouterr()
    print(f"[DEBUG] Output capturé:\n{captured.out}")

    # 3. Vérification
    db_session.commit()
    analytics = db_session.query(Analytic).all()

    print(f"[DEBUG] Analytics trouvées: {len(analytics)}")
    for a in analytics:
        print(f"  - sensor_id={a.sensor_id}, sensor_code={a.sensor_code}, value={a.value}, type={a.analytic_type}")

    assert len(analytics) == 4, f"Expected 4 analytics, got {len(analytics)}."

    print("✅ Test handle_sensor_data JSON passé avec succès !")


def test_handle_sensor_data_sensor_not_found(db_session):
    """
    Teste le comportement quand le capteur n'existe pas en base de données.
    """
    payload = json.dumps({
        "uid": "UNKNOWN-SENSOR",
        "timestamp": "2025-11-20T18:32:41Z",
        "payload": {"TA-01": 32.0}
    })

    with patch('services.mqtt.handlers.SessionLocal', return_value=db_session):
        handle_sensor_data("test/topic", payload)

    analytics = db_session.query(Analytic).all()
    assert len(analytics) == 0, "No analytics should be created for unknown sensor"
    print("✅ Test capteur inconnu passé avec succès !")


def test_handle_sensor_data_invalid_format(db_session):
    """
    Teste le comportement avec des messages au format invalide.
    """
    invalid_payloads = [
        "INVALID",                                              # Pas du JSON
        "{}",                                                    # JSON vide
        json.dumps({"uid": "X"}),                               # Incomplet
        json.dumps({"uid": "X", "timestamp": "2025-01-01"}),   # Pas de payload
    ]

    for payload in invalid_payloads:
        with patch('services.mqtt.handlers.SessionLocal', return_value=db_session):
            handle_sensor_data("test/topic", payload)

        analytics = db_session.query(Analytic).all()
        assert len(analytics) == 0, f"No analytics should be created for invalid payload: {payload}"

    print("✅ Test formats invalides passé avec succès !")


def test_handle_sensor_data_event_ack(db_session):
    """
    Teste qu'un message d'acquittement (event sans payload) est ignoré proprement.
    """
    payload = json.dumps({"event": "config_ack", "status": "ok"})

    with patch('services.mqtt.handlers.SessionLocal', return_value=db_session):
        handle_sensor_data("test/topic", payload)

    analytics = db_session.query(Analytic).all()
    assert len(analytics) == 0, "No analytics should be created for event/ack messages"
    print("✅ Test event ack passé avec succès !")


@pytest.fixture(scope="function")
def setup_test_sensor(db_session):
    """Fixture pour créer une structure complète Area -> Cell -> Sensor"""
    area = Area(name="Test Area", color="#FF0000")
    db_session.add(area)
    db_session.commit()

    cell = Cell(name="Test Cell", area_id=area.id, deviceID="TEST-DEVICE-001")
    db_session.add(cell)
    db_session.commit()

    sensor = Sensor(
        sensor_id="TA-01",
        sensor_type="temperature",
        cell_id=cell.id
    )
    db_session.add(sensor)
    db_session.commit()

    return {"area": area, "cell": cell, "sensor": sensor}


def test_with_fixture(db_session, setup_test_sensor, capsys):
    """Test avec fixture — message JSON"""
    sensor = setup_test_sensor["sensor"]
    cell = setup_test_sensor["cell"]

    payload = json.dumps({
        "uid": cell.deviceID,
        "timestamp": "2025-11-20T18:32:41Z",
        "payload": {"TA-01": 25.0}
    })

    def mock_session_local():
        return db_session

    with patch('services.mqtt.handlers.SessionLocal', mock_session_local):
        handle_sensor_data("test/topic", payload)

    captured = capsys.readouterr()
    print(f"[DEBUG] Output:\n{captured.out}")

    db_session.commit()
    sensor = db_session.merge(sensor)

    analytics = db_session.query(Analytic).filter_by(sensor_id=sensor.id).all()

    print(f"[DEBUG] Analytics trouvées: {len(analytics)}")
    for a in analytics:
        print(f"  - {a.sensor_code} = {a.value}")

    assert len(analytics) > 0, f"Analytics should be created. Found {len(analytics)} analytics."
    print("✅ Test avec fixture passé avec succès !")