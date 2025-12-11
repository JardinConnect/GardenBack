from datetime import datetime, timedelta, UTC

from db.models import Area as AreaModel, Cell as CellModel, Sensor as SensorModel, Analytic as AnalyticModel, AnalyticType
from services.area.service import get_area_with_analytics


def test_get_area_not_found(db_session):
    """
    Vérifie que la fonction retourne None si l'ID de la zone n'existe pas.
    """
    area = get_area_with_analytics(db_session, 999)
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
    db_session.add_all([sensor_temp, sensor_hum])
    db_session.commit()

    analytic_temp = AnalyticModel(sensor_id=sensor_temp.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=25.5, sensor_code="T1")
    analytic_hum = AnalyticModel(sensor_id=sensor_hum.id, analytic_type=AnalyticType.AIR_HUMIDITY, value=60.0, sensor_code="H1")
    db_session.add_all([analytic_temp, analytic_hum])
    db_session.commit()

    # --- Exécution ---
    result_area = get_area_with_analytics(db_session, area1.id)

    # --- Vérification ---
    assert result_area is not None
    assert result_area.name == "Area 1"
    assert len(result_area.areas) == 0
    assert result_area.analytics_average is not None
    assert result_area.analytics_average.temperature == 25.5
    assert result_area.analytics_average.humidity == 60.0
    assert result_area.analytics_average.light is None


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
    analytic_parent = AnalyticModel(sensor_id=sensor_parent.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=10.0, sensor_code="TP")
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
    analytic_child = AnalyticModel(sensor_id=sensor_child.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=30.0, sensor_code="TC")
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
    assert result_child.analytics_average is not None
    assert result_child.analytics_average.temperature == 30.0

    # Vérifier l'agrégation sur la zone parente
    assert result_area.analytics_average is not None
    assert result_area.analytics_average.temperature == (10.0 + 30.0) / 2  # Moyenne de 10 et 30


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
    analytic_old = AnalyticModel(sensor_id=sensor1.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=10.0, occured_at=now - timedelta(hours=1), sensor_code="T1")
    analytic_new = AnalyticModel(sensor_id=sensor1.id, analytic_type=AnalyticType.AIR_TEMPERATURE, value=50.0, occured_at=now, sensor_code="T1")
    db_session.add_all([analytic_old, analytic_new])
    db_session.commit()

    # --- Exécution ---
    result_area = get_area_with_analytics(db_session, area1.id)

    # --- Vérification ---
    assert result_area is not None
    assert result_area.analytics_average is not None
    # La moyenne doit être basée sur la dernière valeur (50.0), pas l'ancienne (10.0)
    assert result_area.analytics_average.temperature == 50.0
