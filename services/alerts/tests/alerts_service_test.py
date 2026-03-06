"""

Tests de la couche service pour le module alertes.
On utilise une base de données en mémoire (via la fixture db_session de conftest.py)
pour tester la logique métier en conditions réelles.
"""

import pytest
import uuid
from datetime import datetime, UTC

from services.alerts import service
from services.alerts.schemas import (
    AlertCreateUpdateSchema,
    AlertToggleSchema,
    AlertValidateInputSchema,
)
from services.alerts.errors import (
    AlertNotFoundError,
    AlertEventNotFoundError,
    AlertConflictError,
)
from db.models import Alert, AlertEvent, Cell, Area, SeverityEnum


# ---------------------------------------------------------------------------
# Fixtures — Mise en place de l'état de la base de données
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_area(db_session):
    area = Area(name="Test Area", color="#FF0000")
    db_session.add(area)
    db_session.commit()
    return area

@pytest.fixture
def setup_cell(db_session, setup_area):
    cell = Cell(name="Test Cell", area_id=setup_area.id)
    db_session.add(cell)
    db_session.commit()
    return cell

@pytest.fixture
def alert_factory(db_session):
    """Factory pour créer des alertes dans la base de données de test."""
    def _make_alert(title="Factory Alert", cell_ids=None, sensor_types=None, is_active=True, warning_enabled=False):
        if sensor_types is None:
            sensor_types = ["air_temperature"]
        
        alert = Alert(
            title=title, is_active=is_active, warning_enabled=warning_enabled,
            cell_ids=cell_ids or [],
            sensors=[
                {"type": s_type, "index": 0, "criticalRange": {"min": -5.0, "max": 40.0}, "warningRange": None}
                for s_type in sensor_types
            ]
        )
        db_session.add(alert)
        db_session.commit()
        return alert
    return _make_alert

def make_alert_create(
    cell_ids: list[uuid.UUID] | None = None,
    sensor_type: str = "air_temperature",
    overwrite: bool = False,
) -> AlertCreateUpdateSchema:
    cids = cell_ids or [uuid.uuid4()]
    return AlertCreateUpdateSchema(
        **{
            "title": "Nouvelle Alerte",
            "isActive": True,
            "cellIds": cids,
            "sensors": [
                {
                    "type": sensor_type,
                    "index": 0,
                    "criticalRange": {"min": -5.0, "max": 40.0},
                    "warningRange": {"min": 0.0, "max": 35.0},
                }
            ],
            "warningEnabled": True,
            "overwriteExisting": overwrite,
        }
    )


# ---------------------------------------------------------------------------
# Tests — get_all_alerts
# ---------------------------------------------------------------------------

class TestGetAllAlerts:

    def test_returns_all_alerts_when_no_filter(self, db_session, alert_factory, setup_cell):
        alert_factory(cell_ids=[str(setup_cell.id)])
        alert_factory()

        result = service.get_all_alerts(db_session, cell_id=None)

        assert len(result) == 2

    def test_filters_by_cell_id(self, db_session, alert_factory, setup_cell):
        alert_match = alert_factory(cell_ids=[str(setup_cell.id)])
        alert_factory() # Une autre alerte non liée

        result = service.get_all_alerts(db_session, cell_id=setup_cell.id)

        assert len(result) == 1
        assert result[0].id == alert_match.id

    def test_returns_empty_list_when_no_alerts(self, db_session):
        # S'assure que la DB est vide pour ce test
        db_session.query(Alert).delete()
        db_session.commit()

        result = service.get_all_alerts(db_session)

        assert result == []


# ---------------------------------------------------------------------------
# Tests — get_alert_by_id
# ---------------------------------------------------------------------------

