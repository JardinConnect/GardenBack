from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import uuid

from db.database import get_db
from db.models import User, ResourceTypeEnum
from services.auth.dependencies import get_current_user
from .service import get_action_logs_paginated
from .schemas import ActionLogFilter, PaginatedActionLogResult


router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedActionLogResult,
    summary="Lister les logs d'actions (audit)",
)
def list_action_logs(
    user_id: Optional[uuid.UUID] = Query(None, description="Filtrer par utilisateur"),
    resource_type: Optional[str] = Query(None, description="Type de ressource (area, cell, user, alert, network)"),
    from_date: Optional[datetime] = Query(None, description="Date de début"),
    to_date: Optional[datetime] = Query(None, description="Date de fin"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedActionLogResult:
    rt_enum = None
    if resource_type is not None:
        try:
            rt_enum = ResourceTypeEnum(resource_type)
        except ValueError:
            rt_enum = None
    filters = ActionLogFilter(
        user_id=user_id,
        resource_type=rt_enum,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )
    return get_action_logs_paginated(db, filters)
