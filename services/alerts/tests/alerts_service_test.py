"""

Tests de la couche service pour le module alertes.
On mocke la Session SQLAlchemy pour tester la logique métier
sans dépendance à une vraie base de données.
"""

import pytest
import uuid
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch, call

from services.alerts import service
from services.alerts.schemas import (
    AlertCreateSchema,
    AlertUpdateSchema,
    AlertToggleSchema,
    AlertValidateInputSchema,
    AlertSensorSchema,
    RangeSchema,
    RangeOptionalSchema,
)
from services.alerts.errors import (
    AlertNotFoundError,
    AlertEventNotFoundError,
    AlertConflictError,
)
from db.models import Alert, AlertEvent, Cell, Area, SeverityEnum


# ---------------------------------------------------------------------------
# Builders — objets Alert/Cell factices
# ---------------------------------------------------------------------------

def make_cell(name: str = "Rangée A", area_name: str = "Parcelle Nord") -> MagicMock:
    cell = MagicMock(spec=Cell)
    cell.id = uuid.uuid4()
    cell.name = name
    area = MagicMock(spec=Area)
    area.name = area_name
    cell.area = area
    return cell


def make_alert(cell_id: uuid.UUID | None = None, sensor_type: str = "air_temperature") -> MagicMock:
    alert = MagicMock(spec=Alert)
    alert.id = uuid.uuid4()
    alert.title = "Alerte Test"
    alert.is_active = True
    alert.warning_enabled = False
    alert.cell_ids = [str(cell_id)] if cell_id else [str(uuid.uuid4())]
    alert.sensors = [
        {
            "type": sensor_type,
            "index": 0,
            "criticalRange": {"min": -5.0, "max": 40.0},
            "warningRange": None,
        }
    ]
    alert.created_at = datetime.now(UTC)
    alert.updated_at = datetime.now(UTC)
    return alert


