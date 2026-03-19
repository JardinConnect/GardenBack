import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, Analytic, AnalyticType, Area, Cell, Sensor, User, RefreshToken
from services.analytics.repository import get_analytics, validate_request, create_analytic, _collect_area_ids
from services.analytics.errors import InvalidDateRangeError, DataNotFoundError
from services.analytics.schemas import AnalyticsFilter, PaginatedAnalyticResult, AnalyticCreate, AnalyticSchema

@pytest.fixture(scope="function")
def setup_sensor(db_session):
    """Crée une hiérarchie Area -> Cell -> Sensor pour les tests."""
    test_area = Area(name="Test Area", color="#FFFFFF")
    db_session.add(test_area)
    db_session.commit()

    test_cell = Cell(name="Test Cell", area_id=test_area.id)
    db_session.add(test_cell)
    db_session.commit()

    test_sensor = Sensor(sensor_id="TEST-SENSOR-01", sensor_type="temperature", cell_id=test_cell.id)
    db_session.add(test_sensor)
    db_session.commit()

    return test_sensor


@pytest.fixture(scope="function")
def setup_area_hierarchy(db_session):
    """
    Crée une hiérarchie à 3 niveaux pour tester le filtre area récursif :
    Parcelle Nord
    ├── Planche Tomates
    │   └── Section Cerises  ← cellule + capteur ici
    └── Planche Salades      ← cellule + capteur ici
    """
    parcelle_nord = Area(name="Parcelle Nord", color="#2E8B57")
    db_session.add(parcelle_nord)
    db_session.commit()

    planche_tomates = Area(name="Planche Tomates", color="#FF6347", parent_id=parcelle_nord.id)
    planche_salades = Area(name="Planche Salades", color="#90EE90", parent_id=parcelle_nord.id)
    db_session.add_all([planche_tomates, planche_salades])
    db_session.commit()

    section_cerises = Area(name="Section Cerises", color="#FF4500", parent_id=planche_tomates.id)
    db_session.add(section_cerises)
    db_session.commit()

    # Cellule dans la sous-planche (niveau 3)
    cell_cerises = Cell(name="Rangée A Cerises", area_id=section_cerises.id)
    # Cellule dans la planche (niveau 2)
    cell_salades = Cell(name="Section Laitues", area_id=planche_salades.id)
    db_session.add_all([cell_cerises, cell_salades])
    db_session.commit()

    sensor_cerises = Sensor(sensor_id="TA-CERISES", sensor_type="air_temperature", cell_id=cell_cerises.id)
    sensor_salades = Sensor(sensor_id="TA-SALADES", sensor_type="air_temperature", cell_id=cell_salades.id)
    db_session.add_all([sensor_cerises, sensor_salades])
    db_session.commit()

    return {
        "parcelle_nord": parcelle_nord,
        "planche_tomates": planche_tomates,
        "planche_salades": planche_salades,
        "section_cerises": section_cerises,
        "cell_cerises": cell_cerises,
        "cell_salades": cell_salades,
        "sensor_cerises": sensor_cerises,
        "sensor_salades": sensor_salades,
    }


# =========================================================
# TESTS — validate_request
# =========================================================

def test_validate_request_invalid_range():
    """Vérifie qu'une plage de dates invalide lève une erreur."""
    start = datetime(2025, 1, 2)
    end = datetime(2025, 1, 1)
    with pytest.raises(InvalidDateRangeError):
        validate_request(start, end)


# =========================================================
# TESTS — get_analytics (existants)
# =========================================================

def test_get_analytics_no_data(db_session):
    """Aucune donnée ne doit renvoyer DataNotFoundError."""
    request = AnalyticsFilter(
        analytic_type=None,
        sensor_id=None,
        sensor_code=None,
        area_id=None,
        cell_id=None,
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 1, 2),
        skip=0,
        limit=10
    )
    with pytest.raises(DataNotFoundError):
        get_analytics(db_session, request)


def test_get_analytics_success(db_session, setup_sensor):
    """Cas nominal : retourne un résultat valide."""
    now = datetime.now()
    analytic = Analytic(
        sensor_code="TA-1",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=22.5,
        occurred_at=now,
        sensor_id=setup_sensor.id
    )
    db_session.add(analytic)
    db_session.commit()

    request = AnalyticsFilter(
        sensor_code="TA-1",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1),
        sensor_id=None,
        cell_id=None,
        area_id=None,
        skip=0,
        limit=10
    )

    result = get_analytics(db_session, request)

    assert isinstance(result, PaginatedAnalyticResult)
    assert result.total == 1
    assert AnalyticType.AIR_TEMPERATURE in result.data
    data = result.data[AnalyticType.AIR_TEMPERATURE][0]
    assert data.value == 22.5
    assert data.sensorCode == "TA-1"
    assert isinstance(data.occurred_at, datetime)


