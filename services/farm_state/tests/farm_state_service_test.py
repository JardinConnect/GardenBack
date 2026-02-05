import pytest
from services.farm_state.service import get_farm_details
from db.models import User, Area, Cell, Sensor, RoleEnum, Farm, Analytic, AnalyticType


def test_get_farm_details_empty_db(db_session):
    """
    Vérifie que get_farm_details retourne une structure vide mais correcte
    pour une base de données vide, sans les analytiques.
    """
    # Act
    details = get_farm_details(db_session, with_analytics=False)

    # Assert
    assert details.name == "JardinConnect"  # Fallback name
    assert details.summary.total_users == 0
    assert details.summary.total_areas == 0
    assert details.summary.total_cells == 0
    assert details.summary.total_sensors == 0
    assert details.summary.sensor_types == {}
    assert details.average_analytics is None


def test_get_farm_details_with_data_no_analytics(db_session):
    """
    Vérifie que get_farm_details retourne les bonnes informations
    quand la base est remplie, mais sans demander les analytiques.
    """
    # Arrange
    db_session.add(Farm(name="Ma Super Ferme"))
    db_session.add(User(email="user@test.com", password="pwd", role=RoleEnum.EMPLOYEES, first_name="f", last_name="l"))
    area = Area(name="A1")
    db_session.add(area)
    db_session.commit()
    cell = Cell(name="C1", area_id=area.id)
    db_session.add(cell)
    db_session.commit()
    db_session.add(Sensor(sensor_id="T1", sensor_type="temperature", cell_id=cell.id))
    db_session.add(Sensor(sensor_id="T2", sensor_type="temperature", cell_id=cell.id))
    db_session.add(Sensor(sensor_id="H1", sensor_type="humidity", cell_id=cell.id))
    db_session.commit()

    # Act
    details = get_farm_details(db_session, with_analytics=False)

    # Assert
    assert details.name == "Ma Super Ferme"
    assert details.summary.total_users == 1
    assert details.summary.total_areas == 1
    assert details.summary.total_cells == 1
    assert details.summary.total_sensors == 3
    assert details.summary.sensor_types == {"temperature": 2, "humidity": 1}
    assert details.average_analytics is None


def test_get_farm_details_with_analytics(db_session):
    """
    Vérifie que get_farm_details retourne les bonnes informations
    y compris les moyennes des analytiques quand demandé.
    """
    # Arrange
    db_session.add(Farm(name="Ferme Analytique"))
    cell = Cell(name="C1")
    db_session.add(cell)
    db_session.commit()
    sensor = Sensor(sensor_id="S1", sensor_type="multi", cell_id=cell.id)
    db_session.add(sensor)
    db_session.commit()
    analytics = [
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_TEMPERATURE, value=20.5),
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_TEMPERATURE, value=30.5), # Avg = 25.5
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_HUMIDITY, value=60),
    ]
    db_session.add_all(analytics)
    db_session.commit()

    # Act
    details = get_farm_details(db_session, with_analytics=True)

    # Assert
    assert details.name == "Ferme Analytique"
    assert details.summary.total_sensors == 1
    assert details.summary.sensor_types == {"multi": 1}
    
    assert details.average_analytics is not None
    assert len(details.average_analytics) == 2
    assert details.average_analytics["AIR_TEMPERATURE"] == 25.5
    assert details.average_analytics["AIR_HUMIDITY"] == 60.0


def test_get_farm_details_with_analytics_rounding(db_session):
    """Vérifie que les moyennes des analytiques sont correctement arrondies."""
    # Arrange
    cell = Cell(name="C1")
    db_session.add(cell)
    db_session.commit()
    sensor = Sensor(sensor_id="S1", sensor_type="multi", cell_id=cell.id)
    db_session.add(sensor)
    db_session.commit()
    analytics = [
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.LIGHT, value=10),
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.LIGHT, value=15),
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.LIGHT, value=12), # Avg = 12.333...
    ]
    db_session.add_all(analytics)
    db_session.commit()

    # Act
    details = get_farm_details(db_session, with_analytics=True)

    # Assert
    assert details.average_analytics is not None
    assert details.average_analytics["LIGHT"] == 12.33