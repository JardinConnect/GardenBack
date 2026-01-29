import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from db.models import Base

# Utiliser une base de données SQLite en mémoire pour les tests
# 'check_same_thread' est nécessaire pour SQLite en mode multithread (ce que fait pytest)
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Fixture pour configurer la base de données une seule fois par session de test.
    Crée toutes les tables avant le début des tests et les supprime à la fin.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(setup_database) -> Session:
    """
    Fixture Pytest qui fournit une session de base de données pour chaque fonction de test.
    La session est encapsulée dans une transaction qui est annulée (rollback) après le test.
    Cela garantit une isolation parfaite et une vitesse d'exécution élevée.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()