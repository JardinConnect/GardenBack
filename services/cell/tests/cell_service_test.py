import pytest
import uuid
from datetime import datetime, UTC
from db.models import (
    Cell as CellModel,
    Area as AreaModel,
    Sensor as SensorModel,
    Analytic as AnalyticModel,
    AnalyticType
)
from services.cell.service import (
    create_cell,
    delete_cell,
    update_cell,
    get_cell,
    get_cells,
    get_analytics_for_cell,
    get_all_analytics_for_cell
)
from services.cell.schemas import CellCreate, CellUpdate
from services.cell.errors import CellNotFoundError, ParentCellNotFoundError


# =========================================================
# FIXTURES
# =========================================================

@pytest.fixture(scope="function")
def setup_area(db_session):
    """Crée une area de test."""
    area = AreaModel(name="Test Area", color="#123456")
    db_session.add(area)
    db_session.commit()
    return area


@pytest.fixture(scope="function")
def setup_cell_with_sensors(db_session, setup_area):
    """Crée une cellule avec des capteurs et des analytics."""
    cell = CellModel(name="Test Cell", area_id=setup_area.id, is_tracked=True)
    db_session.add(cell)
    db_session.commit()
    
    sensor_temp = SensorModel(sensor_id="TEMP-01", sensor_type="temperature", cell_id=cell.id)
    sensor_hum = SensorModel(sensor_id="HUM-01", sensor_type="humidity", cell_id=cell.id)
    db_session.add_all([sensor_temp, sensor_hum])
    db_session.commit()
    
    analytic_temp = AnalyticModel(
        sensor_id=sensor_temp.id,
        sensor_code="TEMP-01",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=25.5,
        occured_at=datetime.now(UTC)
    )
    analytic_hum = AnalyticModel(
        sensor_id=sensor_hum.id,
        sensor_code="HUM-01",
        analytic_type=AnalyticType.AIR_HUMIDITY,
        value=60.0,
        occured_at=datetime.now(UTC)
    )
    db_session.add_all([analytic_temp, analytic_hum])
    db_session.commit()
    
    return {"cell": cell, "sensor_temp": sensor_temp, "sensor_hum": sensor_hum}


# =========================================================
# TESTS FOR create_cell
# =========================================================

def test_create_cell_with_valid_area(db_session, setup_area):
    """Teste la création d'une cellule avec une area valide."""
    cell_data = CellCreate(name="New Cell", area_id=setup_area.id)
    
    result = create_cell(db_session, cell_data)
    
    assert result is not None
    assert result.name == "New Cell"
    assert result.area_id == setup_area.id
    
    db_cell = db_session.query(CellModel).filter(CellModel.id == result.id).first()
    assert db_cell is not None


def test_create_cell_without_area(db_session):
    """Teste la création d'une cellule sans area."""
    cell_data = CellCreate(name="Orphan Cell", area_id=None)
    
    result = create_cell(db_session, cell_data)
    
    assert result is not None
    assert result.name == "Orphan Cell"
    assert result.area_id is None


def test_create_cell_with_invalid_area(db_session):
    """Teste que la création échoue si l'area n'existe pas."""
    cell_data = CellCreate(name="Invalid Cell", area_id=uuid.uuid4())
    
    with pytest.raises(ParentCellNotFoundError):
        create_cell(db_session, cell_data)


# =========================================================
# TESTS FOR delete_cell
# =========================================================

def test_delete_cell_success(db_session, setup_area):
    """Teste la suppression réussie d'une cellule."""
    cell = CellModel(name="Cell to Delete", area_id=setup_area.id)
    db_session.add(cell)
    db_session.commit()
    cell_id = cell.id
    
    result = delete_cell(db_session, cell_id)
    
    assert result is None
    
    deleted_cell = db_session.query(CellModel).filter(CellModel.id == cell_id).first()
    assert deleted_cell is None


def test_delete_cell_not_found(db_session):
    """Teste que delete_cell lève une erreur si la cellule n'existe pas."""
    with pytest.raises(CellNotFoundError):
        delete_cell(db_session, uuid.uuid4())


# =========================================================
# TESTS FOR update_cell
# =========================================================

def test_update_cell_name(db_session, setup_area):
    """Teste la mise à jour du nom d'une cellule."""
    cell = CellModel(name="Old Name", area_id=setup_area.id)
    db_session.add(cell)
    db_session.commit()
    
    update_data = CellUpdate(name="New Name")
    
    result = update_cell(db_session, cell.id, update_data)
    
    assert result.name == "New Name"


def test_update_cell_change_area(db_session, setup_area):
    """Teste le changement d'area d'une cellule."""
    cell = CellModel(name="Cell", area_id=setup_area.id)
    db_session.add(cell)
    db_session.commit()
    
    new_area = AreaModel(name="New Area")
    db_session.add(new_area)
    db_session.commit()
    
    update_data = CellUpdate(area_id=new_area.id)
    
    result = update_cell(db_session, cell.id, update_data)
    
    assert result.area_id == new_area.id


def test_update_cell_with_invalid_area(db_session, setup_area):
    """Teste que la mise à jour échoue si l'area n'existe pas."""
    cell = CellModel(name="Cell", area_id=setup_area.id)
    db_session.add(cell)
    db_session.commit()
    
    update_data = CellUpdate(area_id=uuid.uuid4())
    
    with pytest.raises(ParentCellNotFoundError):
        update_cell(db_session, cell.id, update_data)


