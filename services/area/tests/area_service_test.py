import pytest
from datetime import datetime, timedelta, UTC
import uuid

from fastapi import HTTPException
from db.models import Area as AreaModel, Cell as CellModel, Sensor as SensorModel, Analytic as AnalyticModel, AnalyticType
from services.area.service import get_area_with_analytics, create_area, delete_area, _get_analytics_for_area, _calculate_daily_averages
from services.area.schemas import AreaCreate
from services.area.errors import ParentAreaNotFoundError, AreaNotFoundError


# === Tests for create_area ===

def test_create_area_as_root_success(db_session):
    """Vérifie la création réussie d'une zone racine."""
    # Arrange
    area_data = AreaCreate(name="Root Garden", color="#00FF00")

    # Act
    result = create_area(db_session, area_data)

    # Assert
    # Vérifier le schéma Pydantic retourné
    assert result.id is not None
    assert result.name == "Root Garden"
    assert result.color == "#00FF00"
    assert result.areas == []
    assert result.cells == []

    # Vérifier les données dans la base de données
    db_area = db_session.query(AreaModel).filter(AreaModel.id == result.id).first()
    assert db_area is not None
    assert db_area.name == "Root Garden"
    assert db_area.color == "#00FF00"
    assert db_area.parent_id is None
    assert db_area.level == 1

def test_create_area_as_child_success(db_session):
    """Vérifie la création réussie d'une zone enfant."""
    # Arrange
    parent_area = AreaModel(name="Parent Area", level=1)
    db_session.add(parent_area)
    db_session.commit()

    area_data = AreaCreate(name="Child Area", color="#FFA500", parent_id=parent_area.id)

    # Act
    result = create_area(db_session, area_data)

    # Assert
    # Vérifier les données dans la base de données
    db_area = db_session.query(AreaModel).filter(AreaModel.id == result.id).first()
    assert db_area is not None
    assert db_area.name == "Child Area"
    assert db_area.parent_id == parent_area.id
    assert db_area.level == 2

def test_create_area_with_nonexistent_parent_fails(db_session):
    """Vérifie qu'une erreur est levée si le parent n'existe pas."""
    # Arrange
    area_data = AreaCreate(name="Orphan Area", parent_id=uuid.uuid4())

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        create_area(db_session, area_data)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Parent area not found"

    # Vérifier qu'aucune zone n'a été ajoutée
    count = db_session.query(AreaModel).count()
    assert count == 0


# === Tests for delete_area ===

def test_delete_area_not_found(db_session):
    """Vérifie qu'une erreur est levée lors de la suppression d'une zone inexistante."""
    with pytest.raises(HTTPException) as exc_info:
        delete_area(db_session, uuid.uuid4())

    assert exc_info.value.status_code == AreaNotFoundError.status_code
    assert exc_info.value.detail == AreaNotFoundError.detail


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
    parent = AreaModel(name="Parent", level=1)
    db_session.add(parent)
    db_session.commit()

    child = AreaModel(name="Child", level=2, parent_id=parent.id)
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


# === Tests for Helper Functions (_get_analytics_for_area, _calculate_daily_averages) ===

def test_get_analytics_for_area_success(db_session):
    """Vérifie que la fonction récupère bien les analytiques des 7 derniers jours."""
    # Arrange
    area = AreaModel(name="Test Area")
    cell = CellModel(name="Test Cell", area=area)
    sensor = SensorModel(sensor_id="S1", sensor_type="temp", cell=cell)
    db_session.add_all([area, cell, sensor])
    db_session.commit()

    now = datetime.now(UTC)
    analytic_recent = AnalyticModel(sensor_id=sensor.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=25, occured_at=now - timedelta(days=1), sensor_code="S1")
    analytic_old = AnalyticModel(sensor_id=sensor.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=10, occured_at=now - timedelta(days=8), sensor_code="S1")
    db_session.add_all([analytic_recent, analytic_old])
    db_session.commit()

    # Act
    result = _get_analytics_for_area(db_session, area)

    # Assert
    assert len(result) == 1
    assert result[0].id == analytic_recent.id
    assert result[0].value == 25

def test_get_analytics_for_area_no_sensors(db_session):
    """Vérifie que la fonction retourne une liste vide si la zone n'a pas de capteurs."""
    # Arrange
    area = AreaModel(name="Empty Area")
    db_session.add(area)
    db_session.commit()

    # Act
    result = _get_analytics_for_area(db_session, area)

    # Assert
    assert result == []

