import uuid
from datetime import datetime, UTC
from unittest.mock import Mock, patch

import pytest

from db.models import User, ResourceTypeEnum
from services.audit.service import log_action, get_action_logs_paginated
from services.audit.schemas import ActionLogFilter


def test_log_action_calls_repository_with_user_id():
    db = Mock()
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    entity_id = uuid.uuid4()
    with patch("services.audit.service.repository.create_action_log") as create:
        log_action(db, user, "create", "area", entity_id=entity_id, details={"name": "Zone A"})
        create.assert_called_once()
        call_kw = create.call_args[1]
        assert call_kw["user_id"] == user.id
        assert call_kw["action"] == "create"
        assert call_kw["resource_type"] == "area"
        assert call_kw["entity_id"] == entity_id
        assert call_kw["details"] == {"name": "Zone A"}


def test_log_action_with_user_none():
    db = Mock()
    with patch("services.audit.service.repository.create_action_log") as create:
        log_action(db, None, "create", "user", entity_id=None, details=None)
        create.assert_called_once()
        assert create.call_args[1]["user_id"] is None
        assert create.call_args[1]["entity_id"] is None
        assert create.call_args[1]["details"] is None


def test_log_action_does_not_pass_password_in_details():
    db = Mock()
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    with patch("services.audit.service.repository.create_action_log") as create:
        log_action(
            db,
            user,
            "update",
            "user",
            entity_id=user.id,
            details={"field": "password"},
        )
        create.assert_called_once()
        details = create.call_args[1]["details"]
        assert "password" not in details or details.get("password") is None
        assert details.get("field") == "password"


def test_get_action_logs_paginated_nominal(db_session):
    from services.audit.repository import create_action_log

    user_id = uuid.uuid4()
    create_action_log(db_session, user_id=user_id, action="create", resource_type="area", entity_id=uuid.uuid4())
    create_action_log(db_session, user_id=user_id, action="delete", resource_type="cell", entity_id=uuid.uuid4())

    filters = ActionLogFilter(skip=0, limit=50)
    result = get_action_logs_paginated(db_session, filters)
    assert result.total >= 2
    assert len(result.data) >= 2
    assert result.skip == 0
    assert result.limit == 50
    assert result.data[0].id is not None
    assert result.data[0].action in ("create", "delete")
    assert result.data[0].resource_type in ("area", "cell")


def test_get_action_logs_paginated_filter_by_resource_type(db_session):
    from services.audit.repository import create_action_log

    user_id = uuid.uuid4()
    create_action_log(db_session, user_id=user_id, action="create", resource_type="area", entity_id=uuid.uuid4())
    create_action_log(db_session, user_id=user_id, action="create", resource_type="cell", entity_id=uuid.uuid4())

    filters = ActionLogFilter(skip=0, limit=50, resource_type=ResourceTypeEnum.AREA)
    result = get_action_logs_paginated(db_session, filters)
    assert all(d.resource_type == "area" for d in result.data)
    assert result.total >= 1


def test_get_action_logs_paginated_limit_200(db_session):
    filters = ActionLogFilter(skip=0, limit=200)
    result = get_action_logs_paginated(db_session, filters)
    assert result.limit == 200
    assert len(result.data) <= 200
