import pytest


class TestGetCurrentNetworkSecurity:
    def test_returns_401_without_authorization_header(self, client):
        response = client.get("/network/current")
        assert response.status_code == 401

    def test_returns_401_with_invalid_token(self, client):
        response = client.get(
            "/network/current",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestGetListSecurity:
    def test_returns_401_without_authorization_header(self, client):
        response = client.get("/network/list")
        assert response.status_code == 401

    def test_returns_401_with_invalid_token(self, client):
        response = client.get(
            "/network/list",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestPostConnectSecurity:
    def test_returns_401_without_authorization_header(self, client):
        response = client.post(
            "/network/connect",
            json={"ssid": "TestNetwork"},
        )
        assert response.status_code == 401

    def test_returns_403_when_role_is_employees(self, client, headers_employees):
        response = client.post(
            "/network/connect",
            json={"ssid": "TestNetwork"},
            headers=headers_employees,
        )
        assert response.status_code == 403
        body = response.json()
        assert "administrateur" in body.get("error", {}).get("message", "").lower() or "admin" in body.get("error", {}).get("message", "").lower()

    def test_returns_403_when_role_is_trainee(self, client, db_session, mock_auth_config):
        from db.models import User, RoleEnum
        from services.auth.utils.security import get_password_hash
        from services.auth.auth import sign_jwt
        import uuid
        user = User(
            id=uuid.uuid4(),
            first_name="T",
            last_name="Trainee",
            email="trainee@test.com",
            password=get_password_hash("password"),
            role=RoleEnum.TRAINEE,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        result = sign_jwt(db_session, user)
        headers = {"Authorization": f"Bearer {result['access_token']}"}
        response = client.post(
            "/network/connect",
            json={"ssid": "TestNetwork"},
            headers=headers,
        )
        assert response.status_code == 403
