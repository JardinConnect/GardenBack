import pytest

from db.models import Alert, Cell, Area, SeverityEnum
from services.alerts import service


@pytest.fixture
def setup_area(db_session):
    area = Area(name="Area SSE", color="#00FF00")
    db_session.add(area)
    db_session.commit()
    return area


@pytest.fixture
def setup_cell(db_session, setup_area):
    cell = Cell(name="Cell SSE", area_id=setup_area.id, deviceID="SSE-TEST-DEVICE-1")
    db_session.add(cell)
    db_session.commit()
    return cell


@pytest.fixture
def setup_alert(db_session, setup_cell):
    alert = Alert(
        title="Alerte SSE",
        is_active=True,
        warning_enabled=False,
        cell_ids=[str(setup_cell.id)],
        sensors=[
            {
                "type": "air_temperature",
                "index": 0,
                "criticalRange": {"min": -5.0, "max": 40.0},
                "warningRange": None,
            }
        ],
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


class TestCreateAlertEventNotify:
    def test_notifies_after_commit(self, db_session, setup_cell, setup_alert, mocker):
        mock_notify = mocker.patch("services.alerts.service.notify_alert_event_if_configured")
        ev = service.create_alert_event(
            db_session,
            alert_id=setup_alert.id,
            alert_title=setup_alert.title,
            cell_id=setup_cell.id,
            cell_name=setup_cell.name,
            cell_location="/test/path",
            sensor_type="air_temperature",
            severity=SeverityEnum.CRITICAL,
            value=99.5,
            threshold_min=0.0,
            threshold_max=100.0,
        )
        mock_notify.assert_called_once()
        assert mock_notify.call_args[0][0].id == ev.id

    def test_persists_row(self, db_session, setup_cell, setup_alert, mocker):
        mocker.patch("services.alerts.service.notify_alert_event_if_configured")
        ev = service.create_alert_event(
            db_session,
            alert_id=setup_alert.id,
            alert_title=setup_alert.title,
            cell_id=setup_cell.id,
            cell_name=setup_cell.name,
            cell_location="/test/path",
            sensor_type="air_temperature",
            severity=SeverityEnum.WARNING,
            value=12.0,
            threshold_min=0.0,
            threshold_max=50.0,
        )
        assert ev.id is not None
        assert ev.alert_id == setup_alert.id
        assert ev.severity == SeverityEnum.WARNING
