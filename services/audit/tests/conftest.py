import os
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_key_32_bytes_minimum!!")

import pytest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from db.database import get_db
from db.models import User, RoleEnum
from services.auth.utils.security import get_password_hash
from services.auth.auth import sign_jwt
from main import app


@pytest.fixture(autouse=True)
def mock_auth_config():
    with patch("services.auth.auth.config") as mock_config:
        mock_config.side_effect = lambda key: (
            "HS256" if key == "JWT_ALGORITHM" else "test_jwt_secret_key_32_bytes_minimum!!"
        )
        yield mock_config


@pytest.fixture
def user_employees(db_session):
    user = User(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="Employee",
        email="employee@test.com",
        password=get_password_hash("password"),
        role=RoleEnum.EMPLOYEES,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_trainee(db_session):
    user = User(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="Trainee",
        email="trainee@test.com",
        password=get_password_hash("password"),
        role=RoleEnum.TRAINEE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_admin(db_session):
    user = User(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="Admin",
        email="admin@test.com",
        password=get_password_hash("password"),
        role=RoleEnum.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_superadmin(db_session):
    user = User(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="Superadmin",
        email="superadmin@test.com",
        password=get_password_hash("password"),
        role=RoleEnum.SUPERADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def token_employees(db_session, user_employees, mock_auth_config):
    result = sign_jwt(db_session, user_employees)
    return result["access_token"]


@pytest.fixture
def token_trainee(db_session, user_trainee, mock_auth_config):
    result = sign_jwt(db_session, user_trainee)
    return result["access_token"]


@pytest.fixture
def token_admin(db_session, user_admin, mock_auth_config):
    result = sign_jwt(db_session, user_admin)
    return result["access_token"]


@pytest.fixture
def token_superadmin(db_session, user_superadmin, mock_auth_config):
    result = sign_jwt(db_session, user_superadmin)
    return result["access_token"]


@pytest.fixture
def headers_employees(token_employees):
    return {"Authorization": f"Bearer {token_employees}"}


@pytest.fixture
def headers_trainee(token_trainee):
    return {"Authorization": f"Bearer {token_trainee}"}


@pytest.fixture
def headers_admin(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture
def headers_superadmin(token_superadmin):
    return {"Authorization": f"Bearer {token_superadmin}"}


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("main.connect_mqtt"):
            with patch("services.audit.purge.create_purge_task", return_value=None):
                with TestClient(app) as c:
                    yield c
    finally:
        app.dependency_overrides.clear()
