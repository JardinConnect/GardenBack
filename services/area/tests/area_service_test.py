import pytest
from datetime import datetime, timedelta, UTC
import uuid

from fastapi import HTTPException
from db.models import Area as AreaModel, Cell as CellModel, Sensor as SensorModel, Analytic as AnalyticModel, AnalyticType, User as UserModel, RoleEnum
from services.area.service import get_area_with_analytics, create_area, delete_area, update_area, _calculate_daily_averages, get_full_location_path_for_cell
from services.area.schemas import AreaCreate, AreaUpdate
from services.area.errors import ParentAreaNotFoundError, AreaNotFoundError


@pytest.fixture
def setup_user(db_session):
    user = UserModel(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password="hashedpassword",
        role=RoleEnum.ADMIN
    )
    db_session.add(user)
    db_session.commit()
    return user

# === Tests for create_area ===

def test_create_area_as_root_success(db_session, setup_user):
    """Vérifie la création réussie d'une zone racine."""
    # Arrange
    area_data = AreaCreate(name="Root Garden", color="#00FF00")

    # Act
    result = create_area(db_session, area_data, setup_user)

    # Assert
    # Vérifier le schéma Pydantic retourné
    assert result.id is not None
    assert result.name == "Root Garden"
    assert result.color == "#00FF00"
    assert result.level == 1
    assert result.originator.id == setup_user.id
    assert result.updater.id == setup_user.id
    assert result.areas == []
    assert result.cells == []

    # Vérifier les données dans la base de données
    db_area = db_session.query(AreaModel).filter(AreaModel.id == result.id).first()
    assert db_area is not None
    assert db_area.name == "Root Garden"
    assert db_area.color == "#00FF00"
    assert db_area.parent_id is None
    assert db_area.originator_id == setup_user.id
    assert db_area.updater_id == setup_user.id

def test_create_area_as_child_success(db_session, setup_user):
    """Vérifie la création réussie d'une zone enfant."""
    # Arrange
    parent_area = AreaModel(name="Parent Area")
    db_session.add(parent_area)
    db_session.commit()

    area_data = AreaCreate(name="Child Area", color="#FFA500", parent_id=parent_area.id)

    # Act
    result = create_area(db_session, area_data, setup_user)

    # Assert
    # Vérifier le schéma Pydantic retourné
    assert result.name == "Child Area"
    assert result.level == 2

    # Vérifier les données dans la base de données
    db_area = db_session.query(AreaModel).filter(AreaModel.id == result.id).first()
    assert db_area is not None
    assert db_area.name == "Child Area"
    assert db_area.parent_id == parent_area.id
    assert db_area.originator_id == setup_user.id
    assert db_area.updater_id == setup_user.id

def test_create_area_with_nonexistent_parent_fails(db_session, setup_user):
    """Vérifie qu'une erreur est levée si le parent n'existe pas."""
    # Arrange
    area_data = AreaCreate(name="Orphan Area", parent_id=uuid.uuid4())

    # Act & Assert
    with pytest.raises(ParentAreaNotFoundError):
        create_area(db_session, area_data, setup_user)

    # Vérifier qu'aucune zone n'a été ajoutée
    count = db_session.query(AreaModel).count()
    assert count == 0


# === Tests for delete_area ===

def test_delete_area_not_found(db_session):
    """Vérifie qu'une erreur est levée lors de la suppression d'une zone inexistante."""
    with pytest.raises(AreaNotFoundError):
        delete_area(db_session, uuid.uuid4())


def test_delete_area_single_with_cell(db_session):
    """Vérifie la suppression d'une zone unique et le détachement de sa cellule."""
    # Arrange
    area = AreaModel(name="Area to delete")
    db_session.add(area)
    db_session.commit()

    cell = CellModel(name="Cell to detach", area_id=area.id)
    db_session.add(cell)
    db_session.commit()

    area_id = area.id
    cell_id = cell.id

    # Act
    delete_area(db_session, area_id)

    # Assert
    # Vérifier que la zone a été supprimée
    deleted_area = db_session.query(AreaModel).filter(AreaModel.id == area_id).first()
    assert deleted_area is None

    # Vérifier que la cellule existe toujours mais est détachée
    detached_cell = db_session.query(CellModel).filter(CellModel.id == cell_id).first()
    assert detached_cell is not None
    assert detached_cell.area_id is None
    assert detached_cell.name == "Cell to detach"


