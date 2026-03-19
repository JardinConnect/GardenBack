import pytest
from services.farm_state.service import get_farm_details, setup_farm
from db.models import (
    User, Area, Cell, Sensor, RoleEnum, Farm, Analytic, AnalyticType
)
from services.farm_state.schemas import OnboardingPayload, FarmCreate
from services.user.schemas import UserSchema
from services.area.schemas import AreaCreate
from services.farm_state.errors import FarmAlreadyExistsError
from services.user.errors import UserAlreadyExistsError as UserExistsError


def test_get_farm_details_empty_db(db_session):
    """
    Vérifie que get_farm_details retourne une structure vide mais correcte
    pour une base de données vide, sans les analytiques.
    """
    # Act
    details = get_farm_details(db_session, with_analytics=False)

    # Assert
    assert details.name == "JardinConnect"  # Fallback name
    assert details.summary.total_users == 0
    assert details.summary.total_areas == 0
    assert details.summary.total_cells == 0
    assert details.summary.total_sensors == 0
    assert details.summary.sensor_types == {}
    assert details.average_analytics is None


def test_get_farm_details_with_data_no_analytics(db_session):
    """
    Vérifie que get_farm_details retourne les bonnes informations
    quand la base est remplie, mais sans demander les analytiques.
    """
    # Arrange
    db_session.add(Farm(
        name="Ma Super Ferme",
        address="123 Rue de Test",
        zip_code="12345",
        city="Testville",
        phone_number="0123456789"))
    db_session.add(User(email="user@test.com", password="pwd", role=RoleEnum.EMPLOYEES, first_name="f", last_name="l"))
    area = Area(name="A1")
    db_session.add(area)
    db_session.commit()
    cell = Cell(name="C1", area_id=area.id)
    db_session.add(cell)
    db_session.commit()
    db_session.add(Sensor(sensor_id="T1", sensor_type="temperature", cell_id=cell.id))
    db_session.add(Sensor(sensor_id="T2", sensor_type="temperature", cell_id=cell.id))
    db_session.add(Sensor(sensor_id="H1", sensor_type="humidity", cell_id=cell.id))
    db_session.commit()

    # Act
    details = get_farm_details(db_session, with_analytics=False)

    # Assert
    assert details.name == "Ma Super Ferme"
    assert details.summary.total_users == 1
    assert details.summary.total_areas == 1
    assert details.summary.total_cells == 1
    assert details.summary.total_sensors == 3
    assert details.summary.sensor_types == {"temperature": 2, "humidity": 1}
    assert details.average_analytics is None


def test_get_farm_details_with_analytics(db_session):
    """
    Vérifie que get_farm_details retourne les bonnes informations
    y compris les moyennes des analytiques quand demandé.
    """
    # Arrange
    db_session.add(Farm(
        name="Ferme Analytique",
        address="123 Rue de Test",
        zip_code="12345",
        city="Testville",
        phone_number="0123456789"))
    cell = Cell(name="C1")
    db_session.add(cell)
    db_session.commit()
    sensor = Sensor(sensor_id="S1", sensor_type="multi", cell_id=cell.id)
    db_session.add(sensor)
    db_session.commit()
    analytics = [
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_TEMPERATURE, value=20.5),
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_TEMPERATURE, value=30.5), # Avg = 25.5
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.AIR_HUMIDITY, value=60),
    ]
    db_session.add_all(analytics)
    db_session.commit()

    # Act
    details = get_farm_details(db_session, with_analytics=True)

    # Assert
    assert details.name == "Ferme Analytique"
    assert details.summary.total_sensors == 1
    assert details.summary.sensor_types == {"multi": 1}
    
    assert details.average_analytics is not None
    assert len(details.average_analytics) == 2
    assert details.average_analytics["air_temperature"] == 25.5
    assert details.average_analytics["air_humidity"] == 60.0


