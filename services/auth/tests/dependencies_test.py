import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from services.auth.dependencies import get_current_user
from db.models import User, RoleEnum
import uuid

@pytest.fixture
def mock_db_session():
    """Crée une session SQLAlchemy mockée."""
    return MagicMock()

@pytest.fixture
def mock_user():
    """Crée un objet User mocké."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        role=RoleEnum.EMPLOYEES
    )

@patch('services.auth.dependencies.get_user_by_email')
def test_get_current_user_success(mock_get_user_by_email, mock_db_session, mock_user):
    """
    Teste que get_current_user retourne bien un utilisateur avec un payload valide.
    """
    # Arrange
    payload = {"user_id": "test@example.com"}
    mock_get_user_by_email.return_value = mock_user
    
    # Act
    # On appelle la fonction directement avec un payload, simulant ce que FastAPI ferait.
    user = get_current_user(db=mock_db_session, payload=payload)
    
    # Assert
    mock_get_user_by_email.assert_called_once_with(mock_db_session, email="test@example.com")
    assert user == mock_user

@patch('services.auth.dependencies.get_user_by_email')
def test_get_current_user_user_not_found(mock_get_user_by_email, mock_db_session):
    """
    Teste que get_current_user lève une HTTPException 404 si l'utilisateur du payload n'existe pas.
    """
    # Arrange
    payload = {"user_id": "ghost@example.com"}
    mock_get_user_by_email.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=mock_db_session, payload=payload)
    
    # L'implémentation actuelle lève un 404, ce qui est testé ici.
    # Un 401 serait aussi une option valide en production.
    assert exc_info.value.status_code == 404
    assert "Utilisateur non trouvé" in exc_info.value.detail
    mock_get_user_by_email.assert_called_once_with(mock_db_session, email="ghost@example.com")

def test_get_current_user_no_user_id_in_payload(mock_db_session):
    """
    Teste que get_current_user lève une HTTPException 401 si le payload ne contient pas de user_id.
    """
    # Arrange
    payload = {"role": "admin"} # Payload sans user_id
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=mock_db_session, payload=payload)
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Impossible de valider les informations d'identification."