def test_delete_area_with_hierarchy(db_session):
    """
    Vérifie la suppression d'une zone parente, de ses enfants,
    et le détachement de toutes les cellules associées.
    """
    # Arrange
    # Structure: Parent -> Child
    parent = AreaModel(name="Parent")
    db_session.add(parent)
    db_session.commit()

    child = AreaModel(name="Child", parent_id=parent.id)
    db_session.add(child)
    db_session.commit()

    # Cellules attachées à chaque niveau
    cell_parent = CellModel(name="Cell Parent", area_id=parent.id)
    cell_child = CellModel(name="Cell Child", area_id=child.id)
    db_session.add_all([cell_parent, cell_child])
    db_session.commit()

    parent_id = parent.id

    # Act: Supprimer la zone parente
    delete_area(db_session, parent_id)

    # Assert
    assert db_session.query(AreaModel).count() == 0
    assert db_session.query(CellModel).count() == 2

    # Vérifie que toutes les cellules ont bien leur area_id à None
    assert db_session.query(CellModel).filter(CellModel.area_id != None).count() == 0


# === Tests for get_full_location_path_for_cell ===

def test_get_full_location_path_for_cell_with_deep_hierarchy(db_session):
    """
    Tests that the full path is correctly constructed for a cell in a deep hierarchy.
    e.g., Parcelle > Planche > Section
    """
    # 1. Create hierarchy
    parcelle = AreaModel(name="Parcelle Nord", color="#2E8B57")
    db_session.add(parcelle)
    db_session.commit()

    planche = AreaModel(name="Planche Tomates", color="#FF6347", parent_id=parcelle.id)
    db_session.add(planche)
    db_session.commit()

    section = AreaModel(name="Section Tomates Cerises", color="#FF4500", parent_id=planche.id)
    db_session.add(section)
    db_session.commit()

    # 2. Create cell
    cell = CellModel(name="Rangée A", area_id=section.id)
    db_session.add(cell)
    db_session.commit()

    # 3. Call function and assert
    path = get_full_location_path_for_cell(cell)
    assert path == "Parcelle Nord > Planche Tomates > Section Tomates Cerises"


def test_get_full_location_path_for_cell_with_root_area(db_session):
    """
    Tests that the path is correct for a cell directly under a root area.
    """
    parcelle = AreaModel(name="Parcelle Sud", color="#228B22")
    db_session.add(parcelle)
    db_session.commit()

    cell = CellModel(name="Carottes", area_id=parcelle.id)
    db_session.add(cell)
    db_session.commit()

    path = get_full_location_path_for_cell(cell)
    assert path == "Parcelle Sud"


def test_get_full_location_path_for_cell_with_no_area(db_session):
    """
    Tests that an empty string is returned for a cell with no associated area.
    """
    cell = CellModel(name="Orphan Cell", area_id=None)
    db_session.add(cell)
    db_session.commit()

    path = get_full_location_path_for_cell(cell)
    assert path == ""


# === Tests for Helper Functions (_get_analytics_for_area, _calculate_daily_averages) ===

def test_calculate_daily_averages_basic():
    """Vérifie le calcul de base des moyennes journalières."""
    # Arrange
    now = datetime.now(UTC)
    analytics = [
        AnalyticModel(analytic_type=AnalyticType.AIR_TEMPERATURE, value=20, occurred_at=now),
        AnalyticModel(analytic_type=AnalyticType.AIR_TEMPERATURE, value=30, occurred_at=now),
        AnalyticModel(analytic_type=AnalyticType.AIR_HUMIDITY, value=60, occurred_at=now - timedelta(days=1)),
    ]

    # Act
    result = _calculate_daily_averages(analytics)

    # Assert
    assert AnalyticType.AIR_TEMPERATURE in result
    assert len(result[AnalyticType.AIR_TEMPERATURE]) == 7

    today_avg_temp = next((a.value for a in result[AnalyticType.AIR_TEMPERATURE] if a.occurred_at.date() == now.date()), None)
    assert today_avg_temp == 25.0

    yesterday_avg_hum = next((a.value for a in result[AnalyticType.AIR_HUMIDITY] if a.occurred_at.date() == (now - timedelta(days=1)).date()), None)
    assert yesterday_avg_hum == 60.0

    two_days_ago_avg_temp = next((a.value for a in result[AnalyticType.AIR_TEMPERATURE] if a.occurred_at.date() == (now - timedelta(days=2)).date()), None)
    assert two_days_ago_avg_temp == 0.0

