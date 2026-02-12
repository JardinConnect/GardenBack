import pytest
from fastapi import HTTPException
import uuid
from datetime import datetime, timedelta, UTC
from db.models import Area, Cell, Sensor, Analytic, AnalyticType
from services.area.repository import (
    create,
    delete_hierarchy,
    get_all_areas_with_relations,
    get_analytics_for_areas,
    get_area_level,
    get_areas_by_ids_with_relations,
    get_by_id,
    get_descendant_area_ids,
    update,
)


@pytest.fixture(scope="function")
def setup_hierarchy(db_session):
    """Crée une hiérarchie de test : Parcelle -> Planche -> Cellule -> Capteur -> Donnée."""
    parcelle = Area(name="Parcelle Test", color="#111111")
    db_session.add(parcelle)
    db_session.commit()  # Commit pour obtenir l'ID de la parcelle

    planche = Area(name="Planche Test", color="#222222", parent_id=parcelle.id)
    db_session.add(planche)
    db_session.commit()  # Commit pour obtenir l'ID de la planche

    cellule = Cell(name="Cellule Test", area_id=planche.id)
    db_session.add(cellule)
    db_session.commit()  # Commit pour obtenir l'ID de la cellule

    capteur = Sensor(sensor_id="TEST-01", sensor_type="temperature", cell_id=cellule.id)
    db_session.add(capteur)
    db_session.commit()  # Commit pour obtenir l'ID du capteur

    analytic = Analytic(
        sensor_id=capteur.id,
        sensor_code="TEST-01",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=25.5,
        occurred_at=datetime.now(UTC),
    )
    db_session.add(analytic)
    db_session.commit()

    return {"parcelle_id": parcelle.id, "planche_id": planche.id, "area_obj": planche}


@pytest.fixture(scope="function")
def setup_areas(db_session):
    """Crée une hiérarchie simple d'areas pour les tests."""
    root1 = Area(name="Root 1")
    root2 = Area(name="Root 2")
    db_session.add_all([root1, root2])
    db_session.commit()

    child1 = Area(name="Child 1.1", parent_id=root1.id)
    db_session.add(child1)
    db_session.commit()

    grandchild1 = Area(name="Grandchild 1.1.1", parent_id=child1.id)
    db_session.add(grandchild1)
    db_session.commit()

    return {"root1": root1, "root2": root2, "child1": child1, "grandchild1": grandchild1}


def test_get_by_id_not_found(db_session):
    """Teste que get_by_id retourne None si l'ID n'existe pas."""
    result = get_by_id(db_session, uuid.uuid4())
    assert result is None

def test_get_by_id_success(db_session, setup_hierarchy):
    """Teste la récupération réussie d'une zone par son ID."""
    parcelle_id = setup_hierarchy["parcelle_id"]
    result = get_by_id(db_session, parcelle_id)
    assert result is not None
    assert result.id == parcelle_id
    assert result.name == "Parcelle Test"

def test_get_analytics_for_areas_success(db_session):
    """Vérifie que la fonction récupère bien les analytiques des 7 derniers jours."""
    area = Area(name="Test Area")
    cell = Cell(name="Test Cell", area=area)
    sensor = Sensor(sensor_id="S1", sensor_type="temp", cell=cell)
    db_session.add_all([area, cell, sensor])
    db_session.commit()

    now = datetime.now(UTC)
    analytic_recent = Analytic(sensor_id=sensor.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=25, occurred_at=now - timedelta(days=1), sensor_code="S1")
    analytic_old = Analytic(sensor_id=sensor.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=10, occurred_at=now - timedelta(days=8), sensor_code="S1")
    db_session.add_all([analytic_recent, analytic_old])
    db_session.commit()

    result = get_analytics_for_areas(db_session, [area.id])

    assert area.id in result
    assert len(result[area.id]) == 1
    assert result[area.id][0].id == analytic_recent.id
    assert result[area.id][0].value == 25

