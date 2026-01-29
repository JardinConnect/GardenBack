from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional
import uuid

from db.models import AnalyticType
from services.analytics.schemas import AnalyticSchema


class Cell(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class AreaCreate(BaseModel):
    name: str
    color: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None

class AreaUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None

class Area(BaseModel):
    id: uuid.UUID
    name: str
    color: Optional[str] = None
    level: int
    areas: List['Area'] = Field(default_factory=list)
    cells: List[Cell] = Field(default_factory=list)
    analytics: Dict[AnalyticType, List[AnalyticSchema]]


    model_config = ConfigDict(from_attributes=True)

# Permet à Pydantic de gérer les références circulaires (Area dans Area)
Area.model_rebuild()