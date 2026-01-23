import time
import pytest
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime
from datetime import timedelta, timezone
from services.user.schemas import UserResponse
from services.auth.auth import sign_jwt, decode_jwt, token_response, create_refresh_token
from db.models import User, RoleEnum as ModelRoleEnum, RefreshToken

# --- Setup des Mocks et des Constantes pour les Tests ---

# Simulez les variables d'environnement (JWT_ALGORITHM, JWT_SECRET)
@pytest.fixture(autouse=True)
def mock_config():
    """Simule la fonction config de python-decouple pour les tests."""
    with patch('services.auth.auth.config') as mock_conf:
        # Assurez-vous que ces valeurs correspondent à celles que PyJWT utilisera pour encoder/décoder
        mock_conf.return_value = 'HS256'  # Simulation de JWT_ALGORITHM
        mock_conf.side_effect = lambda key: 'test_secret' if key == 'JWT_SECRET' else 'HS256'
        yield mock_conf

# Objet UserSchema mocké pour les retours
@pytest.fixture
def mock_user_model():
    """Crée un objet User (modèle SQLAlchemy) concret mockant le retour du dépôt."""
    # Créer une instance concrète de User
    return User( # L'ID est maintenant un UUID
        id=uuid.uuid4(),
        first_name='Test',
        last_name='User',
        phone_number='1234567890',
        email='test@example.com',
        role=ModelRoleEnum.EMPLOYEES,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

# Session SQLAlchemy mockée
@pytest.fixture
def mock_db_session():
    """Crée une session SQLAlchemy mockée."""
    return MagicMock()

# --- Tests de la fonction `create_refresh_token` ---

@patch('services.auth.auth.uuid.uuid4')
@patch('services.auth.auth.datetime') # Patch datetime dans le module où il est utilisé
def test_create_refresh_token_success(mock_datetime_module, mock_uuid4, mock_db_session):
    """Vérifie que create_refresh_token crée, stocke et retourne un token valide."""
    # Arrange
    # Correct way to mock uuid.uuid4() so that str() on its return value works as expected
    mock_uuid_obj = MagicMock()
    mock_uuid_obj.__str__.return_value = "mock-uuid-token"
    mock_uuid4.return_value = mock_uuid_obj

    # Mock datetime.now(timezone.utc)
    mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_datetime_module.now.return_value = mock_now
    mock_datetime_module.timedelta = timedelta # Assure que timedelta fonctionne
    mock_datetime_module.timezone = timezone # Assure que timezone est disponible

    user_id = uuid.uuid4()

    # Act
    token = create_refresh_token(mock_db_session, user_id)

    # Assert
    assert token == "mock-uuid-token"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

    # Vérifie l'objet ajouté à la session
    added_refresh_token = mock_db_session.add.call_args[0][0]
    assert isinstance(added_refresh_token, RefreshToken)
    assert added_refresh_token.token == "mock-uuid-token"
    assert added_refresh_token.user_id == user_id
    assert added_refresh_token.expires_at == mock_now + timedelta(days=30)

# --- Tests de la fonction `token_response` ---

def test_token_response_returns_correct_dict(mock_user_model):
    """Vérifie que token_response retourne le dictionnaire attendu."""
    access_token = "a_dummy_access_token"
    refresh_token = "a_dummy_refresh_token"
    response = token_response(access_token, refresh_token, mock_user_model)
    
    assert isinstance(response, dict)
    assert "access_token" in response
    assert "refresh_token" in response
    assert "user" in response
    assert response["access_token"] == access_token
    assert response["refresh_token"] == refresh_token
    assert isinstance(response["user"], UserResponse)
    assert response["user"].email == mock_user_model.email


# --- Tests de la fonction `sign_jwt` ---

# mock de get_userByEmail car sign_jwt l'appelle
def test_sign_jwt_returns_valid_token_and_user(mock_db_session, mock_user_model):
    """Vérifie que sign_jwt encode un token et retourne la réponse complète."""
    user_email = "test@example.com"

    # L'objet utilisateur est maintenant passé directement.
    response = sign_jwt(mock_db_session, mock_user_model)

    # 2. Vérifie la structure de la réponse
    assert "access_token" in response
    assert "refresh_token" in response
    assert "user" in response
    assert response["user"].email == mock_user_model.email
    
    # 3. Vérifie que le token est une chaîne de caractères non vide
    token = response["access_token"]
    assert isinstance(token, str)
    assert len(token) > 10 # Un vrai token JWT est assez long

    # 4. Vérifie que le token peut être décodé (test implicite d'encodage)
    decoded = decode_jwt(token) 
    
    assert decoded is not None
    assert decoded["user_id"] == user_email
    assert decoded["role"] == mock_user_model.role.value
    # Vérifie que la date d'expiration est dans le futur (600 secondes)
    assert decoded["expires"] > time.time()
    # Vérifie que l'expiration est proche de l'expiration prévue (dans une marge de 10 secondes)
    assert decoded["expires"] < time.time() + 600 + 10


# --- Tests de la fonction `decode_jwt` ---

@patch('services.auth.auth.jwt.decode')
def test_decode_jwt_valid_token_returns_payload(mock_jwt_decode):
    """Vérifie que decode_jwt retourne le payload pour un token non expiré."""
    
    # Simule le temps actuel + 60s pour l'expiration (token valide)
    valid_payload = {
        "user_id": "test@example.com",
        "expires": time.time() + 60,
        "role": "employees"
    }
    # Le mock de jwt.decode doit retourner le payload valide
    mock_jwt_decode.return_value = valid_payload
    
    token = "dummy_valid_token"
    decoded = decode_jwt(token)

    # Vérifie que jwt.decode a été appelé correctement
    mock_jwt_decode.assert_called_once()
    
    # Vérifie le résultat
    assert decoded == valid_payload


@patch('services.auth.auth.jwt.decode')
def test_decode_jwt_expired_token_returns_none(mock_jwt_decode):
    """Vérifie que decode_jwt retourne None pour un token expiré."""
    
    # Simule le temps actuel - 60s pour l'expiration (token expiré)
    expired_payload = {
        "user_id": "test@example.com",
        "expires": time.time() - 60,
        "role": "employees"
    }
    mock_jwt_decode.return_value = expired_payload
    
    token = "dummy_expired_token"
    decoded = decode_jwt(token)

    # Vérifie le résultat: None est retourné lorsque le temps d'expiration est dépassé
    assert decoded is None


@patch('services.auth.auth.jwt.decode')
@patch('builtins.print') # Pour mocker l'appel à print dans le bloc except
def test_decode_jwt_invalid_token_returns_none(mock_print, mock_jwt_decode):
    """Vérifie que decode_jwt gère les erreurs de décodage (token invalide, secret erroné, etc.)."""
    
    # Simule une exception typique de PyJWT
    mock_jwt_decode.side_effect = Exception("Signature verification failed")
    
    token = "dummy_invalid_token"
    decoded = decode_jwt(token)

    # Vérifie le résultat: {} est retourné suite à l'exception
    assert decoded is None
    # Vérifie que l'erreur a été affichée (le print a été appelé)
    mock_print.assert_called_once() 
    assert "Erreur de décodage du token JWT" in mock_print.call_args[0][0]