def test_update_cell_not_found(db_session):
    """Teste que update_cell lève une erreur si la cellule n'existe pas."""
    update_data = CellUpdate(name="Ghost Cell")
    
    with pytest.raises(CellNotFoundError):
        update_cell(db_session, uuid.uuid4(), update_data)


# =========================================================
# TESTS FOR get_cell
# =========================================================

def test_get_cell_with_analytics(db_session, setup_cell_with_sensors):
    """Teste la récupération d'une cellule avec ses analytics."""
    cell = setup_cell_with_sensors["cell"]
    
    result = get_cell(db_session, cell.id)
    
    assert result is not None
    assert result.id == cell.id
    assert result.name == "Test Cell"
    assert result.analytics is not None
    assert AnalyticType.AIR_TEMPERATURE in result.analytics
    assert AnalyticType.AIR_HUMIDITY in result.analytics


def test_get_cell_not_found(db_session):
    """Teste que get_cell lève une erreur si la cellule n'existe pas."""
    with pytest.raises(CellNotFoundError):
        get_cell(db_session, uuid.uuid4())


def test_get_cell_without_sensors(db_session, setup_area):
    """Teste la récupération d'une cellule sans capteurs."""
    cell = CellModel(name="Empty Cell", area_id=setup_area.id)
    db_session.add(cell)
    db_session.commit()
    
    result = get_cell(db_session, cell.id)
    
    assert result is not None
    assert result.analytics == {}


# =========================================================
# TESTS FOR get_cells
# =========================================================

def test_get_cells_with_analytics(db_session, setup_cell_with_sensors):
    """Teste la récupération de toutes les cellules avec leurs analytics."""
    results = get_cells(db_session)
    
    assert len(results) >= 1
    cell = next((c for c in results if c.id == setup_cell_with_sensors["cell"].id), None)
    assert cell is not None
    assert AnalyticType.AIR_TEMPERATURE in cell.analytics


def test_get_cells_empty_database(db_session):
    """Teste que get_cells lève une erreur si aucune cellule n'existe."""
    with pytest.raises(CellNotFoundError):
        get_cells(db_session)


# =========================================================
# TESTS FOR get_analytics_for_cell
# =========================================================

def test_get_analytics_for_cell_latest_only(db_session, setup_cell_with_sensors):
    """Teste que seule la dernière analytique de chaque type est retournée."""
    cell = setup_cell_with_sensors["cell"]
    sensor_temp = setup_cell_with_sensors["sensor_temp"]
    
    old_analytic = AnalyticModel(
        sensor_id=sensor_temp.id,
        sensor_code="TEMP-01",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=10.0,
        occured_at=datetime(2020, 1, 1, tzinfo=UTC)
    )
    db_session.add(old_analytic)
    db_session.commit()
    
    result = get_analytics_for_cell(db_session, cell.id)
    
    assert AnalyticType.AIR_TEMPERATURE in result
    assert len(result[AnalyticType.AIR_TEMPERATURE]) == 1
    assert result[AnalyticType.AIR_TEMPERATURE][0].value == 25.5


def test_get_analytics_for_cell_no_sensors(db_session, setup_area):
    """Teste que la fonction retourne un dict vide pour une cellule sans capteurs."""
    cell = CellModel(name="Empty Cell", area_id=setup_area.id)
    db_session.add(cell)
    db_session.commit()
    
    result = get_analytics_for_cell(db_session, cell.id)
    
    assert result == {}


def test_get_analytics_for_cell_not_found(db_session):
    """Teste que la fonction lève une erreur si la cellule n'existe pas."""
    with pytest.raises(CellNotFoundError):
        get_analytics_for_cell(db_session, uuid.uuid4())


# =========================================================
# TESTS FOR get_all_analytics_for_cell
# =========================================================

def test_get_all_analytics_for_cell(db_session, setup_cell_with_sensors):
    """Teste la récupération de toutes les analytics d'une cellule."""
    cell = setup_cell_with_sensors["cell"]
    sensor_temp = setup_cell_with_sensors["sensor_temp"]
    
    old_analytic = AnalyticModel(
        sensor_id=sensor_temp.id,
        sensor_code="TEMP-01",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=10.0,
        occured_at=datetime(2020, 1, 1, tzinfo=UTC)
    )
    db_session.add(old_analytic)
    db_session.commit()
    
    result = get_all_analytics_for_cell(db_session, cell.id)
    
    assert AnalyticType.AIR_TEMPERATURE in result
    assert len(result[AnalyticType.AIR_TEMPERATURE]) == 2
    values = {a.value for a in result[AnalyticType.AIR_TEMPERATURE]}
    assert 10.0 in values
    assert 25.5 in values


def test_get_all_analytics_for_cell_grouping(db_session, setup_cell_with_sensors):
    """Teste que les analytics sont bien groupées par type."""
    cell = setup_cell_with_sensors["cell"]
    
    result = get_all_analytics_for_cell(db_session, cell.id)
    
    assert AnalyticType.AIR_TEMPERATURE in result
    assert AnalyticType.AIR_HUMIDITY in result
    assert len(result[AnalyticType.AIR_TEMPERATURE]) == 1
    assert len(result[AnalyticType.AIR_HUMIDITY]) == 1


def test_get_all_analytics_for_cell_not_found(db_session):
    """Teste que la fonction lève une erreur si la cellule n'existe pas."""
    with pytest.raises(CellNotFoundError):
        get_all_analytics_for_cell(db_session, uuid.uuid4())