def test_get_farm_details_with_analytics_rounding(db_session):
    """Vérifie que les moyennes des analytiques sont correctement arrondies."""
    # Arrange
    cell = Cell(name="C1")
    db_session.add(cell)
    db_session.commit()
    sensor = Sensor(sensor_id="S1", sensor_type="multi", cell_id=cell.id)
    db_session.add(sensor)
    db_session.commit()
    analytics = [
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.LIGHT, value=10),
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.LIGHT, value=15),
        Analytic(sensor_id=sensor.id, sensor_code="S1", analytic_type=AnalyticType.LIGHT, value=12), # Avg = 12.333...
    ]
    db_session.add_all(analytics)
    db_session.commit()

    # Act
    details = get_farm_details(db_session, with_analytics=True)

    # Assert
    assert details.average_analytics is not None
    assert details.average_analytics["light"] == 12.33


class TestSetupFarm:
    def test_setup_farm_success(self, db_session):
        """
        Vérifie que la configuration initiale crée la ferme, l'utilisateur SUPERADMIN et les zones.
        """
        # Arrange
        payload = OnboardingPayload(
            farm=FarmCreate(
                name="Ma Nouvelle Ferme",
                address="123 Rue de la Ferme",
                zip_code="44000",
                city="Nanoed",
                phone_number="0123456789"
                ),
            user=UserSchema(
                first_name="Super",
                last_name="Admin",
                email="super@newfarm.com",
                password="securepassword123",
                role=RoleEnum.EMPLOYEES,  # Le service doit forcer SUPERADMIN
            ),
            areas=[
                AreaCreate(name="Serre Principale"),
                AreaCreate(name="Champ Ouest"),
            ],
        )

        # Act
        result = setup_farm(db_session, payload)

        # Assert
        assert result == {"message": "Ferme configurée avec succès."}

        # Vérifier la ferme
        farm = db_session.query(Farm).one()
        assert farm.name == "Ma Nouvelle Ferme"

        # Vérifier l'utilisateur
        user = db_session.query(User).one()
        assert user.email == "super@newfarm.com"
        assert user.role == RoleEnum.SUPERADMIN  # Vérifier que le rôle a été forcé

        # Vérifier les zones
        areas = db_session.query(Area).all()
        assert len(areas) == 2
        area_names = {area.name for area in areas}
        assert "Serre Principale" in area_names
        assert "Champ Ouest" in area_names
        for area in areas:
            assert area.parent_id is None  # Doivent être des zones racines

    def test_setup_farm_fails_if_farm_already_exists(self, db_session):
        """
        Vérifie que setup_farm lève une FarmAlreadyExistsError si une ferme existe déjà.
        """
        # Arrange
        db_session.add(Farm(
            name="Ferme Existante",
            address="123 Rue de Test",
            zip_code="12345",
            city="Testville",
            phone_number="0123456789"))
        db_session.commit()

        payload = OnboardingPayload(
            farm=FarmCreate(
                name="Une autre ferme",
                address="123 Rue de la Ferme",
                zip_code="44000",
                city="Nanoed",
                phone_number="0123456789"
                ),
            user=UserSchema(first_name="a", last_name="b", email="c@d.com", password="password123", role=RoleEnum.ADMIN),
            areas=[],
        )

        # Act & Assert
        with pytest.raises(FarmAlreadyExistsError):
            setup_farm(db_session, payload)

    def test_setup_farm_fails_if_user_already_exists(self, db_session):
        """
        Vérifie que setup_farm propage UserExistsError si l'email de l'utilisateur existe déjà.
        """
        # Arrange
        db_session.add(User(email="super@newfarm.com", password="pwd", first_name="f", last_name="l"))
        db_session.commit()

        payload = OnboardingPayload(
            farm=FarmCreate(
                name="Ma Nouvelle Ferme",
                address="123 Rue de la Ferme",
                zip_code="44000",
                city="Nanoed",
                phone_number="0123456789"
                ),
            user=UserSchema(first_name="Super", last_name="Admin", email="super@newfarm.com", password="password123", role=RoleEnum.EMPLOYEES),
            areas=[],
        )

        # Act & Assert
        with pytest.raises(UserExistsError):
            setup_farm(db_session, payload)

        # Vérifier qu'aucune ferme n'a été créée dans ce cas
        assert db_session.query(Farm).count() == 0