def test_get_analytics_for_areas_no_sensors(db_session):
    """Vérifie que la fonction retourne un dict vide pour une zone sans capteurs."""
    area = Area(name="Empty Area")
    db_session.add(area)
    db_session.commit()

    result = get_analytics_for_areas(db_session, [area.id])

    assert area.id not in result
    assert result == {}

def test_get_analytics_for_areas_no_areas(db_session):
    """Vérifie que la fonction retourne un dict vide si la liste d'IDs est vide."""
    result = get_analytics_for_areas(db_session, [])
    assert result == {}


def test_get_all_areas_with_relations(db_session, setup_areas):
    """Teste que la fonction retourne toutes les zones avec leurs relations."""
    all_areas = get_all_areas_with_relations(db_session)
    assert len(all_areas) == 4

    root1_from_db = next(a for a in all_areas if a.id == setup_areas["root1"].id)
    assert len(root1_from_db.children) == 1
    assert root1_from_db.children[0].name == "Child 1.1"


def test_get_areas_by_ids_with_relations(db_session, setup_areas):
    """Teste que la fonction retourne uniquement les zones demandées."""
    root1_id = setup_areas["root1"].id
    child1_id = setup_areas["child1"].id

    areas = get_areas_by_ids_with_relations(db_session, [root1_id, child1_id])

    assert len(areas) == 2
    area_names = {a.name for a in areas}
    assert "Root 1" in area_names
    assert "Child 1.1" in area_names


def test_get_area_level(db_session, setup_areas):
    """Teste le calcul du niveau hiérarchique d'une zone."""
    root1_id = setup_areas["root1"].id
    child1_id = setup_areas["child1"].id
    grandchild1_id = setup_areas["grandchild1"].id

    assert get_area_level(db_session, root1_id) == 1
    assert get_area_level(db_session, child1_id) == 2
    assert get_area_level(db_session, grandchild1_id) == 3


def test_get_descendant_area_ids(db_session, setup_areas):
    """Teste la récupération des IDs de tous les descendants d'une zone."""
    root1_id = setup_areas["root1"].id
    child1_id = setup_areas["child1"].id
    grandchild1_id = setup_areas["grandchild1"].id

    descendants = get_descendant_area_ids(db_session, root1_id)

    assert len(descendants) == 3
    assert root1_id in descendants
    assert child1_id in descendants
    assert grandchild1_id in descendants


def test_create_repository(db_session):
    """Teste la création d'une zone via le repository."""
    new_area = Area(name="New Area From Repo")
    created_area = create(db_session, new_area)

    assert created_area.id is not None
    assert created_area.name == "New Area From Repo"

    from_db = db_session.query(Area).filter(Area.id == created_area.id).first()
    assert from_db is not None
    assert from_db.name == "New Area From Repo"


def test_update_repository(db_session):
    """Teste la mise à jour d'une zone via le repository."""
    area_to_update = Area(name="Original Name")
    db_session.add(area_to_update)
    db_session.commit()

    area_to_update.name = "Updated Name"
    area_to_update.color = "#123456"

    updated_area = update(db_session, area_to_update)

    assert updated_area.name == "Updated Name"
    assert updated_area.color == "#123456"

    db_session.refresh(area_to_update)
    assert area_to_update.name == "Updated Name"


def test_delete_hierarchy_repository(db_session):
    """Teste la suppression d'une hiérarchie via le repository."""
    root = Area(name="Root to delete")
    db_session.add(root)
    db_session.commit()
    child = Area(name="Child to delete", parent_id=root.id)
    db_session.add(child)
    db_session.commit()
    cell_on_child = Cell(name="Cell to detach", area_id=child.id)
    db_session.add(cell_on_child)
    db_session.commit()

    root_id = root.id
    child_id = child.id
    cell_id = cell_on_child.id

    delete_hierarchy(db_session, root)

    assert db_session.query(Area).filter(Area.id == root_id).first() is None
    assert db_session.query(Area).filter(Area.id == child_id).first() is None

    detached_cell = db_session.query(Cell).filter(Cell.id == cell_id).first()
    assert detached_cell is not None
    assert detached_cell.area_id is None
