import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base


@pytest.fixture(scope="function")
def db_session():
    """
    Fixture Pytest globale pour fournir une session de base de données SQLite 
    en mémoire pour chaque fonction de test.
    
    Cette fixture est définie au niveau racine et est donc disponible
    pour tous les tests du projet.
    """
    # Utilise une base de données en mémoire pour l'isolation des tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)