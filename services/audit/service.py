from typing import Optional, Any
import uuid
from sqlalchemy.orm import Session

from db.models import User
from . import repository
from .schemas import ActionLogResponse, ActionLogFilter, PaginatedActionLogResult


def log_action(
    db: Session,
    user: Optional[User],
    action: str,
    resource_type: str,
    entity_id: Optional[uuid.UUID] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    user_id = user.id if user else None
    repository.create_action_log(
        db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        entity_id=entity_id,
        details=details,
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
        data=[ActionLogResponse.model_validate(row) for row in rows],
    )
