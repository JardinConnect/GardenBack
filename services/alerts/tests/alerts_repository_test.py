"""

Tests de la couche base de données pour le module alertes.
La fixture `db_session` est fournie par conftest.py.
"""

import pytest
import uuid
from datetime import datetime, timedelta, UTC

from db.models import Alert, AlertEvent, Cell, Area, SeverityEnum


# =========================================================
# FIXTURES
# =========================================================

@pytest.fixture(scope="function")
def setup_area(db_session):
    """Crée une area de test."""
    area = Area(name="Parcelle Nord", color="#2E8B57")
    db_session.add(area)
    db_session.commit()
    return area


@pytest.fixture(scope="function")
def setup_cell(db_session, setup_area):
    """Crée une cellule de test."""
    cell = Cell(name="Rangée A", area_id=setup_area.id, deviceID="REPO-TEST-DEVICE-8")
    db_session.add(cell)
    db_session.commit()
    return cell


@pytest.fixture(scope="function")
def setup_alert(db_session, setup_cell):
    """Crée une alerte de test associée à la cellule."""
    alert = Alert(
        title="Alerte Température Air",
        is_active=True,
        warning_enabled=True,
        cell_ids=[str(setup_cell.id)],
        sensors=[
            {
                "type": "air_temperature",
                "index": 0,
                "criticalRange": {"min": -5.0, "max": 40.0},
                "warningRange": {"min": 0.0, "max": 35.0},
            }
        ],
    )
    db_session.add(alert)
    db_session.commit()
    return alert


@pytest.fixture(scope="function")
def setup_alert_event(db_session, setup_alert, setup_cell):
    """Crée un événement d'alerte de test."""
    event = AlertEvent(
        alert_id=setup_alert.id,
        alert_title=setup_alert.title,
        cell_id=setup_cell.id,
        cell_name=setup_cell.name,
        cell_location="Parcelle Nord",
        sensor_type="air_temperature",
        severity=SeverityEnum.CRITICAL,
        value=45.0,
        threshold_min=-5.0,
        threshold_max=40.0,
        is_archived=False,
    )
    db_session.add(event)
    db_session.commit()
    return event


# =========================================================
# TESTS — Alert CRUD
# =========================================================

def test_create_alert(db_session, setup_cell):
    """Un alert peut être persisté et relu depuis la DB."""
    alert = Alert(
        title="Test Création",
        is_active=True,
        warning_enabled=True,
        cell_ids=[str(setup_cell.id)],
        sensors=[
            {
                "type": "soil_humidity",
                "index": 0,
                "criticalRange": {"min": 10.0, "max": 90.0},
                "warningRange": None,
            }
        ],
    )
    db_session.add(alert)
    db_session.commit()

    fetched = db_session.query(Alert).filter(Alert.id == alert.id).first()

    assert fetched is not None
    assert fetched.title == "Test Création"
    assert fetched.is_active is True
    assert fetched.warning_enabled is True
    assert len(fetched.sensors) == 1
    assert fetched.sensors[0]["type"] == "soil_humidity"


def test_cell_ids_stored_as_list(db_session, setup_cell):
    """Les cell_ids sont bien stockés et récupérés en tant que liste JSON."""
    second_cell_id = str(uuid.uuid4())
    alert = Alert(
        title="Multi-cellules",
        is_active=True,
        warning_enabled=False,
        cell_ids=[str(setup_cell.id), second_cell_id],
        sensors=[],
    )
    db_session.add(alert)
    db_session.commit()

    fetched = db_session.query(Alert).filter(Alert.id == alert.id).first()

    assert isinstance(fetched.cell_ids, list)
    assert len(fetched.cell_ids) == 2


def test_sensors_json_structure(db_session, setup_alert):
    """La structure JSON des capteurs est correctement persistée."""
    fetched = db_session.query(Alert).filter(Alert.id == setup_alert.id).first()
    sensor = fetched.sensors[0]

    assert "criticalRange" in sensor
    assert "warningRange" in sensor
    assert sensor["criticalRange"]["min"] == -5.0
    assert sensor["criticalRange"]["max"] == 40.0
    assert sensor["warningRange"]["min"] == 0.0
    assert sensor["warningRange"]["max"] == 35.0


def test_update_alert_title(db_session, setup_alert):
    """Un alert peut être mis à jour."""
    setup_alert.title = "Titre Modifié"
    db_session.commit()
    db_session.refresh(setup_alert)

    fetched = db_session.query(Alert).filter(Alert.id == setup_alert.id).first()

    assert fetched.title == "Titre Modifié"