def test_calculate_daily_averages_empty_input():
    """Vérifie que la fonction gère une liste d'analytiques vide."""
    result = _calculate_daily_averages([])
    for analytic_type in AnalyticType:
        assert len(result[analytic_type]) == 0

def test_calculate_daily_averages_rounding():
    """Vérifie que les valeurs moyennes sont bien arrondies à 2 décimales."""
    now = datetime.now(UTC)
    analytics = [AnalyticModel(analytic_type=AnalyticType.LIGHT, value=v, occurred_at=now) for v in [10, 15, 12]] # Moyenne = 12.333...

    result = _calculate_daily_averages(analytics)

    today_avg_light = next((a.value for a in result[AnalyticType.LIGHT] if a.occurred_at.date() == now.date()), None)
    assert today_avg_light == 12.33

# === Tests for get_area_with_analytics ===

@pytest.fixture(scope="function")
def setup_hierarchy_for_service(db_session):
    """Crée une hiérarchie de test : Parcelle -> Planche -> Cellule."""
    parcelle = AreaModel(name="Parcelle Test", color="#111111")
    db_session.add(parcelle)
    db_session.commit()

    planche = AreaModel(name="Planche Test", color="#222222", parent_id=parcelle.id)
    db_session.add(planche)
    db_session.commit()

    cellule = CellModel(name="Cellule Test", area_id=planche.id)
    db_session.add(cellule)
    db_session.commit()

    return {"parcelle_id": parcelle.id, "planche_id": planche.id}

def test_get_area_with_analytics_structure(db_session, setup_hierarchy_for_service):
    """Teste la récupération réussie d'une zone et sa structure hiérarchique."""
    parcelle_id = setup_hierarchy_for_service["parcelle_id"]

    # Action
    result = get_area_with_analytics(db_session, parcelle_id)
    assert result is not None
    # Assertions
    assert result.name == "Parcelle Test"
    assert result.color == "#111111"
    assert result.level == 1
    
    # Vérifier la sous-zone (planche)
    assert len(result.areas) == 1
    planche_schema = result.areas[0]
    assert planche_schema.name == "Planche Test"
    assert planche_schema.level == 2
    
    # Vérifier la cellule dans la planche
    assert len(planche_schema.cells) == 1
    cellule_schema = planche_schema.cells[0]
    assert cellule_schema.name == "Cellule Test"
    assert cellule_schema.location == "Parcelle Test > Planche Test"

def test_get_area_not_found(db_session):
    """
    Vérifie que la fonction retourne None si l'ID de la zone n'existe pas.
    """
    area = get_area_with_analytics(db_session, uuid.uuid4())
    assert area is None


def test_get_area_single_level_with_analytics(db_session):
    """
    Vérifie le calcul des moyennes pour une zone simple sans sous-zones.
    """
    # --- Préparation ---
    area1 = AreaModel(name="Area 1")
    db_session.add(area1)
    db_session.commit()

    cell1 = CellModel(name="Cell 1", area_id=area1.id)
    db_session.add(cell1)
    db_session.commit()

    sensor_temp = SensorModel(sensor_id="T1", sensor_type="temperature", cell_id=cell1.id)
    sensor_hum = SensorModel(sensor_id="H1", sensor_type="humidity", cell_id=cell1.id)
    sensor_soil_hum = SensorModel(sensor_id="SH1", sensor_type="soil_humidity", cell_id=cell1.id)
    db_session.add_all([sensor_temp, sensor_hum, sensor_soil_hum])
    db_session.commit()

    analytic_temp = AnalyticModel(sensor_id=sensor_temp.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=25.5, sensor_code="T1")
    analytic_hum = AnalyticModel(sensor_id=sensor_hum.id, analytic_type=AnalyticType.AIR_HUMIDITY, value=60.0, sensor_code="H1")
    analytic_soil_hum = AnalyticModel(sensor_id=sensor_soil_hum.id, analytic_type=AnalyticType.SOIL_HUMIDITY, value=45.0, sensor_code="SH1")
    db_session.add_all([analytic_temp, analytic_hum, analytic_soil_hum])
    db_session.commit()

    # --- Exécution ---
    result_area = get_area_with_analytics(db_session, area1.id)

    # --- Vérification ---
    assert result_area is not None
    assert result_area.name == "Area 1"
    assert result_area.level == 1
    assert len(result_area.areas) == 0
    assert result_area.analytics is not None

    # Vérifier que la moyenne est correcte pour le jour où la donnée a été ajoutée
    today = datetime.now(UTC).date()
    
    # La valeur doit être présente dans la liste pour le bon type et le bon jour
    air_temp_avg = next((avg.value for avg in result_area.analytics[AnalyticType.AIR_TEMPERATURE] if avg.occurred_at.date() == today), None)
    air_hum_avg = next((avg.value for avg in result_area.analytics[AnalyticType.AIR_HUMIDITY] if avg.occurred_at.date() == today), None)
    soil_hum_avg = next((avg.value for avg in result_area.analytics[AnalyticType.SOIL_HUMIDITY] if avg.occurred_at.date() == today), None)

    assert air_temp_avg == 25.5
    assert air_hum_avg == 60.0
    assert soil_hum_avg == 45.0

