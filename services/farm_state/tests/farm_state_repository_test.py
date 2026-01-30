import pytest
from services.farm_state.repository import (
    get_summary_counts,
    get_farm,
    get_all_sensor_types,
    get_average_analytics_by_type,
)
from db.models import User, Area, Cell, Sensor, RoleEnum, Farm, Analytic, AnalyticType


# === Tests for get_summary_counts ===
def test_get_summary_counts_populated_db(db_session):
    """Vérifie que get_summary_counts retourne les bons comptes pour une base de données remplie."""
    # Arrange
    users = [
        User(email="user1@test.com", password="pwd", role=RoleEnum.EMPLOYEES, first_name="f", last_name="l"),
        User(email="user2@test.com", password="pwd", role=RoleEnum.EMPLOYEES, first_name="f", last_name="l"),
    ]
    areas = [Area(name="Area 1"), Area(name="Area 2"), Area(name="Area 3")]
    cells = [Cell(name="Cell 1"), Cell(name="Cell 2")]
    db_session.add_all(users + areas + cells)
    db_session.commit()

    # Un capteur a besoin d'une cellule avec un ID
    sensors = [Sensor(sensor_id="S1", sensor_type="temp", cell_id=cells[0].id)]
    db_session.add_all(sensors)
    db_session.commit()

    # Act
    counts = get_summary_counts(db_session)

    # Assert
    assert counts["total_users"] == 2
    assert counts["total_areas"] == 3
    assert counts["total_cells"] == 2
    assert counts["total_sensors"] == 1


def test_get_summary_counts_empty_db(db_session):
    """Vérifie que get_summary_counts retourne des zéros pour une base de données vide."""
    # Act
    counts = get_summary_counts(db_session)

    # Assert
    assert counts["total_users"] == 0
    assert counts["total_areas"] == 0
    assert counts["total_cells"] == 0
    assert counts["total_sensors"] == 0


# === Tests for get_farm ===

def test_get_farm_exists(db_session):
    """Vérifie que get_farm retourne la ferme si elle existe."""
    # Arrange
    farm = Farm(name="Ma Belle Ferme")
    db_session.add(farm)
    db_session.commit()

    # Act
    result = get_farm(db_session)

    # Assert
    assert result is not None
    assert result.name == "Ma Belle Ferme"

def test_get_farm_not_exists(db_session):
    """Vérifie que get_farm retourne None si aucune ferme n'existe."""
    # Act
    result = get_farm(db_session)

    # Assert
    assert result is None


# === Tests for get_all_sensor_types ===

def test_get_all_sensor_types_populated(db_session):
    """Vérifie que get_all_sensor_types retourne une liste de types de capteurs."""
    # Arrange
    cell = Cell(name="C1")
    db_session.add(cell)
    db_session.commit()
    sensors = [
        Sensor(sensor_id="T1", sensor_type="temperature", cell_id=cell.id),
        Sensor(sensor_id="T2", sensor_type="temperature", cell_id=cell.id),
        Sensor(sensor_id="H1", sensor_type="humidity", cell_id=cell.id),
    ]
    db_session.add_all(sensors)
    db_session.commit()

    # Act
    result = get_all_sensor_types(db_session)
    types = [r[0] for r in result]

    # Assert
    assert len(types) == 3
    assert "temperature" in types
    assert "humidity" in types
    assert types.count("temperature") == 2

def test_get_all_sensor_types_empty(db_session):
    """Vérifie que get_all_sensor_types retourne une liste vide si aucun capteur n'existe."""
    # Act
    result = get_all_sensor_types(db_session)

    # Assert
    assert result == []


# === Tests for get_average_analytics_by_type ===

def test_get_average_analytics_by_type_populated(db_session):
    """Vérifie que get_average_analytics_by_type calcule correctement les moyennes."""
    # Arrange
    cell = Cell(name="C1")
    db_session.add(cell)
    db_session.commit()
    sensor = Sensor(sensor_id="S1", sensor_type="multi", cell_id=cell.id)
    db_session.add(sensor)
    db_session.commit()

    analytics = [
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_TEMPERATURE, value=20),
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_TEMPERATURE, value=30), # Avg = 25
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_HUMIDITY, value=60),
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_HUMIDITY, value=70), # Avg = 65
    ]
    db_session.add_all(analytics)
    db_session.commit()

    # Act
    result = get_average_analytics_by_type(db_session)
    avg_dict = dict(result)

    # Assert
    assert len(avg_dict) == 2
    assert avg_dict[AnalyticType.AIR_TEMPERATURE] == 25.0
    assert avg_dict[AnalyticType.AIR_HUMIDITY] == 65.0

def test_get_average_analytics_by_type_empty(db_session):
    """Vérifie que get_average_analytics_by_type retourne une liste vide si aucune analytique n'existe."""
    # Act
    result = get_average_analytics_by_type(db_session)

    # Assert
    assert result == []