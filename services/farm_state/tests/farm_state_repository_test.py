import pytest
from services.farm_state.repository import get_counts
from db.models import User, Area, Cell, Role


def test_get_counts_populated_db(db_session):
    """Vérifie que get_counts retourne les bons comptes pour une base de données remplie."""
    # Arrange
    role = Role(name="test_role")
    db_session.add(role)
    db_session.commit()

    users = [
        User(email="user1@test.com", password="pwd", role_id=role.id, first_name="f", last_name="l"),
        User(email="user2@test.com", password="pwd", role_id=role.id, first_name="f", last_name="l"),
    ]
    areas = [Area(name="Area 1"), Area(name="Area 2"), Area(name="Area 3")]
    cells = [Cell(name="Cell 1"), Cell(name="Cell 2")]
    db_session.add_all(users + areas + cells)
    db_session.commit()

    # Act
    total_users, total_areas, total_cells = get_counts(db_session)

    # Assert
    assert total_users == 2
    assert total_areas == 3
    assert total_cells == 2


def test_get_counts_empty_db(db_session):
    """Vérifie que get_counts retourne des zéros pour une base de données vide."""
    # Act
    total_users, total_areas, total_cells = get_counts(db_session)

    # Assert
    assert total_users == 0
    assert total_areas == 0
    assert total_cells == 0