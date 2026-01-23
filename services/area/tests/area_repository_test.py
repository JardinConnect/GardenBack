import pytest
from fastapi import HTTPException
from db.models import Area, Cell, Sensor, Analytic, AnalyticType
from services.area.repository import get_area_by_id
from datetime import datetime

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

    return {"parcelle_id": parcelle.id, "planche_id": planche.id}

def test_get_area_not_found(db_session):
    """Teste que l'erreur AreaNotFoundError est levée si l'ID n'existe pas."""
    with pytest.raises(HTTPException) as excinfo:
        get_area_by_id(db_session, 999)
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Area not found"

def test_get_area_by_id_success(db_session, setup_hierarchy):
    """Teste la récupération réussie d'une zone et sa structure."""
    parcelle_id = setup_hierarchy["parcelle_id"]

    # Action
    result = get_area_by_id(db_session, parcelle_id)

    # Assertions
    assert result.name == "Parcelle Test"
    assert result.color == "#111111"
    
    # Vérifier la sous-zone (planche)
    assert len(result.areas) == 1
    planche_schema = result.areas[0]
    assert planche_schema.name == "Planche Test"
    
    # Vérifier la cellule dans la planche
    assert len(planche_schema.cells) == 1
    cellule_schema = planche_schema.cells[0]
    assert cellule_schema.name == "Cellule Test"