import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from services.user.repository import (
    check_user, get_user, get_users, create_user, delete_user, update_user
)

from services.user.errors import UserAlreadyExistsError, UserNotFoundErrorEmail, UserNotFoundErrorID
from services.user.schemas import UserLoginSchema, UserSchema, UserUpdate
from db.models import User


class TestUserService:
    """Test container pour le service utilisateur"""

    def setup_method(self):
        """Configuration avant chaque test"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query
        
        # Utilisateur de test
        self.test_user = User(
            id=1,
            first_name="test",
            last_name="user",
            phone_number="0102030405",
            email="test@example.com",
            password="hashed_password",
            isAdmin=False,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

    # Tests pour check_user
    def test_check_user_success(self):
        """Test de vérification d'utilisateur réussie"""
        # Arrange
        self.mock_query.filter.return_value.first.return_value = self.test_user
        login_data = UserLoginSchema(email="test@example.com", password="password")
        
        with patch('services.user.repository.verify_password', return_value=True):
            # Act
            result = check_user(self.mock_db, login_data)
            
            # Assert
            assert result is True
            self.mock_db.query.assert_called_once_with(User)

    def test_check_user_not_found(self):
        """Test utilisateur non trouvé lors de la vérification"""
        # Arrange
        self.mock_query.filter.return_value.first.return_value = None
        login_data = UserLoginSchema(email="nonexistent@example.com", password="password")
        
        # Act & Assert
        with pytest.raises(UserNotFoundErrorEmail) as exc_info:
            check_user(self.mock_db, login_data)
        
        assert "nonexistent@example.com" in str(exc_info.value)

    def test_check_user_wrong_password(self):
        """Test avec mot de passe incorrect"""
        # Arrange
        self.mock_query.filter.return_value.first.return_value = self.test_user
        login_data = UserLoginSchema(email="test@example.com", password="wrong_password")
        
        with patch('services.user.repository.verify_password', return_value=False):
            # Act
            result = check_user(self.mock_db, login_data)
            
            # Assert
            assert result is None

    # Tests pour get_user
    def test_get_user_success(self):
        """Test de récupération d'utilisateur réussie"""
        # Arrange
        self.mock_query.filter.return_value.first.return_value = self.test_user
        
        # Act
        result = get_user(self.mock_db, 1)
        
        # Assert
        assert result == self.test_user
        self.mock_db.query.assert_called_once_with(User)

    def test_get_user_not_found(self):
        """Test utilisateur non trouvé par ID"""
        # Arrange
        self.mock_query.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundErrorID) as exc_info:
            get_user(self.mock_db, 999)
        
        assert "999" in str(exc_info.value)

    # Tests pour get_users
    def test_get_users_default_params(self):
        """Test récupération de liste d'utilisateurs avec paramètres par défaut"""
        # Arrange
        users_list = [self.test_user]
        self.mock_query.offset.return_value.limit.return_value.all.return_value = users_list
        
        # Act
        result = get_users(self.mock_db)
        
        # Assert
        assert result == users_list
        self.mock_query.offset.assert_called_once_with(0)
        self.mock_query.offset.return_value.limit.assert_called_once_with(10)

    def test_get_users_custom_params(self):
        """Test récupération de liste avec paramètres personnalisés"""
        # Arrange
        users_list = [self.test_user]
        self.mock_query.offset.return_value.limit.return_value.all.return_value = users_list
        
        # Act
        result = get_users(self.mock_db, skip=5, limit=20)
        
        # Assert
        assert result == users_list
        self.mock_query.offset.assert_called_once_with(5)
        self.mock_query.offset.return_value.limit.assert_called_once_with(20)

    # Tests pour create_user
    @patch('services.user.repository.datetime')
    @patch('services.user.repository.get_password_hash')
    def test_create_user_success(self, mock_hash, mock_datetime):
        """Test de création d'utilisateur réussie"""
        # Arrange
        mock_datetime.now.return_value = datetime(2024, 1, 1)
        mock_hash.return_value = "hashed_password"
        self.mock_query.filter.return_value.first.return_value = None  # Pas d'utilisateur existant
        
        user_data = UserSchema(
            first_name="new",
            last_name="user",
            phone_number="0601020304",
            email="new@example.com",
            password="password123"
        )
        
        # Act
        result = create_user(self.mock_db, user_data)
        
        # Assert
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()
        mock_hash.assert_called_once_with("password123")

    def test_create_user_already_exists(self):
        """Test création d'utilisateur déjà existant"""
        # Arrange
        self.mock_query.filter.return_value.first.return_value = self.test_user
        
        user_data = UserSchema(
            first_name="test",
            last_name="user",
            email="test@example.com",
            password="password123"
        )
        
        # Act & Assert
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            create_user(self.mock_db, user_data)
        
        assert "test@example.com" in str(exc_info.value)
        self.mock_db.add.assert_not_called()

    # Tests pour delete_user
    def test_delete_user_success(self):
        """Test de suppression d'utilisateur réussie"""
        # Arrange
        self.mock_query.filter.return_value.first.return_value = self.test_user
        
        # Act
        result = delete_user(self.mock_db, 1)
        
        # Assert
        assert result is True
        self.mock_db.delete.assert_called_once_with(self.test_user)
        self.mock_db.commit.assert_called_once()

    def test_delete_user_not_found(self):
        """Test suppression d'utilisateur non trouvé"""
        # Arrange
        self.mock_query.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundErrorID) as exc_info:
            delete_user(self.mock_db, 999)
        
        assert "999" in str(exc_info.value)
        self.mock_db.delete.assert_not_called()

    # Tests pour update_user
    @patch('services.user.repository.datetime')
    def test_update_user_success(self, mock_datetime):
        """Test de mise à jour d'utilisateur réussie"""
        # Arrange
        now = datetime(2024, 2, 1)
        mock_datetime.now.return_value = now
        
        # On simule que get_user trouve bien l'utilisateur
        with patch('services.user.repository.get_user', return_value=self.test_user) as mock_get_user:
            update_data = UserUpdate(first_name="new_firstname", last_name="new_lastname")

            # Act
            result = update_user(self.mock_db, 1, update_data)

            # Assert
            mock_get_user.assert_called_once_with(self.mock_db, 1)
            assert result.first_name == "new_firstname"
            assert result.last_name == "new_lastname"
            assert result.updated_at == now
            self.mock_db.add.assert_called_once_with(self.test_user)
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(self.test_user)

    def test_update_user_not_found(self):
        """Test de mise à jour pour un utilisateur non trouvé"""
        # Arrange
        with patch('services.user.repository.get_user', side_effect=UserNotFoundErrorID(999)) as mock_get_user:
            update_data = UserUpdate(first_name="any_name")

            # Act & Assert
            with pytest.raises(UserNotFoundErrorID):
                update_user(self.mock_db, 999, update_data)
            mock_get_user.assert_called_once_with(self.mock_db, 999)

    # Tests d'intégration
    def test_user_workflow(self):
        """Test du flux complet utilisateur"""
        # Ce test simule un workflow complet
        with patch('services.user.repository.get_password_hash', return_value="hashed"):
            with patch('services.user.repository.verify_password', return_value=True):
                with patch('services.user.repository.datetime') as mock_dt:
                    mock_dt.now.return_value = datetime(2024, 1, 1)
                    
                    # 1. Créer un utilisateur
                    self.mock_query.filter.return_value.first.return_value = None
                    user_data = UserSchema(
                        first_name="workflow",
                        last_name="user",
                        email="workflow@example.com",
                        password="password123"
                    )
                    
                    create_user(self.mock_db, user_data)
                    
                    # 2. Vérifier l'utilisateur
                    self.mock_query.filter.return_value.first.return_value = self.test_user
                    login_data = UserLoginSchema(
                        email="workflow@example.com",
                        password="password123"
                    )
                    
                    check_result = check_user(self.mock_db, login_data)
                    assert check_result is True

    # Tests des cas limites
    def test_empty_users_list(self):
        """Test avec une liste vide d'utilisateurs"""
        # Arrange
        self.mock_query.offset.return_value.limit.return_value.all.return_value = []
        
        # Act
        result = get_users(self.mock_db)
        
        # Assert
        assert result == []

    def test_get_users_large_skip(self):
        """Test avec un skip important"""
        # Arrange
        self.mock_query.offset.return_value.limit.return_value.all.return_value = []
        
        # Act
        result = get_users(self.mock_db, skip=1000, limit=10)
        
        # Assert
        assert result == []
        self.mock_query.offset.assert_called_once_with(1000)