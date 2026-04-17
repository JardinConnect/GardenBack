import pytest
import uuid
from datetime import datetime, UTC
from db.models import Cell as CellModel, Area as AreaModel, Sensor as SensorModel, User as UserModel, RoleEnum
from services.cell.repository import (
    get_cell_by_id,
    get_cells,
    create_cell,
    delete_cell,
    update_cell
)
from services.cell.schemas import Cell as CellSchema, CellUpdate, CellCreate
from services.cell.errors import CellNotFoundError


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
def setup_cell(db_session, setup_area):
    """Crée une cellule de test."""
    cell = CellModel(name="Test Cell", area_id=setup_area.id, is_tracked=True, deviceID="REPO-TEST-DEVICE-1")
    db_session.add(cell)
    db_session.commit()
    return cell

@pytest.fixture(scope="function")
def setup_user(db_session):
    """Crée un utilisateur de test."""
    # Utilise un email unique pour éviter les conflits entre les tests
    email = f"test.user.{uuid.uuid4()}@example.com"
    user = UserModel(
        first_name="Test",
        last_name="User",
        email=email,
        password="password",
        role=RoleEnum.ADMIN
    )
    db_session.add(user)
    db_session.commit()
    return user

# =========================================================
# TESTS FOR get_cell_by_id
# =========================================================

def test_get_cell_by_id_success(db_session, setup_cell):
    """Teste la récupération réussie d'une cellule par son ID."""
    result = get_cell_by_id(db_session, setup_cell.id)
    
    assert result is not None
    assert isinstance(result, CellSchema)
    assert result.id == setup_cell.id
    assert result.name == "Test Cell"
    assert result.area_id == setup_cell.area_id
    assert result.is_tracked is True
    assert result.location == "Test Area"


def test_get_cell_by_id_not_found(db_session):
    """Teste que get_cell_by_id lève une erreur si l'ID n'existe pas."""
    with pytest.raises(CellNotFoundError):
        get_cell_by_id(db_session, uuid.uuid4())


# =========================================================
# TESTS FOR get_cells
# =========================================================

def test_get_cells_success(db_session, setup_area):
    """Teste la récupération de toutes les cellules."""
    cell1 = CellModel(name="Cell 1", area_id=setup_area.id, is_tracked=True, deviceID="REPO-TEST-DEVICE-2")
    cell2 = CellModel(name="Cell 2", area_id=setup_area.id, is_tracked=False, deviceID="REPO-TEST-DEVICE-3")
    db_session.add_all([cell1, cell2])
    db_session.commit()
    
    results = get_cells(db_session)
    
    assert len(results) == 2
    assert all(isinstance(cell, CellSchema) for cell in results)
    cell_names = {cell.name for cell in results}
    assert "Cell 1" in cell_names
    assert "Cell 2" in cell_names
    for cell in results:
        assert cell.location == "Test Area"


def test_get_cells_empty_database(db_session):
    """Teste que get_cells retourne une liste vide si aucune cellule n'existe."""
    results = get_cells(db_session)
    assert results == []


# =========================================================
# TESTS FOR create_cell
# =========================================================

def test_create_cell_with_area(db_session, setup_area, setup_user):
    """Teste la création d'une cellule avec une area."""
    cell_data = CellCreate(
        name="New Cell",
        area_id=setup_area.id,
        deviceID="DEVICE-1"
    )

    result = create_cell(db_session, cell_data, setup_user)
    
    assert result is not None
    assert isinstance(result, CellSchema)
    assert result.name == "New Cell"
    assert result.area_id == setup_area.id
    assert result.is_tracked is False  # Default value in DB model
    assert result.location == "Test Area"
    assert result.originator.id == setup_user.id
    assert result.updater.id == setup_user.id
    
    db_cell = db_session.query(CellModel).filter(CellModel.id == result.id).first()
    assert db_cell is not None
    assert db_cell.name == "New Cell"


def test_create_cell_without_area(db_session, setup_user):
    """Teste la création d'une cellule sans area."""
    cell_data = CellCreate(
        name="Orphan Cell",
        area_id=None,
        deviceID="DEVICE-2"
    )

    result = create_cell(db_session, cell_data, setup_user)
    
    assert result is not None
    assert result.name == "Orphan Cell"
    assert result.area_id is None
    assert result.is_tracked is False
    assert result.location == ""

def test_create_cell_no_commit(db_session, setup_area, setup_user):
    """Teste que create_cell avec commit=False garde la transaction ouverte."""
    cell_data = CellCreate(name="Uncommitted Cell", area_id=setup_area.id, deviceID="DEVICE-3")
    
    # On crée sans commit
    result = create_cell(db_session, cell_data, setup_user, commit=False)
    
    assert result is not None
    assert result.id is not None  # L'ID a bien été généré par le flush
    
    # On simule une erreur et on annule la transaction
    db_session.rollback()
    
    # La cellule ne doit pas exister en base
    with pytest.raises(CellNotFoundError):
        get_cell_by_id(db_session, result.id)