def test_toggle_alert_active(db_session, setup_alert):
    """Le toggle is_active fonctionne dans les deux sens."""
    assert setup_alert.is_active is True

    setup_alert.is_active = False
    db_session.commit()
    db_session.refresh(setup_alert)
    assert setup_alert.is_active is False

    setup_alert.is_active = True
    db_session.commit()
    db_session.refresh(setup_alert)
    assert setup_alert.is_active is True


def test_delete_alert(db_session, setup_alert):
    """La suppression retire bien l'alert de la DB."""
    alert_id = setup_alert.id
    db_session.delete(setup_alert)
    db_session.commit()

    fetched = db_session.query(Alert).filter(Alert.id == alert_id).first()

    assert fetched is None


def test_delete_alert_cascades_events(db_session, setup_alert, setup_alert_event):
    """La suppression d'une alerte supprime en cascade ses événements."""
    event_id = setup_alert_event.id

    db_session.delete(setup_alert)
    db_session.commit()

    fetched_event = db_session.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    assert fetched_event is None


def test_filter_alerts_by_cell_id(db_session, setup_cell):
    """On peut filtrer les alertes par cell_id."""
    other_cell_id = str(uuid.uuid4())

    alert_matching = Alert(
        title="Alerte Cellule A",
        is_active=True,
        warning_enabled=False,
        cell_ids=[str(setup_cell.id)],
        sensors=[],
    )
    alert_other = Alert(
        title="Alerte Autre Cellule",
        is_active=True,
        warning_enabled=False,
        cell_ids=[other_cell_id],
        sensors=[],
    )
    db_session.add_all([alert_matching, alert_other])
    db_session.commit()

    all_alerts = db_session.query(Alert).all()
    cell_id_str = str(setup_cell.id)
    filtered = [a for a in all_alerts if cell_id_str in [str(c) for c in a.cell_ids]]

    assert len(filtered) == 1
    assert filtered[0].title == "Alerte Cellule A"


# =========================================================
# TESTS — AlertEvent
# =========================================================

def test_create_alert_event(db_session, setup_alert, setup_cell):
    """Un événement d'alerte peut être créé et récupéré."""
    event = AlertEvent(
        alert_id=setup_alert.id,
        alert_title=setup_alert.title,
        cell_id=setup_cell.id,
        cell_name=setup_cell.name,
        cell_location="Parcelle Nord",
        sensor_type="air_temperature",
        severity=SeverityEnum.WARNING,
        value=37.5,
        threshold_min=0.0,
        threshold_max=35.0,
        is_archived=False,
    )
    db_session.add(event)
    db_session.commit()

    fetched = db_session.query(AlertEvent).filter(AlertEvent.id == event.id).first()

    assert fetched is not None
    assert fetched.severity == SeverityEnum.WARNING
    assert fetched.value == 37.5
    assert fetched.is_archived is False


def test_archive_event(db_session, setup_alert_event):
    """Archiver un événement met is_archived à True."""
    assert setup_alert_event.is_archived is False

    setup_alert_event.is_archived = True
    db_session.commit()
    db_session.refresh(setup_alert_event)

    assert setup_alert_event.is_archived is True


def test_filter_non_archived_events(db_session, setup_alert, setup_cell):
    """Seuls les événements non archivés sont retournés par le filtre."""
    active_event = AlertEvent(
        alert_id=setup_alert.id, alert_title=setup_alert.title,
        cell_id=setup_cell.id, cell_name=setup_cell.name, cell_location="",
        sensor_type="air_temperature", severity=SeverityEnum.CRITICAL,
        value=50.0, threshold_min=-5.0, threshold_max=40.0, is_archived=False,
    )
    archived_event = AlertEvent(
        alert_id=setup_alert.id, alert_title=setup_alert.title,
        cell_id=setup_cell.id, cell_name=setup_cell.name, cell_location="",
        sensor_type="air_temperature", severity=SeverityEnum.WARNING,
        value=36.0, threshold_min=0.0, threshold_max=35.0, is_archived=True,
    )
    db_session.add_all([active_event, archived_event])
    db_session.commit()

    non_archived = (
        db_session.query(AlertEvent)
        .filter(AlertEvent.is_archived == False)  # noqa: E712
        .all()
    )

    assert len(non_archived) == 1
    assert non_archived[0].value == 50.0