def test_calculate_daily_averages_basic():
    """Vérifie le calcul de base des moyennes journalières."""
    # Arrange
    now = datetime.now(UTC)
    analytics = [
        AnalyticModel(analytic_type=AnalyticType.AIR_TEMPERATURE, value=20, occured_at=now),
        AnalyticModel(analytic_type=AnalyticType.AIR_TEMPERATURE, value=30, occured_at=now),
        AnalyticModel(analytic_type=AnalyticType.AIR_HUMIDITY, value=60, occured_at=now - timedelta(days=1)),
    ]

    # Act
    result = _calculate_daily_averages(analytics)

    # Assert
    assert AnalyticType.AIR_TEMPERATURE in result
    assert len(result[AnalyticType.AIR_TEMPERATURE]) == 7

    today_avg_temp = next((a.value for a in result[AnalyticType.AIR_TEMPERATURE] if a.occured_at.date() == now.date()), None)
    assert today_avg_temp == 25.0

    yesterday_avg_hum = next((a.value for a in result[AnalyticType.AIR_HUMIDITY] if a.occured_at.date() == (now - timedelta(days=1)).date()), None)
    assert yesterday_avg_hum == 60.0

    two_days_ago_avg_temp = next((a.value for a in result[AnalyticType.AIR_TEMPERATURE] if a.occured_at.date() == (now - timedelta(days=2)).date()), None)
    assert two_days_ago_avg_temp == 0.0

def test_calculate_daily_averages_empty_input():
    """Vérifie que la fonction gère une liste d'analytiques vide."""
    result = _calculate_daily_averages([])
    for analytic_type in AnalyticType:
        assert len(result[analytic_type]) == 7
        assert all(avg.value == 0.0 for avg in result[analytic_type])

def test_calculate_daily_averages_rounding():
    """Vérifie que les valeurs moyennes sont bien arrondies à 2 décimales."""
    now = datetime.now(UTC)
    analytics = [AnalyticModel(analytic_type=AnalyticType.LIGHT, value=v, occured_at=now) for v in [10, 15, 12]] # Moyenne = 12.333...

    result = _calculate_daily_averages(analytics)

    today_avg_light = next((a.value for a in result[AnalyticType.LIGHT] if a.occured_at.date() == now.date()), None)
    assert today_avg_light == 12.33

# === Tests for get_area_with_analytics ===

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
    assert len(result_area.areas) == 0
    assert result_area.analytics is not None

    # Vérifier que la moyenne est correcte pour le jour où la donnée a été ajoutée
    today = datetime.now(UTC).date()
    
    # La valeur doit être présente dans la liste pour le bon type et le bon jour
    air_temp_avg = next((avg.value for avg in result_area.analytics[AnalyticType.AIR_TEMPERATURE] if avg.occured_at.date() == today), None)
    air_hum_avg = next((avg.value for avg in result_area.analytics[AnalyticType.AIR_HUMIDITY] if avg.occured_at.date() == today), None)
    soil_hum_avg = next((avg.value for avg in result_area.analytics[AnalyticType.SOIL_HUMIDITY] if avg.occured_at.date() == today), None)

    assert air_temp_avg == 25.5
    assert air_hum_avg == 60.0
    assert soil_hum_avg == 45.0

def test_get_area_multi_level_aggregation(db_session):
    """
    Vérifie que les moyennes sont correctement agrégées depuis les sous-zones.
    """
    # --- Préparation ---
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
    now = datetime.now(UTC)
    analytic_parent = AnalyticModel(sensor_id=sensor_parent.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=10.0, sensor_code="TP", occured_at=now)
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
    analytic_child = AnalyticModel(sensor_id=sensor_child.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=30.0, sensor_code="TC", occured_at=now)
    db_session.add(analytic_child)
    db_session.commit()

    # --- Exécution ---
    result_area = get_area_with_analytics(db_session, parent_area.id)

    # --- Vérification ---
    assert result_area is not None
    assert result_area.name == "Parent Area"
    assert len(result_area.areas) == 1
    
    # Vérifier la sous-zone
    result_child = result_area.areas[0]
    assert result_child.name == "Child Area"
    assert result_child.analytics is not None
    child_avg = next((avg.value for avg in result_child.analytics[AnalyticType.AIR_TEMPERATURE] if avg.occured_at.date() == now.date()), None)
    assert child_avg == 30.0

    # Vérifier l'agrégation sur la zone parente
    assert result_area.analytics is not None
    parent_avg = next((avg.value for avg in result_area.analytics[AnalyticType.AIR_TEMPERATURE] if avg.occured_at.date() == now.date()), None)
    assert parent_avg == (10.0 + 30.0) / 2  # Moyenne de 10 et 30


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
    analytic_old = AnalyticModel(sensor_id=sensor1.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=10.0, occured_at=now - timedelta(days=1), sensor_code="T1")
    analytic_new = AnalyticModel(sensor_id=sensor1.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=50.0, occured_at=now, sensor_code="T1") # Cette donnée est pour aujourd'hui
    db_session.add_all([analytic_old, analytic_new])
    db_session.commit()

    # --- Exécution ---
    result_area = get_area_with_analytics(db_session, area1.id)

    # --- Vérification ---
    assert result_area is not None
    assert result_area.analytics is not None
    # La moyenne pour aujourd'hui doit être 50.0
    today_avg = next((avg.value for avg in result_area.analytics[AnalyticType.AIR_TEMPERATURE] if avg.occured_at.date() == now.date()), None)
    assert today_avg == 50.0
