import time
from unittest.mock import patch
import paho.mqtt.client as mqtt
import pytest
from db.models import Analytic, Area, Cell, Sensor
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


def test_process_data_message_success(db_session, capsys):
    """
    Teste le traitement d'un message MQTT valide et la création des entrées en base de données.
    """
    # 1. Préparation de la structure : Area -> Cell -> Sensor
    
    # Créer une area de test
    test_area = Area(name="Test Area", color="#FFFFFF")
    db_session.add(test_area)
    db_session.commit()
    
    # Créer une cellule dans cette area
    test_cell = Cell(name="Test Cell", area_id=test_area.id, deviceID="REPO-TEST-DEVICE-17")
    db_session.add(test_cell)
    db_session.commit()
    
    # Créer un capteur de test dans cette cellule
    sensor_uid_test = "TA-SENSOR-01" # Utiliser un préfixe valide (TA pour Air Temperature)
    test_sensor = Sensor(
        sensor_id=sensor_uid_test,
        sensor_type="temperature",
        cell_id=test_cell.id
    )
    db_session.add(test_sensor)
    db_session.commit()
    db_session.refresh(test_sensor)
    test_sensor_id = test_sensor.id

    print(f"\n[DEBUG] Sensor créé avec ID: {test_sensor_id}, sensor_id: {test_sensor.sensor_id}")

    # Vérifier que le capteur existe bien
    check_sensor = db_session.query(Sensor).filter(Sensor.sensor_id == sensor_uid_test).first()
    assert check_sensor is not None, "Sensor should exist in database"
    print(f"[DEBUG] Sensor trouvé en DB: {check_sensor.sensor_id}")

    # Message MQTT valide
    # Format: B|D|timestamp|sensor_uid|données|E
    payload = f"B|D|2025-11-20T18:32:41Z|{sensor_uid_test}|1TA32;1HS45;1L200;1B97|E"
    print(f"[DEBUG] Payload à traiter: {payload}")

    # 2. Action
    # Mock de SessionLocal pour retourner notre session de test
    def mock_session_local():
        """Retourne directement la session de test sans la fermer"""
        return db_session
    
    with patch('services.mqtt.client.SessionLocal', mock_session_local):
        process_data_message(payload)
    
    # Capturer les logs pour debug
    captured = capsys.readouterr()
    print(f"[DEBUG] Output capturé:\n{captured.out}")
    if captured.err:
        print(f"[DEBUG] Erreurs capturées:\n{captured.err}")

    # 3. Vérification
    # On vérifie que les 4 entrées analytiques ont été créées
    db_session.commit()  # S'assurer que tout est commité
    analytics = db_session.query(Analytic).all()
    
    print(f"[DEBUG] Analytics trouvées: {len(analytics)}")
    for a in analytics:
        print(f"  - sensor_id={a.sensor_id}, sensor_code={a.sensor_code}, value={a.value}, type={a.analytic_type}")
    
    assert len(analytics) == 4, f"Expected 4 analytics, got {len(analytics)}. Check logs above for errors."

    # Les analytics devraient toutes être liées au même sensor_id
    for analytic in analytics:
        assert analytic.sensor_id == test_sensor_id, f"Analytic sensor_id mismatch: {analytic.sensor_id} != {test_sensor_id}"
        # Le sensor_code doit correspondre à l'ID du capteur qui a envoyé le message
        assert analytic.sensor_code == sensor_uid_test
    print("✅ Test de traitement du message de données passé avec succès !")


def test_process_data_message_sensor_not_found(db_session):
    """
    Teste le comportement quand le capteur n'existe pas en base de données.
    """
    # Message avec un sensor_uid qui n'existe pas
    payload = "B|D|2025-11-20T18:32:41Z|UNKNOWN-SENSOR|1TA32|E"

    # Action
    with patch('services.mqtt.client.SessionLocal', return_value=db_session):
        # La fonction devrait gérer l'erreur proprement
        process_data_message(payload)

    # Vérification : aucune donnée ne devrait être créée
    analytics = db_session.query(Analytic).all()
    assert len(analytics) == 0, "No analytics should be created for unknown sensor"

    print("✅ Test capteur inconnu passé avec succès !")


def test_process_data_message_invalid_format(db_session):
    """
    Teste le comportement avec un message au format invalide.
    """
    invalid_payloads = [
        "INVALID",
        "B|D|2025-11-20T18:32:41Z",  # Incomplet
        "B|X|2025-11-20T18:32:41Z|SENSOR|data|E",  # Type invalide
        "X|D|2025-11-20T18:32:41Z|SENSOR|data|E",  # Début invalide
    ]

    for payload in invalid_payloads:
        with patch('services.mqtt.client.SessionLocal', return_value=db_session):
            # La fonction devrait gérer l'erreur sans crash
            process_data_message(payload)

        # Vérification : aucune donnée ne devrait être créée
        analytics = db_session.query(Analytic).all()
        assert len(analytics) == 0, f"No analytics should be created for invalid payload: {payload}"

    print("✅ Test formats invalides passé avec succès !")


@pytest.fixture(scope="function")
def setup_test_sensor(db_session):
    """Fixture pour créer une structure complète Area -> Cell -> Sensor"""
    area = Area(name="Test Area", color="#FF0000")
    db_session.add(area)
    db_session.commit()
    
    cell = Cell(name="Test Cell", area_id=area.id, deviceID="REPO-TEST-DEVICE-17")
    db_session.add(cell)
    db_session.commit()
    
    sensor = Sensor(
        sensor_id="TA-01", # Utiliser un préfixe valide
        sensor_type="temperature",
        cell_id=cell.id
    )
    db_session.add(sensor)
    db_session.commit()
    
    return {"area": area, "cell": cell, "sensor": sensor}


def test_with_fixture(db_session, setup_test_sensor, capsys):
    """Exemple d'utilisation de la fixture"""
    sensor = setup_test_sensor["sensor"]
    
    print(f"\n[DEBUG] Test avec fixture - Sensor ID: {sensor.id}, sensor_id: {sensor.sensor_id}")
    
    payload = f"B|D|2025-11-20T18:32:41Z|{sensor.sensor_id}|1TA25|E"
    print(f"[DEBUG] Payload: {payload}")
    
    def mock_session_local():
        return db_session
    
    with patch('services.mqtt.client.SessionLocal', mock_session_local):
        process_data_message(payload)
    
    # Capturer les logs
    captured = capsys.readouterr()
    print(f"[DEBUG] Output:\n{captured.out}")
    
    db_session.commit()
    # L'objet 'sensor' a été détaché car process_data_message utilise sa propre session.
    # On le "rattache" à la session de test actuelle avant de l'utiliser.
    sensor = db_session.merge(sensor)

    analytics = db_session.query(Analytic).filter_by(sensor_id=sensor.id).all()
    
    print(f"[DEBUG] Analytics trouvées: {len(analytics)}")
    for a in analytics:
        print(f"  - {a.sensor_code} = {a.value}")
    
    assert len(analytics) > 0, f"Analytics should be created. Found {len(analytics)} analytics."
    
    print("✅ Test avec fixture passé avec succès !")