# =========================================================
# TESTS FOR delete_cell
# =========================================================

def test_delete_cell_success(db_session, setup_cell):
    """Teste la suppression (soft delete) réussie d'une cellule."""
    cell_id = setup_cell.id
    
    result = delete_cell(db_session, cell_id)
    
    assert result is None
    
    # Après un soft delete, la cellule ne doit plus être récupérable par get_cell_by_id
    with pytest.raises(CellNotFoundError):
        get_cell_by_id(db_session, cell_id)


def test_delete_cell_not_found(db_session):
    """Teste que delete_cell lève une erreur si la cellule n'existe pas."""
    with pytest.raises(CellNotFoundError):
        delete_cell(db_session, uuid.uuid4())


def test_delete_cell_with_sensors(db_session, setup_cell):
    """Teste que le soft-delete d'une cellule soft-delete aussi ses capteurs."""
    sensor = SensorModel(
        sensor_id="SENSOR-01",
        sensor_type="temperature",
        cell_id=setup_cell.id
    )
    db_session.add(sensor)
    db_session.commit()
    sensor_id = sensor.id

    delete_cell(db_session, setup_cell.id)

    # Vérifier que le capteur est bien soft-deleted en le requêtant directement
    soft_deleted_sensor = db_session.query(SensorModel).filter(SensorModel.id == sensor_id).first()
    assert soft_deleted_sensor is not None
    assert soft_deleted_sensor.deleted_at is not None

# =========================================================
# TESTS FOR update_cell
# =========================================================

def test_update_cell_name(db_session, setup_cell, setup_user):
    """Teste la mise à jour du nom d'une cellule."""
    update_data = CellUpdate(name="Updated Cell Name") # type: ignore
    
    result = update_cell(db_session, setup_cell.id, update_data, setup_user)
    
    assert result.name == "Updated Cell Name"
    assert result.location == "Test Area"
    assert result.updater.id == setup_user.id
    
    db_session.refresh(setup_cell)
    assert setup_cell.name == "Updated Cell Name"
    assert setup_cell.updater_id == setup_user.id


def test_update_cell_area(db_session, setup_cell, setup_user):
    """Teste le changement d'area d'une cellule."""
    new_area = AreaModel(name="New Area", color="#654321")
    db_session.add(new_area)
    db_session.commit()
    
    update_data = CellUpdate(area_id=new_area.id) # type: ignore
    
    result = update_cell(db_session, setup_cell.id, update_data, setup_user)
    
    assert result.area_id == new_area.id
    assert result.location == "New Area"
    assert result.updater.id == setup_user.id
    
    db_session.refresh(setup_cell)
    assert setup_cell.area_id == new_area.id


def test_update_cell_is_tracked(db_session, setup_cell, setup_user):
    """Teste la mise à jour du statut is_tracked."""
    update_data = CellUpdate(is_tracked=False) # type: ignore
    
    result = update_cell(db_session, setup_cell.id, update_data, setup_user)
    
    assert result.is_tracked is False
    assert result.location == "Test Area"
    assert result.updater.id == setup_user.id
    
    db_session.refresh(setup_cell)
    assert setup_cell.is_tracked is False


def test_update_cell_multiple_fields(db_session, setup_cell, setup_user):
    """Teste la mise à jour de plusieurs champs en même temps."""
    new_area = AreaModel(name="Another Area")
    db_session.add(new_area)
    db_session.commit()
    
    update_data = CellUpdate(
        name="Multi Update Cell",
        area_id=new_area.id,
        is_tracked=False
    )

    result = update_cell(db_session, setup_cell.id, update_data, setup_user)
    
    assert result.name == "Multi Update Cell"
    assert result.area_id == new_area.id
    assert result.is_tracked is False
    assert result.location == "Another Area"


def test_update_cell_not_found(db_session, setup_user):
    """Teste que update_cell lève une erreur si la cellule n'existe pas."""
    update_data = CellUpdate(name="Ghost Cell") # type: ignore
    
    with pytest.raises(CellNotFoundError):
        update_cell(db_session, uuid.uuid4(), update_data, setup_user)


def test_update_cell_remove_area(db_session, setup_cell, setup_user):
    """Teste le détachement d'une cellule de son area."""
    update_data = CellUpdate(area_id=None) # type: ignore
    
    result = update_cell(db_session, setup_cell.id, update_data, setup_user)
    
    assert result.area_id is None
    assert result.location == ""
    
    db_session.refresh(setup_cell)
    assert setup_cell.area_id is None