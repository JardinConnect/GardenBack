import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from db.models import AnalyticType
from services.analytics.repository import get_analytics, validate_request
from services.analytics.errors import InvalidDateRangeError, DataNotFoundError
from services.analytics.schemas import AnalyticsFilter, AnalyticResult


# === Simulation du modèle Analytic ===
Base = declarative_base()

class Analytic(Base):
    __tablename__ = "analytics"
    id = Column(Integer, primary_key=True)
    node_id = Column(Integer)
    sensor_code = Column(String)
    analytic_type = Column(String)
    value = Column(Float)
    occured_at = Column(DateTime)



@pytest.fixture(scope="function")
def db_session(monkeypatch):
    """Crée une base SQLite temporaire en mémoire pour les tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Monkeypatch le modèle utilisé dans le repository (si nécessaire)
    import services.analytics.repository as repo
    repo.Analytic = Analytic
    repo.AnalyticType = AnalyticType

    yield session

    session.close()
    engine.dispose()


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
        node_id=None,
        sensor_code=None,
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 1, 2)
    )
    with pytest.raises(DataNotFoundError):
        get_analytics(db_session, request)


def test_get_analytics_success(db_session):
    """Cas nominal : retourne un résultat valide."""
    now = datetime.now()
    analytic = Analytic(
        node_id=1,
        sensor_code="AT-1",
        analytic_type=AnalyticType.AIR_TEMPERATURE.value,
        value=22.5,
        occured_at=now
    )
    db_session.add(analytic)
    db_session.commit()

    request = AnalyticsFilter(
        node_id=1,
        sensor_code="AT-1",
        analytic_type=AnalyticType.AIR_TEMPERATURE,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1),
    )

    result = get_analytics(db_session, request)

    assert isinstance(result, AnalyticResult)
    assert AnalyticType.AIR_TEMPERATURE in result.result
    data = result.result[AnalyticType.AIR_TEMPERATURE][0]
    assert data.value == 22.5
    assert data.sensorCode == "AT-1"
    assert isinstance(data.occured_at, datetime)


def test_get_analytics_filters_work(db_session):
    """Teste les filtres node_id, sensor_code, analytic_type."""
    now = datetime.now()
    data = [
        Analytic(
            node_id=1,
            sensor_code="AT-1",
            analytic_type=AnalyticType.AIR_TEMPERATURE.value,
            value=21.7,
            occured_at=now,
        ),
        Analytic(
            node_id=2,
            sensor_code="SH-1",
            analytic_type=AnalyticType.SOIL_HUMIDITY.value,
            value=61.3,
            occured_at=now,
        ),
    ]
    db_session.add_all(data)
    db_session.commit()

    request = AnalyticsFilter(
        node_id=2,
        sensor_code="SH-1",
        analytic_type=AnalyticType.SOIL_HUMIDITY,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
    )

    result = get_analytics(db_session, request)

    assert AnalyticType.SOIL_HUMIDITY in result.result
    assert len(result.result[AnalyticType.SOIL_HUMIDITY]) == 1
    analytic = result.result[AnalyticType.SOIL_HUMIDITY][0]
    assert analytic.value == 61.3
    assert analytic.sensorCode == "SH-1"