class TestGetAlertById:

    def test_returns_alert_when_found(self, db_session, alert_factory):
        alert = alert_factory()

        result = service.get_alert_by_id(db_session, alert.id)

        assert result.id == alert.id

    def test_raises_404_when_not_found(self, db_session):

        with pytest.raises(AlertNotFoundError):
            service.get_alert_by_id(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Tests — validate_alert
# ---------------------------------------------------------------------------

class TestValidateAlert:

    def test_no_conflicts_returns_empty(self, db_session):
        payload = AlertValidateInputSchema(
            **{"cellIds": [uuid.uuid4()], "sensorTypes": ["air_temperature"]}
        )
        result = service.validate_alert(db_session, payload)

        assert result["hasConflicts"] is False
        assert result["conflicts"] == []

    def test_detects_conflict_on_same_cell_and_sensor_type(self, db_session, setup_cell, alert_factory):
        alert_factory(cell_ids=[str(setup_cell.id)], sensor_types=["air_temperature"])

        payload = AlertValidateInputSchema(
            **{"cellIds": [setup_cell.id], "sensorTypes": ["air_temperature"]}
        )
        result = service.validate_alert(db_session, payload)

        assert result["hasConflicts"] is True
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["sensorType"] == "air_temperature"

    def test_no_conflict_when_sensor_type_differs(self, db_session, setup_cell, alert_factory):
        alert_factory(cell_ids=[str(setup_cell.id)], sensor_types=["air_temperature"])

        payload = AlertValidateInputSchema(
            **{"cellIds": [setup_cell.id], "sensorTypes": ["soil_humidity"]}
        )
        result = service.validate_alert(db_session, payload)

        assert result["hasConflicts"] is False

    def test_no_conflict_when_cell_differs(self, db_session, setup_cell, alert_factory):
        alert_factory(cell_ids=[str(uuid.uuid4())], sensor_types=["air_temperature"])

        payload = AlertValidateInputSchema(
            **{"cellIds": [setup_cell.id], "sensorTypes": ["air_temperature"]}
        )
        result = service.validate_alert(db_session, payload)

        assert result["hasConflicts"] is False

    def test_no_conflict_when_excluding_alert_id(self, db_session, setup_cell, alert_factory):
        existing = alert_factory(cell_ids=[str(setup_cell.id)], sensor_types=["air_temperature"])
        payload = AlertValidateInputSchema(**{"cellIds": [setup_cell.id], "sensorTypes": ["air_temperature"], "alertId": existing.id})
        result = service.validate_alert(db_session, payload)
        assert result["hasConflicts"] is False

# ---------------------------------------------------------------------------
# Tests — create_alert
# ---------------------------------------------------------------------------

class TestCreateAlert:

    def test_creates_alert_without_conflicts(self, db_session, setup_cell):
        create_payload = make_alert_create(cell_ids=[setup_cell.id])
        result = service.create_alert(db_session, create_payload)

        assert result["message"] == "Alerte créée avec succès."
        created_alert = db_session.query(Alert).filter(Alert.id == result["id"]).first()
        assert created_alert is not None
        assert created_alert.title == "Nouvelle Alerte"

    def test_raises_409_when_conflict_and_no_overwrite(self, db_session, setup_cell, alert_factory):
        alert_factory(cell_ids=[str(setup_cell.id)], sensor_types=["air_temperature"])

        with pytest.raises(AlertConflictError):
            service.create_alert(db_session, make_alert_create(cell_ids=[setup_cell.id], overwrite=False))

    def test_partially_overwrites_conflicting_sensor_when_flag_true(self, db_session, setup_cell, alert_factory):
        """
        Si une nouvelle alerte entre en conflit sur un seul capteur d'une alerte existante
        qui en a plusieurs, seul le capteur en conflit est retiré de l'alerte existante.
        """
        existing_alert = alert_factory(
            cell_ids=[str(setup_cell.id)], sensor_types=["air_temperature", "soil_humidity"]
        )
        create_payload = make_alert_create(
            cell_ids=[setup_cell.id], sensor_type="air_temperature", overwrite=True
        )

        result = service.create_alert(db_session, create_payload)

        db_session.refresh(existing_alert)
        assert len(existing_alert.sensors) == 1
        assert existing_alert.sensors[0]["type"] == "soil_humidity"
        assert result["message"] == "Alerte créée avec succès."
        assert len(result["overwrittenAlerts"]) == 0

    def test_fully_overwrites_alert_when_all_sensors_conflict(self, db_session, setup_cell, alert_factory):
        """
        Si une nouvelle alerte entre en conflit sur tous les capteurs d'une alerte
        existante, l'alerte existante est complètement supprimée.
        """
        existing_alert = alert_factory(cell_ids=[str(setup_cell.id)], sensor_types=["air_temperature"])
        existing_alert_id = existing_alert.id
        create_payload = make_alert_create(
            cell_ids=[setup_cell.id], sensor_type="air_temperature", overwrite=True
        )

        result = service.create_alert(db_session, create_payload)

        deleted_alert = db_session.query(Alert).filter(Alert.id == existing_alert_id).first()
        assert deleted_alert is None
        assert result["message"] == "Alerte créée avec succès."
        assert len(result["overwrittenAlerts"]) == 1
        assert result["overwrittenAlerts"][0] == existing_alert_id


# ---------------------------------------------------------------------------
# Tests — update_alert
# ---------------------------------------------------------------------------

class TestUpdateAlert:

    def test_updates_alert_fields(self, db_session, alert_factory):
        existing = alert_factory()
        update_data = AlertCreateUpdateSchema(
            **{
                "title": "Titre Modifié",
                "isActive": False,
                "cellIds": [str(uuid.uuid4())],
                "sensors": [
                    {
                        "type": "soil_humidity",
                        "index": 0,
                        "criticalRange": {"min": 10.0, "max": 80.0},
                        "warningRange": None,
                    }
                ],
                "warningEnabled": True,
                "overwriteExisting": False,
            }
        )

        result = service.update_alert(db_session, existing.id, update_data)

        db_session.refresh(existing)
        assert existing.title == "Titre Modifié"
        assert existing.is_active is False
        assert existing.warning_enabled is True
        assert result["message"] == "Alerte mise à jour avec succès."

    def test_raises_404_when_not_found(self, db_session):
        """Vérifie qu'une exception est levée si l'alerte à mettre à jour n'existe pas."""
        update_data = AlertCreateUpdateSchema(
            **{
                "title": "X",
                "isActive": True,
                "cellIds": [],
                "sensors": [],
                "warningEnabled": False,
                "overwriteExisting": False,
            }
        )
        with pytest.raises(AlertNotFoundError):
            service.update_alert(db_session, uuid.uuid4(), update_data)

    def test_update_raises_409_when_conflict_and_no_overwrite(self, db_session, setup_cell, alert_factory):
        """
        Vérifie qu'une mise à jour créant un conflit lève une erreur 409
        si `overwriteExisting` est False.
        """
        alert_to_update = alert_factory(title="To Update")
        alert_factory(title="Conflicting", cell_ids=[str(setup_cell.id)], sensor_types=["air_temperature"])
        update_data = make_alert_create(
            cell_ids=[setup_cell.id], sensor_type="air_temperature", overwrite=False
        )

        with pytest.raises(AlertConflictError):
            service.update_alert(db_session, alert_to_update.id, update_data)

    def test_update_partially_overwrites_conflicting_sensor(self, db_session, setup_cell, alert_factory):
        """
        Vérifie qu'une mise à jour résout un conflit partiel en modifiant l'autre alerte.
        """
        alert_to_update = alert_factory(title="To Update")
        conflicting_alert = alert_factory(
            title="Conflicting",
            cell_ids=[str(setup_cell.id)],
            sensor_types=["air_temperature", "soil_humidity"]
        )
        update_data = make_alert_create(cell_ids=[setup_cell.id], sensor_type="air_temperature", overwrite=True)

        result = service.update_alert(db_session, alert_to_update.id, update_data)

        db_session.refresh(conflicting_alert)
        assert len(conflicting_alert.sensors) == 1
        assert conflicting_alert.sensors[0]["type"] == "soil_humidity"
        assert len(result["overwrittenAlerts"]) == 0

    def test_update_fully_overwrites_conflicting_alert(self, db_session, setup_cell, alert_factory):
        """
        Vérifie qu'une mise à jour résout un conflit total en supprimant l'autre alerte.
        """
        alert_to_update = alert_factory(title="To Update")
        conflicting_alert = alert_factory(
            title="Conflicting",
            cell_ids=[str(setup_cell.id)],
            sensor_types=["air_temperature"]
        )
        conflicting_alert_id = conflicting_alert.id
        update_data = make_alert_create(cell_ids=[setup_cell.id], sensor_type="air_temperature", overwrite=True)

        result = service.update_alert(db_session, alert_to_update.id, update_data)

        deleted_alert = db_session.query(Alert).filter(Alert.id == conflicting_alert_id).first()
        assert deleted_alert is None
        assert len(result["overwrittenAlerts"]) == 1
        assert result["overwrittenAlerts"][0] == conflicting_alert.id


# ---------------------------------------------------------------------------
# Tests — toggle_alert
# ---------------------------------------------------------------------------

class TestToggleAlert:

    def test_activates_alert(self, db_session, alert_factory):
        alert = alert_factory(is_active=False)
        result = service.toggle_alert(db_session, alert.id, AlertToggleSchema(**{"isActive": True}))

        db_session.refresh(alert)
        assert alert.is_active is True
        assert result["isActive"] is True

    def test_deactivates_alert(self, db_session, alert_factory):
        alert = alert_factory(is_active=True)
        result = service.toggle_alert(db_session, alert.id, AlertToggleSchema(**{"isActive": False}))

        db_session.refresh(alert)
        assert alert.is_active is False
        assert result["isActive"] is False

    def test_raises_404_when_not_found(self, db_session):
        with pytest.raises(AlertNotFoundError):
            service.toggle_alert(db_session, uuid.uuid4(), AlertToggleSchema(**{"isActive": True}))


# ---------------------------------------------------------------------------
# Tests — delete_alert
# ---------------------------------------------------------------------------

class TestDeleteAlert:

    def test_deletes_existing_alert(self, db_session, alert_factory):
        alert = alert_factory()
        alert_id = alert.id
        service.delete_alert(db_session, alert.id)

        deleted_alert = db_session.query(Alert).filter(Alert.id == alert_id).first()
        assert deleted_alert is None

    def test_raises_404_when_not_found(self, db_session):
        with pytest.raises(AlertNotFoundError):
            service.delete_alert(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Tests — Events
# ---------------------------------------------------------------------------

class TestAlertEvents:

    def _make_event(self, db_session, is_archived: bool = False, severity=SeverityEnum.CRITICAL) -> AlertEvent:
        event = AlertEvent(
            id=uuid.uuid4(), alert_id=uuid.uuid4(), alert_title="Alerte Test",
            cell_id=uuid.uuid4(), cell_name="Rangée A", cell_location="Parcelle Nord",
            sensor_type="air_temperature", severity=severity, value=45.0,
            threshold_min=-5.0, threshold_max=40.0, timestamp=datetime.now(UTC),
            is_archived=is_archived
        )
        db_session.add(event)
        db_session.commit()
        return event

    def test_get_events_returns_non_archived(self, db_session):
        # Sans filtres optionnels le service fait exactement :
        # db.query(AlertEvent).filter(...).order_by(...).all()
        # → 1 seul .filter(), pas 4
        self._make_event(db_session, is_archived=False)
        self._make_event(db_session, is_archived=False)
        self._make_event(db_session, is_archived=True)

        result = service.get_alert_events(db_session)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_archive_event_sets_flag(self, db_session):
        event = self._make_event(db_session, is_archived=False)
        result = service.archive_event(db_session, event.id)

        db_session.refresh(event)
        assert event.is_archived is True
        assert "archivé" in result["message"]

    def test_archive_event_raises_404_when_not_found(self, db_session):
        with pytest.raises(AlertEventNotFoundError):
            service.archive_event(db_session, uuid.uuid4())

    def test_archive_all_events(self, db_session):
        events = [self._make_event(db_session, is_archived=False) for _ in range(3)]
        result = service.archive_all_events(db_session)

        assert result["archivedCount"] == 3
        for event in events:
            db_session.refresh(event)
            assert event.is_archived is True

    def test_archive_all_returns_zero_when_no_events(self, db_session):
        result = service.archive_all_events(db_session)
        assert result["archivedCount"] == 0

    def test_archive_by_cell(self, db_session):
        event = self._make_event(db_session, is_archived=False)
        cell_id = event.cell_id
        result = service.archive_events_by_cell(db_session, cell_id)

        db_session.refresh(event)
        assert event.is_archived is True
        assert result["archivedCount"] == 1
        assert result["cellId"] == cell_id
