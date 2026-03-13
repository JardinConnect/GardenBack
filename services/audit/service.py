from typing import Optional, Any
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from db.models import User
from . import repository
from .schemas import ActionLogResponse, ActionLogFilter, PaginatedActionLogResult


def _make_details_json_serializable(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _make_details_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_details_json_serializable(v) for v in obj]
    return obj


def log_action(
    db: Session,
    user: Optional[User],
    action: str,
    resource_type: str,
    entity_id: Optional[uuid.UUID] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    user_id = user.id if user else None
    details_safe = _make_details_json_serializable(details) if details else None
    repository.create_action_log(
        db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        entity_id=entity_id,
        details=details_safe,
    )


def _row_to_action_log_response(row) -> "ActionLogResponse":
    first_name = row.user.first_name if row.user else None
    last_name = row.user.last_name if row.user else None
    return ActionLogResponse(
        id=row.id,
        first_name=first_name,
        last_name=last_name,
        action=row.action,
        resource_type=row.resource_type,
        entity_id=row.entity_id,
        details=row.details,
        created_at=row.created_at,
    )


def get_action_logs_paginated(
    db: Session,
    filters: ActionLogFilter,
) -> PaginatedActionLogResult:
    resource_type_str = filters.resource_type.value if filters.resource_type else None
    rows, total = repository.get_action_logs(
        db,
        user_id=filters.user_id,
        resource_type=resource_type_str,
        from_date=filters.from_date,
        to_date=filters.to_date,
        skip=filters.skip,
        limit=filters.limit,
    )
    return PaginatedActionLogResult(
        total=total,
        skip=filters.skip,
        limit=filters.limit,
        data=[_row_to_action_log_response(row) for row in rows],
    )