def test_get_analytics_filters_work(db_session, setup_sensor):
    """Teste les filtres sensor_id, sensor_code, analytic_type."""
    now = datetime.now()

    other_sensor = Sensor(sensor_id="OTHER-SENSOR", sensor_type="humidity", cell_id=setup_sensor.cell_id)
    db_session.add(other_sensor)
    db_session.commit()

    data = [
        Analytic(sensor_code="TA-1", analytic_type=AnalyticType.AIR_TEMPERATURE, value=21.7, occurred_at=now, sensor_id=setup_sensor.id),
        Analytic(sensor_code="HS-1", analytic_type=AnalyticType.SOIL_HUMIDITY, value=61.3, occurred_at=now, sensor_id=other_sensor.id),
    ]
    db_session.add_all(data)
    db_session.commit()

    request = AnalyticsFilter(
        sensor_code="HS-1",
        analytic_type=AnalyticType.SOIL_HUMIDITY,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
        sensor_id=other_sensor.id,
        cell_id=None,
        area_id=None,
        skip=0,
        limit=10
    )

    result = get_analytics(db_session, request)

    assert AnalyticType.SOIL_HUMIDITY in result.data
    assert len(result.data[AnalyticType.SOIL_HUMIDITY]) == 1
    analytic = result.data[AnalyticType.SOIL_HUMIDITY][0]
    assert analytic.value == 61.3
    assert analytic.sensorCode == "HS-1"


# =========================================================
# TESTS — _collect_area_ids
# =========================================================

def test_collect_area_ids_single_area(db_session, setup_area_hierarchy):
    """Une area sans enfants retourne uniquement son propre ID."""
    h = setup_area_hierarchy
    ids = _collect_area_ids(db_session, h["section_cerises"].id)

    assert ids == {h["section_cerises"].id}


def test_collect_area_ids_with_children(db_session, setup_area_hierarchy):
    """Une area avec des enfants directs retourne les deux IDs."""
    h = setup_area_hierarchy
    ids = _collect_area_ids(db_session, h["planche_tomates"].id)

    assert h["planche_tomates"].id in ids
    assert h["section_cerises"].id in ids
    assert len(ids) == 2


def test_collect_area_ids_recursive(db_session, setup_area_hierarchy):
    """La racine retourne tous les descendants (3 niveaux)."""
    h = setup_area_hierarchy
    ids = _collect_area_ids(db_session, h["parcelle_nord"].id)

    assert h["parcelle_nord"].id in ids
    assert h["planche_tomates"].id in ids
    assert h["planche_salades"].id in ids
    assert h["section_cerises"].id in ids
    assert len(ids) == 4


def test_collect_area_ids_unknown_id(db_session):
    """Un ID inexistant retourne un ensemble contenant uniquement cet ID."""
    import uuid
    unknown_id = uuid.uuid4()
    ids = _collect_area_ids(db_session, unknown_id)

    # L'ID est ajouté au set avant de chercher ses enfants — comportement attendu
    assert ids == {unknown_id}


# =========================================================
# TESTS — get_analytics avec area_id
# =========================================================

def test_get_analytics_filter_by_direct_area(db_session, setup_area_hierarchy):
    """Filtre sur une area directe retourne uniquement ses capteurs."""
    h = setup_area_hierarchy
    now = datetime.now()

    db_session.add(Analytic(
        sensor_code="TA-CERISES",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=24.0,
        occurred_at=now,
        sensor_id=h["sensor_cerises"].id,
    ))
    db_session.add(Analytic(
        sensor_code="TA-SALADES",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=19.0,
        occurred_at=now,
        sensor_id=h["sensor_salades"].id,
    ))
    db_session.commit()

    # Filtre sur section_cerises uniquement → ne doit pas retourner TA-SALADES
    request = AnalyticsFilter(
        area_id=h["section_cerises"].id,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1),
        sensor_id=None, sensor_code=None, analytic_type=None, cell_id=None,
        skip=0, limit=100
    )
    result = get_analytics(db_session, request)

    values = [a.value for a in result.data[AnalyticType.AIR_TEMPERATURE]]
    assert 24.0 in values
    assert 19.0 not in values


def test_get_analytics_filter_by_parent_area_is_recursive(db_session, setup_area_hierarchy):
    """Filtre sur la parcelle racine remonte toutes les données des sous-areas."""
    h = setup_area_hierarchy
    now = datetime.now()

    db_session.add(Analytic(
        sensor_code="TA-CERISES",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=24.0,
        occurred_at=now,
        sensor_id=h["sensor_cerises"].id,
    ))
    db_session.add(Analytic(
        sensor_code="TA-SALADES",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=19.0,
        occurred_at=now,
        sensor_id=h["sensor_salades"].id,
    ))
    db_session.commit()

    # Filtre sur parcelle_nord → doit retourner les deux capteurs
    request = AnalyticsFilter(
        area_id=h["parcelle_nord"].id,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1),
        sensor_id=None, sensor_code=None, analytic_type=None, cell_id=None,
        skip=0, limit=100
    )
    result = get_analytics(db_session, request)

    values = [a.value for a in result.data[AnalyticType.AIR_TEMPERATURE]]
    assert 24.0 in values
    assert 19.0 in values
    assert result.total == 2


