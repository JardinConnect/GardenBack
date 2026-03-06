from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional
import uuid
from datetime import datetime
from services.cell.schemas import Cell
from db.models import AnalyticType
from services.analytics.schemas import AnalyticSchema

class UserInfo(BaseModel):
    id: uuid.UUID
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class AreaCreate(BaseModel):
    name: str
    color: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    is_tracked: Optional[bool] = False

class AreaUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    is_tracked: Optional[bool] = None

class Area(BaseModel):
    id: uuid.UUID
    name: str
    color: Optional[str] = None
    is_tracked: bool
    level: int
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    originator: Optional[UserInfo] = Field(None, alias="createdBy")
    updater: Optional[UserInfo] = Field(None, alias="updatedBy")
    areas: List['Area'] = Field(default_factory=list)
    cells: List[Cell] = Field(default_factory=list)
    analytics: Dict[AnalyticType, List[AnalyticSchema]]


    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# Permet à Pydantic de gérer les références circulaires (Area dans Area)
Area.model_rebuild()