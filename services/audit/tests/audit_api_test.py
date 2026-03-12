import uuid

import pytest

from services.audit.repository import create_action_log


def test_list_action_logs_returns_200_with_admin(client, headers_admin, db_session):
    response = client.get("/api/action-logs/", headers=headers_admin)
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "data" in body
    assert "skip" in body
    assert "limit" in body
    assert body["limit"] >= 1 and body["limit"] <= 200


def test_list_action_logs_returns_200_with_superadmin(client, headers_superadmin):
    response = client.get("/api/action-logs/", headers=headers_superadmin)
    assert response.status_code == 200


def test_list_action_logs_returns_200_with_employees(client, headers_employees):
    response = client.get("/api/action-logs/", headers=headers_employees)
    assert response.status_code == 200
    body = response.json()
    assert "total" in body and "data" in body


def test_list_action_logs_returns_200_with_trainee(client, headers_trainee):
    response = client.get("/api/action-logs/", headers=headers_trainee)
    assert response.status_code == 200


def test_list_action_logs_returns_401_without_token(client):
    response = client.get("/api/action-logs/")
    assert response.status_code == 401


def test_list_action_logs_returns_401_invalid_token(client):
    response = client.get(
        "/api/action-logs/",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


def test_list_action_logs_response_structure(client, headers_admin, db_session):
    create_action_log(
        db_session,
        user_id=None,
        action="create",
        resource_type="area",
        entity_id=uuid.uuid4(),
        details={"name": "Zone"},
    )
    response = client.get("/api/action-logs/", headers=headers_admin)
    assert response.status_code == 200
    body = response.json()
    assert "total" in body and "data" in body and "skip" in body and "limit" in body
    if body["data"]:
        log = body["data"][0]
        assert "id" in log
        assert "user_id" in log
        assert "action" in log
        assert "resource_type" in log
        assert "entity_id" in log
        assert "details" in log
        assert "created_at" in log
        assert log.get("password") is None
        assert log.get("token") is None


def test_list_action_logs_filter_by_user_id(client, headers_admin, db_session, user_admin, user_employees):
    create_action_log(
        db_session,
        user_id=user_admin.id,
        action="create",
        resource_type="area",
        entity_id=uuid.uuid4(),
        details={},
    )
    create_action_log(
        db_session,
        user_id=user_employees.id,
        action="create",
        resource_type="cell",
        entity_id=uuid.uuid4(),
        details={},
    )
    response = client.get(
        f"/api/action-logs/?user_id={user_admin.id}",
        headers=headers_admin,
    )
    assert response.status_code == 200
    body = response.json()
    assert all(d["user_id"] == str(user_admin.id) for d in body["data"])


def test_list_action_logs_filter_by_resource_type(client, headers_admin, db_session):
    create_action_log(
        db_session,
        user_id=None,
        action="create",
        resource_type="alert",
        entity_id=uuid.uuid4(),
        details={},
    )
    response = client.get("/api/action-logs/?resource_type=alert", headers=headers_admin)
    assert response.status_code == 200
    body = response.json()
    assert all(d["resource_type"] == "alert" for d in body["data"])


def test_list_action_logs_pagination_skip_limit(client, headers_admin):
    response = client.get("/api/action-logs/?skip=0&limit=1", headers=headers_admin)
    assert response.status_code == 200
    body = response.json()
    assert body["skip"] == 0
    assert body["limit"] == 1
    assert len(body["data"]) <= 1


def test_list_action_logs_invalid_params_422(client, headers_admin):
    response = client.get("/api/action-logs/?skip=-1", headers=headers_admin)
    assert response.status_code == 422

    response = client.get("/api/action-logs/?limit=0", headers=headers_admin)
    assert response.status_code == 422

    response = client.get("/api/action-logs/?limit=201", headers=headers_admin)
    assert response.status_code == 422


def test_create_area_creates_one_audit_log(client, headers_admin, db_session):
    from db.models import ActionLog

    payload = {"name": "Zone Test Audit", "color": "#fff"}
    r = client.post("/api/area/", json=payload, headers=headers_admin)
    assert r.status_code == 201
    area_id = r.json()["id"]
    logs = (
        db_session.query(ActionLog)
        .filter(ActionLog.resource_type == "area", ActionLog.entity_id == uuid.UUID(area_id))
        .all()
    )
    assert len(logs) == 1
    assert logs[0].action == "create"


def test_401_does_not_reveal_system_info(client):
    response = client.get("/api/action-logs/")
    assert response.status_code == 401
    data = response.json()
    message = data.get("error", {}).get("message", data.get("detail", ""))
    assert "traceback" not in str(message).lower()
