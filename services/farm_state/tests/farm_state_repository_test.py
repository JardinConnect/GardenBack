import pytest
from services.farm_state.repository import get_summary_counts
from db.models import User, Area, Cell, Sensor, RoleEnum


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