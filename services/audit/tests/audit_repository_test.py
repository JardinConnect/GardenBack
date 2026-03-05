import uuid
from datetime import datetime, timedelta, UTC

from db.models import ActionLog
from services.audit.repository import (
    create_action_log,
    get_action_logs,
    delete_logs_older_than,
)


def test_create_action_log_nominal(db_session):
    user_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    log = create_action_log(
        db_session,
        user_id=user_id,
        action="create",
        resource_type="area",
        entity_id=entity_id,
        details={"name": "Zone A"},
    )
    assert log.id is not None
    assert log.user_id == user_id
    assert log.action == "create"
    assert log.resource_type == "area"
    assert log.entity_id == entity_id
    assert log.details == {"name": "Zone A"}
    assert log.created_at is not None
    assert log.created_at.tzinfo is not None


def test_create_action_log_user_id_null(db_session):
    log = create_action_log(
        db_session,
        user_id=None,
        action="create",
        resource_type="user",
        entity_id=None,
        details=None,
    )
    assert log.user_id is None
    assert log.entity_id is None
    assert log.details is None
    assert log.id is not None
    assert log.resource_type == "user"


def test_create_action_log_entity_id_and_details_null(db_session):
    user_id = uuid.uuid4()
    log = create_action_log(
        db_session,
        user_id=user_id,
        action="archive_all",
        resource_type="alert",
        entity_id=None,
        details=None,
    )
    assert log.entity_id is None
    assert log.details is None
    assert log.user_id == user_id


def test_get_action_logs_ordering(db_session):
    user_id = uuid.uuid4()
    base = datetime.now(UTC)
    for i in range(3):
        log = ActionLog(
            user_id=user_id,
            action="create",
            resource_type="area",
            entity_id=uuid.uuid4(),
            details=None,
            created_at=base - timedelta(minutes=i),
        )
        db_session.add(log)
    db_session.commit()

    rows, total = get_action_logs(db_session, skip=0, limit=10)
    assert total == 3
    assert len(rows) == 3
    assert rows[0].created_at >= rows[1].created_at >= rows[2].created_at


def test_get_action_logs_with_filters(db_session):
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    create_action_log(db_session, user_id=user_a, action="create", resource_type="area", entity_id=user_a)
    create_action_log(db_session, user_id=user_b, action="create", resource_type="cell", entity_id=user_b)
    create_action_log(db_session, user_id=user_a, action="delete", resource_type="area", entity_id=user_a)

    rows, total = get_action_logs(db_session, user_id=user_a)
    assert total == 2
    assert all(r.user_id == user_a for r in rows)

    rows, total = get_action_logs(db_session, resource_type="cell")
    assert total == 1
    assert rows[0].resource_type == "cell"


def test_get_action_logs_skip_exceeds_total(db_session):
    create_action_log(db_session, user_id=None, action="create", resource_type="area", entity_id=uuid.uuid4())
    rows, total = get_action_logs(db_session, skip=1000, limit=50)
    assert total == 1
    assert len(rows) == 0


def test_get_action_logs_limit_one(db_session):
    for _ in range(3):
        create_action_log(db_session, user_id=None, action="create", resource_type="area", entity_id=uuid.uuid4())
    rows, total = get_action_logs(db_session, skip=0, limit=1)
    assert total == 3
    assert len(rows) == 1


def test_get_action_logs_from_date_to_date(db_session):
    user_id = uuid.uuid4()
    base = datetime.now(UTC)
    old = base - timedelta(days=10)
    mid = base - timedelta(days=5)
    recent = base - timedelta(days=1)
    for t in (old, mid, recent):
        log = ActionLog(user_id=user_id, action="create", resource_type="area", entity_id=uuid.uuid4(), created_at=t)
        db_session.add(log)
    db_session.commit()

    from_date = base - timedelta(days=7)
    to_date = base - timedelta(days=2)
    rows, total = get_action_logs(db_session, from_date=from_date, to_date=to_date)
    assert total == 1
    assert rows[0].created_at == mid


def test_delete_logs_older_than_removes_only_old(db_session):
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=90)
    old_log = ActionLog(
        user_id=user_id,
        action="create",
        resource_type="area",
        entity_id=uuid.uuid4(),
        created_at=cutoff - timedelta(days=1),
    )
    recent_log = ActionLog(
        user_id=user_id,
        action="create",
        resource_type="area",
        entity_id=uuid.uuid4(),
        created_at=now - timedelta(days=1),
    )
    db_session.add_all([old_log, recent_log])
    db_session.commit()
    old_id = old_log.id
    recent_id = recent_log.id

    deleted = delete_logs_older_than(db_session, cutoff)
    assert deleted == 1

    assert db_session.query(ActionLog).filter(ActionLog.id == old_id).first() is None
    assert db_session.query(ActionLog).filter(ActionLog.id == recent_id).first() is not None


def test_delete_logs_older_than_none_to_delete(db_session):
    cutoff = datetime.now(UTC) + timedelta(days=1)
    deleted = delete_logs_older_than(db_session, cutoff)
    assert deleted == 0


def test_delete_logs_older_than_all_removed(db_session):
    user_id = uuid.uuid4()
    old_date = datetime.now(UTC) - timedelta(days=400)
    log = ActionLog(
        user_id=user_id,
        action="create",
        resource_type="area",
        entity_id=uuid.uuid4(),
        created_at=old_date,
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    log_id = log.id
    cutoff_past = datetime.now(UTC) - timedelta(days=365)
    deleted = delete_logs_older_than(db_session, cutoff_past)
    assert deleted >= 1
    assert db_session.query(ActionLog).filter(ActionLog.id == log_id).first() is None
