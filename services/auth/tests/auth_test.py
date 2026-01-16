import time
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from services.user.schemas import UserResponse, RoleNameEnum
from services.auth.auth import sign_jwt, decode_jwt, token_response 
from services.user.repository import get_userByEmail

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
def mock_user_schema():
    """Crée un objet UserResponse concret mockant le retour du dépôt."""
    # Créer une instance concrète de UserResponse
    return UserResponse(
        id=1,
        first_name='Test',
        last_name='User',
        phone_number='1234567890',
        email='test@example.com',
        role=RoleNameEnum.EMPLOYEES,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

# Session SQLAlchemy mockée
@pytest.fixture
def mock_db_session():
    """Crée une session SQLAlchemy mockée."""
    return MagicMock()

# --- Tests de la fonction `token_response` ---

def test_token_response_returns_correct_dict(mock_user_schema):
    """Vérifie que token_response retourne le dictionnaire attendu."""
    token = "a_dummy_token"
    response = token_response(token, mock_user_schema)
    
    assert isinstance(response, dict)
    assert "access_token" in response
    assert "user" in response
    assert response["access_token"] == token
    assert response["user"] == mock_user_schema


# --- Tests de la fonction `sign_jwt` ---

# mock de get_userByEmail car sign_jwt l'appelle
@patch('services.auth.auth.get_userByEmail')
def test_sign_jwt_returns_valid_token_and_user(mock_get_userByEmail, mock_user_schema, mock_db_session):
    """Vérifie que sign_jwt encode un token et retourne la réponse complète."""
    user_email = "test@example.com"
    mock_get_userByEmail.return_value = mock_user_schema

    response = sign_jwt(user_email, mock_db_session)

    # 1. Vérifie que le dépôt a été appelé correctement
    mock_get_userByEmail.assert_called_once_with(mock_db_session, user_email)

    # 2. Vérifie la structure de la réponse
    assert "access_token" in response
    assert "user" in response
    assert response["user"] == mock_user_schema
    
    # 3. Vérifie que le token est une chaîne de caractères non vide
    token = response["access_token"]
    assert isinstance(token, str)
    assert len(token) > 10 # Un vrai token JWT est assez long

    # 4. Vérifie que le token peut être décodé (test implicite d'encodage)
    decoded = decode_jwt(token) 
    
    assert decoded is not None
    assert decoded["user_id"] == user_email
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
        "expires": time.time() + 60 
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
        "expires": time.time() - 60 
    }
    mock_jwt_decode.return_value = expired_payload
    
    token = "dummy_expired_token"
    decoded = decode_jwt(token)

    # Vérifie le résultat: None est retourné lorsque le temps d'expiration est dépassé
    assert decoded is None


@patch('services.auth.auth.jwt.decode')
@patch('builtins.print') # Pour mocker l'appel à print dans le bloc except
def test_decode_jwt_invalid_token_returns_empty_dict(mock_print, mock_jwt_decode):
    """Vérifie que decode_jwt gère les erreurs de décodage (token invalide, secret erroné, etc.)."""
    
    # Simule une exception typique de PyJWT
    mock_jwt_decode.side_effect = Exception("Signature verification failed")
    
    token = "dummy_invalid_token"
    decoded = decode_jwt(token)

    # Vérifie le résultat: {} est retourné suite à l'exception
    assert decoded == {}
    # Vérifie que l'erreur a été affichée (le print a été appelé)
    mock_print.assert_called_once() 
    assert "Erreur de décodage du token JWT" in mock_print.call_args[0][0]