def make_alert_create(
    cell_ids: list[uuid.UUID] | None = None,
    sensor_type: str = "air_temperature",
    overwrite: bool = False,
) -> AlertCreateSchema:
    cids = cell_ids or [uuid.uuid4()]
    return AlertCreateSchema(
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

    def test_returns_all_alerts_when_no_filter(self):
        db = MagicMock()
        cell_id = uuid.uuid4()
        alert1 = make_alert(cell_id)
        alert2 = make_alert(uuid.uuid4())
        db.query().all.return_value = [alert1, alert2]

        with patch.object(service, "_build_alert_response", side_effect=lambda a, d: a):
            result = service.get_all_alerts(db, cell_id=None)

        assert len(result) == 2

    def test_filters_by_cell_id(self):
        db = MagicMock()
        cell_id = uuid.uuid4()
        alert_match = make_alert(cell_id)
        alert_other = make_alert(uuid.uuid4())
        db.query().all.return_value = [alert_match, alert_other]

        with patch.object(service, "_build_alert_response", side_effect=lambda a, d: a):
            result = service.get_all_alerts(db, cell_id=cell_id)

        assert len(result) == 1
        assert result[0] is alert_match

    def test_returns_empty_list_when_no_alerts(self):
        db = MagicMock()
        db.query().all.return_value = []

        result = service.get_all_alerts(db)

        assert result == []


# ---------------------------------------------------------------------------
# Tests — get_alert_by_id
# ---------------------------------------------------------------------------

class TestGetAlertById:

    def test_returns_alert_when_found(self):
        db = MagicMock()
        alert = make_alert()
        db.query().filter().first.return_value = alert

        with patch.object(service, "_build_alert_response", return_value=alert):
            result = service.get_alert_by_id(db, alert.id)

        assert result is alert

    def test_raises_404_when_not_found(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        with pytest.raises(AlertNotFoundError):
            service.get_alert_by_id(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# Tests — validate_alert
# ---------------------------------------------------------------------------

class TestValidateAlert:

    def test_no_conflicts_returns_empty(self):
        db = MagicMock()
        db.query().all.return_value = []  # aucune alerte existante

        payload = AlertValidateInputSchema(
            **{"cellIds": [str(uuid.uuid4())], "sensorTypes": ["air_temperature"]}
        )
        result = service.validate_alert(db, payload)

        assert result["hasConflicts"] is False
        assert result["conflicts"] == []

    def test_detects_conflict_on_same_cell_and_sensor_type(self):
        db = MagicMock()
        cell_id = uuid.uuid4()
        existing = make_alert(cell_id, sensor_type="air_temperature")

        # db.query(Alert).all() → liste d'alertes
        # db.query(Cell).filter().first() → cellule
        cell_mock = make_cell()
        cell_mock.id = cell_id

        db.query.side_effect = lambda model: _mock_query_for(model, existing, cell_mock)

        payload = AlertValidateInputSchema(
            **{"cellIds": [str(cell_id)], "sensorTypes": ["air_temperature"]}
        )
        result = service.validate_alert(db, payload)

        assert result["hasConflicts"] is True
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["sensorType"] == "air_temperature"

    def test_no_conflict_when_sensor_type_differs(self):
        db = MagicMock()
        cell_id = uuid.uuid4()
        existing = make_alert(cell_id, sensor_type="air_temperature")
        cell_mock = make_cell()
        cell_mock.id = cell_id

        db.query.side_effect = lambda model: _mock_query_for(model, existing, cell_mock)

        payload = AlertValidateInputSchema(
            **{"cellIds": [str(cell_id)], "sensorTypes": ["soil_humidity"]}
        )
        result = service.validate_alert(db, payload)

        assert result["hasConflicts"] is False

    def test_no_conflict_when_cell_differs(self):
        db = MagicMock()
        existing = make_alert(uuid.uuid4(), sensor_type="air_temperature")
        db.query().all.return_value = [existing]

        payload = AlertValidateInputSchema(
            **{"cellIds": [str(uuid.uuid4())], "sensorTypes": ["air_temperature"]}
        )
        result = service.validate_alert(db, payload)

        assert result["hasConflicts"] is False


# ---------------------------------------------------------------------------
# Tests — create_alert
# ---------------------------------------------------------------------------

class TestCreateAlert:

    def test_creates_alert_without_conflicts(self):
        db = MagicMock()
        db.query().all.return_value = []  # pas de conflits

        new_alert = make_alert()
        db.refresh.side_effect = lambda obj: None

        with patch("services.alerts.service.Alert") as MockAlert:
            MockAlert.return_value = new_alert
            result = service.create_alert(db, make_alert_create())

        db.add.assert_called_once()
        db.commit.assert_called()
        assert result["message"] == "Alerte créée avec succès."

    def test_raises_409_when_conflict_and_no_overwrite(self):
        db = MagicMock()
        cell_id = uuid.uuid4()
        existing = make_alert(cell_id, sensor_type="air_temperature")
        cell_mock = make_cell()
        cell_mock.id = cell_id
        db.query.side_effect = lambda model: _mock_query_for(model, existing, cell_mock)

        with pytest.raises(AlertConflictError):
            service.create_alert(db, make_alert_create(cell_ids=[cell_id], overwrite=False))

    def test_overwrites_existing_alert_when_flag_true(self):
        db = MagicMock()
        cell_id = uuid.uuid4()
        existing = make_alert(cell_id, sensor_type="air_temperature")
        cell_mock = make_cell()
        cell_mock.id = cell_id

        db.query.side_effect = lambda model: _mock_query_for(model, existing, cell_mock)
        # db.refresh ne doit rien faire (l'objet Alert est instancié sans session réelle)
        db.refresh.side_effect = lambda obj: None

        # On NE patche PAS services.alerts.service.Alert :
        # patcher la classe remplace le modèle passé à db.query(), ce qui casse
        # le type-check `model is Alert` dans _mock_query_for et empêche
        # la branche delete d'être atteinte.
        result = service.create_alert(db, make_alert_create(cell_ids=[cell_id], overwrite=True))

        # L'alerte existante doit avoir été supprimée
        db.delete.assert_called()
        assert result["message"] == "Alerte créée avec succès."
        assert len(result["overwrittenAlerts"]) >= 1


# ---------------------------------------------------------------------------
# Tests — update_alert
# ---------------------------------------------------------------------------

class TestUpdateAlert:

    def test_updates_alert_fields(self):
        db = MagicMock()
        existing = make_alert()
        db.query().filter().first.return_value = existing
        db.refresh.side_effect = lambda obj: None

        update_data = AlertUpdateSchema(
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
            }
        )

        result = service.update_alert(db, existing.id, update_data)

        assert existing.title == "Titre Modifié"
        assert existing.is_active is False
        assert existing.warning_enabled is True
        db.commit.assert_called()
        assert result["message"] == "Alerte mise à jour avec succès."

    def test_raises_404_when_not_found(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        update_data = AlertUpdateSchema(
            **{
                "title": "X",
                "isActive": True,
                "cellIds": [],
                "sensors": [],
                "warningEnabled": False,
            }
        )
        with pytest.raises(AlertNotFoundError):
            service.update_alert(db, uuid.uuid4(), update_data)


# ---------------------------------------------------------------------------
# Tests — toggle_alert
# ---------------------------------------------------------------------------

class TestToggleAlert:

    def test_activates_alert(self):
        db = MagicMock()
        alert = make_alert()
        alert.is_active = False
        db.query().filter().first.return_value = alert
        db.refresh.side_effect = lambda obj: None

        result = service.toggle_alert(db, alert.id, AlertToggleSchema(**{"isActive": True}))

        assert alert.is_active is True
        assert result["isActive"] is True

    def test_deactivates_alert(self):
        db = MagicMock()
        alert = make_alert()
        alert.is_active = True
        db.query().filter().first.return_value = alert
        db.refresh.side_effect = lambda obj: None

        result = service.toggle_alert(db, alert.id, AlertToggleSchema(**{"isActive": False}))

        assert alert.is_active is False
        assert result["isActive"] is False

    def test_raises_404_when_not_found(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        with pytest.raises(AlertNotFoundError):
            service.toggle_alert(db, uuid.uuid4(), AlertToggleSchema(**{"isActive": True}))


# ---------------------------------------------------------------------------
# Tests — delete_alert
# ---------------------------------------------------------------------------

class TestDeleteAlert:

    def test_deletes_existing_alert(self):
        db = MagicMock()
        alert = make_alert()
        db.query().filter().first.return_value = alert

        service.delete_alert(db, alert.id)

        db.delete.assert_called_once_with(alert)
        db.commit.assert_called()

    def test_raises_404_when_not_found(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        with pytest.raises(AlertNotFoundError):
            service.delete_alert(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# Tests — Events
# ---------------------------------------------------------------------------

class TestAlertEvents:

    def _make_event(self, is_archived: bool = False, severity=SeverityEnum.CRITICAL) -> MagicMock:
        event = MagicMock(spec=AlertEvent)
        event.id = uuid.uuid4()
        event.alert_id = uuid.uuid4()
        event.alert_title = "Alerte Test"
        event.cell_id = uuid.uuid4()
        event.cell_name = "Rangée A"
        event.cell_location = "Parcelle Nord"
        event.sensor_type = "air_temperature"
        event.severity = severity
        event.value = 45.0
        event.threshold_min = -5.0
        event.threshold_max = 40.0
        event.timestamp = datetime.now(UTC)
        event.is_archived = is_archived
        return event

    def test_get_events_returns_non_archived(self):
        db = MagicMock()
        events = [self._make_event(False), self._make_event(False)]
        # Sans filtres optionnels le service fait exactement :
        # db.query(AlertEvent).filter(...).order_by(...).all()
        # → 1 seul .filter(), pas 4
        db.query().filter().order_by().all.return_value = events

        result = service.get_alert_events(db)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_archive_event_sets_flag(self):
        db = MagicMock()
        event = self._make_event(is_archived=False)
        db.query().filter().first.return_value = event

        result = service.archive_event(db, event.id)

        assert event.is_archived is True
        db.commit.assert_called()
        assert "archivé" in result["message"]

    def test_archive_event_raises_404_when_not_found(self):
        db = MagicMock()
        db.query().filter().first.return_value = None

        with pytest.raises(AlertEventNotFoundError):
            service.archive_event(db, uuid.uuid4())

    def test_archive_all_events(self):
        db = MagicMock()
        events = [self._make_event(False) for _ in range(3)]
        db.query().filter().all.return_value = events

        result = service.archive_all_events(db)

        for e in events:
            assert e.is_archived is True
        assert result["archivedCount"] == 3
        db.commit.assert_called()

    def test_archive_all_returns_zero_when_no_events(self):
        db = MagicMock()
        db.query().filter().all.return_value = []

        result = service.archive_all_events(db)

        assert result["archivedCount"] == 0

    def test_archive_by_cell(self):
        db = MagicMock()
        cell_id = uuid.uuid4()
        events = [self._make_event(False) for _ in range(2)]
        db.query().filter().all.return_value = events

        result = service.archive_events_by_cell(db, cell_id)

        for e in events:
            assert e.is_archived is True
        assert result["archivedCount"] == 2
        assert result["cellId"] == cell_id


# ---------------------------------------------------------------------------
# Helpers internes pour les mocks
# ---------------------------------------------------------------------------

def _mock_query_for(model, existing_alert: MagicMock, cell_mock: MagicMock):
    """
    Retourne un mock de query adapté selon le modèle interrogé.
    - Alert  → renvoie la liste [existing_alert] pour .all()
    - Cell   → renvoie cell_mock pour .filter().first()
    """
    q = MagicMock()
    if model is Alert:
        q.all.return_value = [existing_alert]
        q.filter.return_value.first.return_value = existing_alert
    elif model is Cell:
        q.filter.return_value.first.return_value = cell_mock
    else:
        q.all.return_value = []
        q.filter.return_value.first.return_value = None
    return q