def test_get_area_multi_level_aggregation(db_session):
    """
    Vérifie que les moyennes sont correctement agrégées depuis les sous-zones.
    """
    # --- Préparation ---
    now = datetime.now(UTC)

    # Zone Parent
    parent_area = AreaModel(name="Parent Area")
    db_session.add(parent_area)
    db_session.commit()
    cell_parent = CellModel(name="Cell Parent", area_id=parent_area.id)
    db_session.add(cell_parent)
    db_session.commit()
    sensor_parent = SensorModel(sensor_id="TP", sensor_type="temperature", cell_id=cell_parent.id)
    db_session.add(sensor_parent)
    db_session.commit()
    analytic_parent = AnalyticModel(sensor_id=sensor_parent.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=10.0, sensor_code="TP", occurred_at=now)
    db_session.add(analytic_parent)
    db_session.commit()

    # Zone Enfant
    child_area = AreaModel(name="Child Area", parent_id=parent_area.id)
    db_session.add(child_area)
    db_session.commit()
    cell_child = CellModel(name="Cell Child", area_id=child_area.id)
    db_session.add(cell_child)
    db_session.commit()
    sensor_child = SensorModel(sensor_id="TC", sensor_type="temperature", cell_id=cell_child.id)
    db_session.add(sensor_child)
    db_session.commit()
    analytic_child = AnalyticModel(sensor_id=sensor_child.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=30.0, sensor_code="TC", occurred_at=now)
    db_session.add(analytic_child)
    db_session.commit()

    # --- Exécution ---
    result_area = get_area_with_analytics(db_session, parent_area.id)

    # --- Vérification ---
    assert result_area is not None
    assert result_area.name == "Parent Area"
    assert result_area.level == 1
    assert len(result_area.areas) == 1
    
    # Vérifier la sous-zone
    result_child = result_area.areas[0]
    assert result_child.name == "Child Area"
    assert result_child.level == 2
    assert result_child.analytics is not None
    child_avg = next((avg.value for avg in result_child.analytics[AnalyticType.AIR_TEMPERATURE] if avg.occurred_at.date() == now.date()), None)
    assert child_avg == 30.0

    # Vérifier l'agrégation sur la zone parente
    assert result_area.analytics is not None
    parent_avg = next((avg.value for avg in result_area.analytics[AnalyticType.AIR_TEMPERATURE] if avg.occurred_at.date() == now.date()), None)
    assert parent_avg == (10.0 + 30.0) / 2  # Moyenne de 10 (parent) et 30 (enfant)


