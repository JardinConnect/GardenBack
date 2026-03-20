import uuid
from unittest.mock import Mock, patch

from db.models import User, ResourceTypeEnum
from services.audit.service import log_action, get_action_logs_paginated
from services.audit.schemas import ActionLogFilter


def test_log_action_calls_repository_with_user_id():
    db = Mock()
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    with patch("services.audit.service.repository.create_action_log") as create:
        log_action(db, user, "create", "area", entity_name="Zone A")
        create.assert_called_once()
        call_kw = create.call_args[1]
        assert call_kw["user_id"] == user.id
        assert call_kw["action"] == "create"
        assert call_kw["resource_type"] == "area"
        assert call_kw["details"] == {"entity_label": "Zone A"}


def test_log_action_stores_only_entity_label_in_details_json(db_session):
    """Le JSON en base ne contient qu'une chaîne lisible (plus de model_dump avec UUID)."""
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    log_action(
        db_session,
        user,
        "update",
        "area",
        entity_name="Parcelle nono",
    )
    from services.audit.repository import get_action_logs

    rows, total = get_action_logs(db_session, limit=1)
    assert total >= 1
    log = rows[0]
    assert log.details == {"entity_label": "Parcelle nono"}


def test_log_action_with_user_none():
    db = Mock()
    with patch("services.audit.service.repository.create_action_log") as create:
        log_action(db, None, "create", "user")
        create.assert_called_once()
        assert create.call_args[1]["user_id"] is None
        assert create.call_args[1]["details"] is None


def test_log_action_password_change_uses_label_not_secrets():
    db = Mock()
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    with patch("services.audit.service.repository.create_action_log") as create:
        log_action(
            db,
            user,
            "update",
            "user",
            entity_name="Jean Dupont",
            context="Mot de passe modifié",
        )
        create.assert_called_once()
        details = create.call_args[1]["details"]
        assert details == {"entity_label": "Jean Dupont — Mot de passe modifié"}
        assert "password" not in str(details)


def test_get_action_logs_paginated_nominal(db_session):
    from services.audit.repository import create_action_log

    user_id = uuid.uuid4()
    create_action_log(db_session, user_id=user_id, action="create", resource_type="area")
    create_action_log(db_session, user_id=user_id, action="delete", resource_type="cell")

    filters = ActionLogFilter(skip=0, limit=50)
    result = get_action_logs_paginated(db_session, filters)
    assert result.total >= 2
    assert len(result.data) >= 2
    assert result.skip == 0
    assert result.limit == 50
    assert result.data[0].id is not None
    assert result.data[0].action in ("create", "delete")
    assert result.data[0].resource_type in ("area", "cell")
    assert isinstance(result.data[0].entity_label, str)


def test_get_action_logs_paginated_filter_by_resource_type(db_session):
    from services.audit.repository import create_action_log

    user_id = uuid.uuid4()
    create_action_log(db_session, user_id=user_id, action="create", resource_type="area")
    create_action_log(db_session, user_id=user_id, action="create", resource_type="cell")

    filters = ActionLogFilter(skip=0, limit=50, resource_type=ResourceTypeEnum.AREA)
    result = get_action_logs_paginated(db_session, filters)
    assert all(d.resource_type == "area" for d in result.data)
    assert result.total >= 1


def test_get_action_logs_paginated_limit_200(db_session):
    filters = ActionLogFilter(skip=0, limit=200)
    result = get_action_logs_paginated(db_session, filters)
    assert result.limit == 200
    assert len(result.data) <= 200
