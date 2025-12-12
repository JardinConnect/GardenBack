import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, Analytic, AnalyticType, Area, Cell, Sensor, User, RefreshToken
from services.analytics.repository import get_analytics, validate_request, create_analytic
from services.analytics.errors import InvalidDateRangeError, DataNotFoundError
from services.analytics.schemas import AnalyticsFilter, PaginatedAnalyticResult, AnalyticCreate, AnalyticSchema


@pytest.fixture(scope="function")
def db_session():
    """Crée une base SQLite temporaire en mémoire pour les tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine) # Crée toutes les tables, y compris Area, Cell, Sensor
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    engine.dispose()

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


# === TESTS ===

def test_validate_request_invalid_range():
    """Vérifie qu'une plage de dates invalide lève une erreur."""
    start = datetime(2025, 1, 2)
    end = datetime(2025, 1, 1)
    with pytest.raises(InvalidDateRangeError):
        validate_request(start, end)


def test_get_analytics_no_data(db_session):
    """Aucune donnée ne doit renvoyer DataNotFoundError."""
    request = AnalyticsFilter(
        analytic_type=None,
        sensor_id=None,
        sensor_code=None,
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
        occured_at=now,
        sensor_id=setup_sensor.id
    )
    db_session.add(analytic)
    db_session.commit()

    request = AnalyticsFilter(
        sensor_code="TA-1", # Filtre par code
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1),
        sensor_id=None,
        skip=0,
        limit=10
    )

    result = get_analytics(db_session, request)

    # Vérifier que le type de retour est correct
    assert isinstance(result, PaginatedAnalyticResult)
    # Vérifier les métadonnées de pagination
    assert result.total == 1
    # Vérifier les données
    assert AnalyticType.AIR_TEMPERATURE in result.data
    data = result.data[AnalyticType.AIR_TEMPERATURE][0]
    assert data.value == 22.5
    assert data.sensorCode == "TA-1"
    assert isinstance(data.occured_at, datetime)


def test_get_analytics_filters_work(db_session, setup_sensor):
    """Teste les filtres sensor_id, sensor_code, analytic_type."""
    now = datetime.now()

    # Créer un deuxième capteur pour le test de filtre
    other_sensor = Sensor(sensor_id="OTHER-SENSOR", sensor_type="humidity", cell_id=setup_sensor.cell_id)
    db_session.add(other_sensor)
    db_session.commit()

    data = [
        Analytic(
            sensor_code="TA-1",
            analytic_type=AnalyticType.AIR_TEMPERATURE,
            value=21.7,
            occured_at=now,
            sensor_id=setup_sensor.id
        ),
        Analytic(
            sensor_code="HS-1",
            analytic_type=AnalyticType.SOIL_HUMIDITY,
            value=61.3,
            occured_at=now,
            sensor_id=other_sensor.id
        ),
    ]
    db_session.add_all(data)
    db_session.commit()

    request = AnalyticsFilter(
        sensor_code="HS-1", # Filtre par code
        analytic_type=AnalyticType.SOIL_HUMIDITY,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
        sensor_id=other_sensor.id, # Filtre par ID
        skip=0,
        limit=10
    )

    result = get_analytics(db_session, request)

    # On s'attend à un seul résultat
    assert AnalyticType.SOIL_HUMIDITY in result.data
    assert len(result.data[AnalyticType.SOIL_HUMIDITY]) == 1
    analytic = result.data[AnalyticType.SOIL_HUMIDITY][0]
    assert analytic.value == 61.3
    assert analytic.sensorCode == "HS-1"

# === TESTS pour create_analytic ===

def test_create_analytic_success(db_session, setup_sensor):
    """Teste la création réussie d'une entrée analytique via le repository."""
    analytic_data = AnalyticCreate(
        sensor_code="TA-1",
        value=25.5,
        timestamp=datetime(2023, 10, 27, 10, 0, 0),
        sensor_id=setup_sensor.id
    )
    
    result_schema = create_analytic(db_session, analytic_data)
    # Vérifie le retour de la fonction
    assert isinstance(result_schema, AnalyticSchema)
    assert result_schema.value == 25.5
    assert result_schema.sensorCode == "TA-1"

    # Vérifie que l'objet a bien été créé en base de données
    created_analytic = db_session.query(Analytic).filter_by(sensor_code="TA-1").one()
    assert created_analytic is not None
    assert created_analytic.value == 25.5
    assert created_analytic.analytic_type == AnalyticType.AIR_TEMPERATURE # L'enum, pas la string
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