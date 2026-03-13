from datetime import datetime
from typing import Optional, List, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict

from db.models import ResourceTypeEnum


class ActionLogResponse(BaseModel):
    id: uuid.UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    action: str
    resource_type: str
    entity_id: Optional[uuid.UUID] = None
    details: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionLogFilter(BaseModel):
    user_id: Optional[uuid.UUID] = Field(None, description="Filtrer par utilisateur")
    resource_type: Optional[ResourceTypeEnum] = Field(None, description="Filtrer par type de ressource")
    from_date: Optional[datetime] = Field(None, description="Date de début (inclus)")
    to_date: Optional[datetime] = Field(None, description="Date de fin (inclus)")
    skip: int = Field(0, ge=0, description="Nombre d'éléments à sauter")
    limit: int = Field(50, ge=1, le=200, description="Nombre maximum d'éléments")


class PaginatedActionLogResult(BaseModel):
    total: int
    skip: int
    limit: int
    data: List[ActionLogResponse]