def test_filter_events_by_severity(db_session, setup_alert, setup_cell):
    """Le filtre par sévérité retourne uniquement les événements correspondants."""
    db_session.add(AlertEvent(
        alert_id=setup_alert.id, alert_title=setup_alert.title,
        cell_id=setup_cell.id, cell_name=setup_cell.name, cell_location="",
        sensor_type="air_temperature", severity=SeverityEnum.CRITICAL,
        value=50.0, threshold_min=-5.0, threshold_max=40.0, is_archived=False,
    ))
    db_session.add(AlertEvent(
        alert_id=setup_alert.id, alert_title=setup_alert.title,
        cell_id=setup_cell.id, cell_name=setup_cell.name, cell_location="",
        sensor_type="air_temperature", severity=SeverityEnum.WARNING,
        value=37.0, threshold_min=0.0, threshold_max=35.0, is_archived=False,
    ))
    db_session.commit()

    critical_events = (
        db_session.query(AlertEvent)
        .filter(AlertEvent.severity == SeverityEnum.CRITICAL)
        .all()
    )

    assert len(critical_events) == 1
    assert critical_events[0].value == 50.0


def test_archive_all_events(db_session, setup_alert, setup_cell):
    """Archiver tous les événements en une opération."""
    for val in [45.0, 46.0, 47.0]:
        db_session.add(AlertEvent(
            alert_id=setup_alert.id, alert_title=setup_alert.title,
            cell_id=setup_cell.id, cell_name=setup_cell.name, cell_location="",
            sensor_type="air_temperature", severity=SeverityEnum.CRITICAL,
            value=val, threshold_min=-5.0, threshold_max=40.0, is_archived=False,
        ))
    db_session.commit()

    active_events = (
        db_session.query(AlertEvent)
        .filter(AlertEvent.is_archived == False)  # noqa: E712
        .all()
    )
    count = len(active_events)
    for e in active_events:
        e.is_archived = True
    db_session.commit()

    remaining = (
        db_session.query(AlertEvent)
        .filter(AlertEvent.is_archived == False)  # noqa: E712
        .all()
    )

    assert count == 3
    assert len(remaining) == 0


def test_filter_events_by_cell(db_session, setup_alert, setup_cell):
    """Le filtre par cellule ne retourne que les événements de cette cellule."""
    other_cell_id = uuid.uuid4()

    db_session.add(AlertEvent(
        alert_id=setup_alert.id, alert_title=setup_alert.title,
        cell_id=setup_cell.id, cell_name=setup_cell.name, cell_location="",
        sensor_type="air_temperature", severity=SeverityEnum.CRITICAL,
        value=50.0, threshold_min=-5.0, threshold_max=40.0, is_archived=False,
    ))
    db_session.add(AlertEvent(
        alert_id=setup_alert.id, alert_title=setup_alert.title,
        cell_id=other_cell_id, cell_name="Autre Cellule", cell_location="",
        sensor_type="air_temperature", severity=SeverityEnum.CRITICAL,
        value=50.0, threshold_min=-5.0, threshold_max=40.0, is_archived=False,
    ))
    db_session.commit()

    events_for_cell = (
        db_session.query(AlertEvent)
        .filter(AlertEvent.cell_id == setup_cell.id)
        .all()
    )

    assert len(events_for_cell) == 1


def test_filter_events_by_date_range(db_session, setup_alert, setup_cell):
    """Le filtre par plage de dates retourne les bons événements."""
    now = datetime.now(UTC)
    old_event = AlertEvent(
        alert_id=setup_alert.id, alert_title=setup_alert.title,
        cell_id=setup_cell.id, cell_name=setup_cell.name, cell_location="",
        sensor_type="air_temperature", severity=SeverityEnum.CRITICAL,
        value=50.0, threshold_min=-5.0, threshold_max=40.0, is_archived=False,
        timestamp=now - timedelta(days=10),
    )
    recent_event = AlertEvent(
        alert_id=setup_alert.id, alert_title=setup_alert.title,
        cell_id=setup_cell.id, cell_name=setup_cell.name, cell_location="",
        sensor_type="air_temperature", severity=SeverityEnum.CRITICAL,
        value=42.0, threshold_min=-5.0, threshold_max=40.0, is_archived=False,
        timestamp=now - timedelta(hours=1),
    )
    db_session.add_all([old_event, recent_event])
    db_session.commit()

    start = now - timedelta(days=2)
    filtered = (
        db_session.query(AlertEvent)
        .filter(AlertEvent.timestamp >= start)
        .all()
    )

    assert len(filtered) == 1
    assert filtered[0].value == 42.0
