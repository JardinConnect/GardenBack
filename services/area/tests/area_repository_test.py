import pytest
from fastapi import HTTPException
import uuid
from datetime import datetime, timedelta, UTC
from db.models import Area, Cell, Sensor, Analytic, AnalyticType
from services.area.repository import get_by_id, get_analytics_for_areas


@pytest.fixture(scope="function")
def setup_hierarchy(db_session):
    """Crée une hiérarchie de test : Parcelle -> Planche -> Cellule -> Capteur -> Donnée."""
    parcelle = Area(name="Parcelle Test", color="#111111")
    db_session.add(parcelle)
    db_session.commit()
    planche = Area(name="Planche Test", color="#222222", parent_id=parcelle.id)
    db_session.add(planche)
    db_session.commit()
    cellule = Cell(name="Cellule Test", area_id=planche.id)
    db_session.add(cellule)
    db_session.commit()
    capteur = Sensor(sensor_id="TEST-01", sensor_type="temperature", cell_id=cellule.id)
    db_session.add(capteur)
    db_session.commit()
    analytic = Analytic(
        sensor_id=capteur.id,
        sensor_code="TEST-01",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=25.5,
        occured_at=datetime.now()
    )
    db_session.add(analytic)
    db_session.commit()

    return {"parcelle_id": parcelle.id, "planche_id": planche.id, "area_obj": planche}


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
    analytic_recent = Analytic(sensor_id=sensor.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=25, occured_at=now - timedelta(days=1), sensor_code="S1")
    analytic_old = Analytic(sensor_id=sensor.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=10, occured_at=now - timedelta(days=8), sensor_code="S1")
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