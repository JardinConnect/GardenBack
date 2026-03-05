from datetime import datetime
from typing import Optional, List
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.models import ActionLog


def create_action_log(
    db: Session,
    *,
    user_id: Optional[uuid.UUID] = None,
    action: str,
    resource_type: str,
    entity_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None,
) -> ActionLog:
    log = ActionLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_action_logs(
    db: Session,
    *,
    user_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[List[ActionLog], int]:
    query = db.query(ActionLog)
    filters = []
    if user_id is not None:
        filters.append(ActionLog.user_id == user_id)
    if resource_type is not None:
        filters.append(ActionLog.resource_type == resource_type)
    if from_date is not None:
        filters.append(ActionLog.created_at >= from_date)
    if to_date is not None:
        filters.append(ActionLog.created_at <= to_date)
    if filters:
        query = query.filter(and_(*filters))

    total = query.count()
    rows = (
        query.order_by(ActionLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return rows, total


def delete_logs_older_than(db: Session, cutoff_date: datetime) -> int:
    deleted = db.query(ActionLog).filter(ActionLog.created_at < cutoff_date).delete(synchronize_session=False)
    db.commit()
    return deleted
