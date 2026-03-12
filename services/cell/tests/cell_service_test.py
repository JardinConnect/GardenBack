import pytest
import uuid
from datetime import datetime, UTC, timedelta
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
    get_all_analytics_for_cell,
    update_multiple_cells_settings
)
from services.cell.schemas import CellCreate, CellUpdate, CellSettingsUpdate
from services.cell.errors import CellNotFoundError, ParentCellNotFoundError, InvalidDateRangeError, CellsNotFoundError


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
        occurred_at=datetime.now(UTC)
    )
    analytic_hum = AnalyticModel(
        sensor_id=sensor_hum.id,
        sensor_code="HUM-01",
        analytic_type=AnalyticType.AIR_HUMIDITY,
        value=60.0,
        occurred_at=datetime.now(UTC)
    )
    db_session.add_all([analytic_temp, analytic_hum])
    db_session.commit()
    
    return {"cell": cell, "sensor_temp": sensor_temp, "sensor_hum": sensor_hum}


@pytest.fixture(scope="function")
def setup_multiple_cells(db_session):
    """Crée plusieurs cellules de test."""
    cell1 = CellModel(name="Cell 1")
    cell2 = CellModel(name="Cell 2")
    cell3 = CellModel(name="Cell 3", settings={"existing_key": "old_value"})
    db_session.add_all([cell1, cell2, cell3])
    db_session.commit()
    db_session.refresh(cell1)
    db_session.refresh(cell2)
    db_session.refresh(cell3)
    return [cell1, cell2, cell3]

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
    
    update_data = CellUpdate(name="New Name") # type: ignore
    
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
    
    update_data = CellUpdate(area_id=new_area.id) # type: ignore
    
    result = update_cell(db_session, cell.id, update_data)
    
    assert result.area_id == new_area.id


def test_update_cell_with_invalid_area(db_session, setup_area):
    """Teste que la mise à jour échoue si l'area n'existe pas."""
    cell = CellModel(name="Cell", area_id=setup_area.id)
    db_session.add(cell)
    db_session.commit()
    
    update_data = CellUpdate(area_id=uuid.uuid4()) # type: ignore
    
    with pytest.raises(ParentCellNotFoundError):
        update_cell(db_session, cell.id, update_data)


def test_update_cell_not_found(db_session):
    """Teste que update_cell lève une erreur si la cellule n'existe pas."""
    update_data = CellUpdate(name="Ghost Cell") # type: ignore
    
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


def test_get_cell_with_analytics_date_filter(db_session, setup_cell_with_sensors):
    """Teste que le filtre de date sur get_cell fonctionne pour les analytics."""
    cell = setup_cell_with_sensors["cell"]
    sensor_temp = setup_cell_with_sensors["sensor_temp"]
    
    # Add an old analytic that should be filtered out
    old_analytic = AnalyticModel(
        sensor_id=sensor_temp.id,
        sensor_code="TEMP-01",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=10.0,
        occurred_at=datetime(2020, 1, 1, tzinfo=UTC)
    )
    db_session.add(old_analytic)
    db_session.commit()

    from_date = datetime.now(UTC) - timedelta(days=1)
    result = get_cell(db_session, cell.id, from_date=from_date)

    assert result is not None
    assert len(result.analytics[AnalyticType.AIR_TEMPERATURE]) == 1
    assert result.analytics[AnalyticType.AIR_TEMPERATURE][0].value == 25.5

def test_get_cell_with_invalid_date_range(db_session, setup_cell_with_sensors):
    """Teste que get_cell lève une erreur si la plage de dates est invalide."""
    cell = setup_cell_with_sensors["cell"]
    from_date = datetime(2025, 1, 1, tzinfo=UTC)
    to_date = datetime(2024, 1, 1, tzinfo=UTC)

    with pytest.raises(InvalidDateRangeError):
        get_cell(db_session, cell.id, from_date=from_date, to_date=to_date)


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
        occurred_at=datetime(2020, 1, 1, tzinfo=UTC)
    )
    db_session.add(old_analytic)
    db_session.commit()
    
    result = get_analytics_for_cell(db_session, cell.id)
    
    assert AnalyticType.AIR_TEMPERATURE in result
    assert len(result[AnalyticType.AIR_TEMPERATURE]) == 1 # type: ignore
    assert result[AnalyticType.AIR_TEMPERATURE][0].value == 25.5 # type: ignore


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
        occurred_at=datetime(2020, 1, 1, tzinfo=UTC)
    )
    db_session.add(old_analytic)
    db_session.commit()
    
    result = get_all_analytics_for_cell(db_session, cell.id)
    
    assert AnalyticType.AIR_TEMPERATURE in result
    assert len(result[AnalyticType.AIR_TEMPERATURE]) == 2
    values = {a.value for a in result[AnalyticType.AIR_TEMPERATURE]}
    assert 10.0 in values
    assert 25.5 in values


# =========================================================
# TESTS FOR update_multiple_cells_settings
# =========================================================

def test_update_multiple_cells_settings_success(db_session, setup_multiple_cells):
    """Teste la mise à jour réussie des paramètres de plusieurs cellules."""
    cells = setup_multiple_cells
    cell_ids_to_update = [cells[0].id, cells[2].id]
    
    settings_data = CellSettingsUpdate(
        cell_ids=cell_ids_to_update,
        daily_update_count=2,
        update_times=["10:00", "22:00"],
        measurement_frequency=900
    )
    
    update_multiple_cells_settings(db_session, settings_data)
    
    db_session.refresh(cells[0])
    db_session.refresh(cells[1])
    db_session.refresh(cells[2])
    
    # Cell 1 (initialement sans settings) doit être mise à jour
    assert cells[0].settings is not None
    assert cells[0].settings["daily_update_count"] == 2
    assert cells[0].settings["update_times"] == ["10:00", "22:00"]
    assert cells[0].settings["measurement_frequency"] == 900
    
    # Cell 2 ne doit PAS être mise à jour
    assert cells[1].settings is None
    
    # Cell 3 (avec settings existants) doit être mise à jour et préserver les anciennes clés
    assert cells[2].settings is not None
    assert cells[2].settings["daily_update_count"] == 2
    assert cells[2].settings["measurement_frequency"] == 900
    assert cells[2].settings["existing_key"] == "old_value"


def test_update_multiple_cells_settings_cell_not_found(db_session, setup_multiple_cells):
    """Teste que la fonction lève une erreur si une cellule n'est pas trouvée."""
    cells = setup_multiple_cells
    non_existent_id = uuid.uuid4()
    cell_ids_to_update = [cells[0].id, non_existent_id]
    
    settings_data = CellSettingsUpdate(
        cell_ids=cell_ids_to_update,
        daily_update_count=1,
        update_times=["12:00"],
        measurement_frequency=300
    )
    
    with pytest.raises(CellsNotFoundError) as exc_info:
        update_multiple_cells_settings(db_session, settings_data)
        
    assert non_existent_id in exc_info.value.not_found_ids


def test_update_multiple_cells_settings_empty_list(db_session):
    """Teste que la fonction ne lève pas d'erreur avec une liste vide d'IDs."""
    settings_data = CellSettingsUpdate(cell_ids=[], daily_update_count=1, update_times=[], measurement_frequency=300)
    
    try:
        update_multiple_cells_settings(db_session, settings_data)
    except Exception as e:
        pytest.fail(f"update_multiple_cells_settings a levé une exception inattendue avec une liste vide: {e}")


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