def test_get_analytics_filter_by_cell_id(db_session, setup_area_hierarchy):
    """Filtre sur un cell_id retourne uniquement les données de cette cellule."""
    h = setup_area_hierarchy
    now = datetime.now()

    db_session.add(Analytic(
        sensor_code="TA-CERISES",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=24.0,
        occurred_at=now,
        sensor_id=h["sensor_cerises"].id,
    ))
    db_session.add(Analytic(
        sensor_code="TA-SALADES",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        value=19.0,
        occurred_at=now,
        sensor_id=h["sensor_salades"].id,
    ))
    db_session.commit()

    # Filtre sur cell_cerises uniquement
    request = AnalyticsFilter(
        cell_id=h["cell_cerises"].id,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1),
        skip=0,
        limit=100,
        analytic_type=None,
        sensor_id=None,
        sensor_code=None,
        area_id=None,
    )
    result = get_analytics(db_session, request)

    values = [a.value for a in result.data[AnalyticType.AIR_TEMPERATURE]]
    assert 24.0 in values
    assert 19.0 not in values
    assert result.total == 1

def test_get_analytics_area_id_no_data(db_session, setup_area_hierarchy):
    """Un area_id valide mais sans analytics lève DataNotFoundError."""
    h = setup_area_hierarchy
    now = datetime.now()

    request = AnalyticsFilter(
        area_id=h["parcelle_nord"].id,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1),
        sensor_id=None, sensor_code=None, analytic_type=None, cell_id=None,
        skip=0, limit=100
    )
    with pytest.raises(DataNotFoundError):
        get_analytics(db_session, request)


def test_get_analytics_pagination(db_session, setup_sensor):
    """La pagination skip/limit fonctionne correctement."""
    now = datetime.now()

    for i in range(5):
        db_session.add(Analytic(
            sensor_code="TA-1",
            analytic_type=AnalyticType.AIR_TEMPERATURE,
            value=float(20 + i),
            occurred_at=now - timedelta(minutes=i),
            sensor_id=setup_sensor.id,
        ))
    db_session.commit()

    # Page 1 : 3 éléments
    request_p1 = AnalyticsFilter(
        sensor_code="TA-1",
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1), sensor_id=None,
        analytic_type=None, area_id=None, cell_id=None,
        skip=0, limit=3
    )
    result_p1 = get_analytics(db_session, request_p1)
    assert result_p1.total == 5
    assert len(result_p1.data[AnalyticType.AIR_TEMPERATURE]) == 3

    # Page 2 : 2 éléments restants
    request_p2 = AnalyticsFilter(
        sensor_code="TA-1",
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1), sensor_id=None,
        analytic_type=None, area_id=None, cell_id=None,
        skip=3, limit=3
    )
    result_p2 = get_analytics(db_session, request_p2)
    assert result_p2.total == 5
    assert len(result_p2.data[AnalyticType.AIR_TEMPERATURE]) == 2


def test_get_analytics_no_limit(db_session, setup_sensor):
    """Vérifie que limit=None retourne tous les résultats."""
    now = datetime.now()

    # Ajouter plus de données qu'une limite habituelle
    for i in range(25):
        db_session.add(Analytic(
            sensor_code="TA-1",
            analytic_type=AnalyticType.AIR_TEMPERATURE,
            value=float(20 + i),
            occurred_at=now - timedelta(minutes=i),
            sensor_id=setup_sensor.id,
        ))
    db_session.commit()

    request = AnalyticsFilter(
        sensor_code="TA-1",
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1),
        sensor_id=None, analytic_type=None, area_id=None,
        skip=0,
        limit=None,  # Test avec aucune limite
        cell_id=None
    )
    result = get_analytics(db_session, request)
    assert result.total == 25
    assert len(result.data[AnalyticType.AIR_TEMPERATURE]) == 25


# =========================================================
# TESTS — create_analytic
# =========================================================

def test_create_analytic_success(db_session, setup_sensor):
    """Teste la création réussie d'une entrée analytique via le repository."""
    analytic_data = AnalyticCreate(
        sensor_code="TA-1",
        value=25.5,
        timestamp=datetime(2023, 10, 27, 10, 0, 0),
        sensor_id=setup_sensor.id
    )

    result_schema = create_analytic(db_session, analytic_data)

    assert isinstance(result_schema, AnalyticSchema)
    assert result_schema.value == 25.5
    assert result_schema.sensorCode == "TA-1"

    created_analytic = db_session.query(Analytic).filter_by(sensor_code="TA-1").one()
    assert created_analytic is not None
    assert created_analytic.value == 25.5
    assert created_analytic.analytic_type == AnalyticType.AIR_TEMPERATURE
    assert created_analytic.sensor_id == setup_sensor.id


def test_create_analytic_invalid_prefix(db_session, setup_sensor):
    """Teste qu'un préfixe invalide lève une ValueError."""
    analytic_data = AnalyticCreate(
        sensor_code="INVALID-1",
        value=30.0,
        timestamp=datetime(2023, 10, 27, 11, 0, 0),
        sensor_id=setup_sensor.id
    )
    with pytest.raises(ValueError, match="Préfixe de capteur invalide: INVALID"):
        create_analytic(db_session, analytic_data)