def test_get_area_uses_latest_analytic_only(db_session):
    """
    Vérifie que seule la dernière donnée analytique d'un capteur est utilisée pour le calcul.
    """
    # --- Préparation ---
    area1 = AreaModel(name="Area 1")
    db_session.add(area1)
    db_session.commit()
    cell1 = CellModel(name="Cell 1", area_id=area1.id)
    db_session.add(cell1)
    db_session.commit()
    sensor1 = SensorModel(sensor_id="T1", sensor_type="temperature", cell_id=cell1.id)
    db_session.add(sensor1)
    db_session.commit()

    # Données anciennes et récentes
    now = datetime.now(UTC)
    analytic_old = AnalyticModel(sensor_id=sensor1.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=10.0, occurred_at=now - timedelta(days=1), sensor_code="T1")
    analytic_new = AnalyticModel(sensor_id=sensor1.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=50.0, occurred_at=now, sensor_code="T1") # Cette donnée est pour aujourd'hui
    db_session.add_all([analytic_old, analytic_new])
    db_session.commit()

    # --- Exécution ---
    result_area = get_area_with_analytics(db_session, area1.id)

    # --- Vérification ---
    assert result_area is not None
    assert result_area.analytics is not None
    # La moyenne pour aujourd'hui doit être 50.0
    today_avg = next((avg.value for avg in result_area.analytics[AnalyticType.AIR_TEMPERATURE] if avg.occurred_at.date() == now.date()), None)
    assert today_avg == 50.0

# === Tests for update_area ===

def test_update_area_not_found(db_session, setup_user):
    """Vérifie qu'une AreaNotFoundError est levée si la zone à mettre à jour n'existe pas."""
    update_data = AreaUpdate(name="New Name")
    with pytest.raises(AreaNotFoundError):
        update_area(db_session, uuid.uuid4(), update_data, setup_user)

def test_update_area_name_and_color(db_session, setup_user):
    """Vérifie la mise à jour simple du nom et de la couleur."""
    area = AreaModel(name="Old Name", color="#000000")
    db_session.add(area)
    db_session.commit()

    update_data = AreaUpdate(name="New Name", color="#FFFFFF")
    updated_area_schema = update_area(db_session, area.id, update_data, setup_user)

    assert updated_area_schema.name == "New Name"
    assert updated_area_schema.color == "#FFFFFF"
    assert updated_area_schema.updater.id == setup_user.id

    db_session.refresh(area)
    assert area.name == "New Name"
    assert area.color == "#FFFFFF"
    assert area.updater_id == setup_user.id

def test_update_area_change_parent(db_session, setup_user):
    """Vérifie le changement de parent d'une zone."""
    root1 = AreaModel(name="Root 1")
    root2 = AreaModel(name="Root 2")
    db_session.add_all([root1, root2])
    db_session.commit()
    child = AreaModel(name="Child", parent_id=root1.id)
    db_session.add(child)
    db_session.commit()

    # Move child from root1 to root2
    update_data = AreaUpdate(parent_id=root2.id)
    updated_area_schema = update_area(db_session, child.id, update_data, setup_user)

    assert updated_area_schema.level == 2
    
    db_session.refresh(child)
    assert child.parent_id == root2.id

def test_update_area_move_to_root(db_session, setup_user):
    """Vérifie le déplacement d'une zone enfant vers la racine."""
    parent = AreaModel(name="Parent")
    db_session.add(parent)
    db_session.commit()
    child = AreaModel(name="Child", parent_id=parent.id)
    db_session.add(child)
    db_session.commit()

    # Move child to root by setting parent_id to None
    update_data = AreaUpdate(parent_id=None)
    updated_area_schema = update_area(db_session, child.id, update_data, setup_user)

    assert updated_area_schema.level == 1
    
    db_session.refresh(child)
    assert child.parent_id is None

def test_update_area_self_parent_error(db_session, setup_user):
    """Vérifie qu'une erreur est levée si une zone est définie comme son propre parent."""
    area = AreaModel(name="Area")
    db_session.add(area)
    db_session.commit()

    update_data = AreaUpdate(parent_id=area.id)
    with pytest.raises(ValueError, match="An area cannot be its own parent."):
        update_area(db_session, area.id, update_data, setup_user)

def test_update_area_cyclic_dependency_error(db_session, setup_user):
    """Vérifie qu'une erreur est levée si on déplace un parent dans son propre enfant."""
    parent = AreaModel(name="Parent")
    db_session.add(parent)
    db_session.commit()
    child = AreaModel(name="Child", parent_id=parent.id)
    db_session.add(child)
    db_session.commit()

    # Try to move parent into child
    update_data = AreaUpdate(parent_id=child.id)
    with pytest.raises(ValueError, match="Cannot move an area into one of its own descendants"):
        update_area(db_session, parent.id, update_data, setup_user)
