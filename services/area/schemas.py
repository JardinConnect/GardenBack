from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional

from db.models import AnalyticType
from services.analytics.schemas import AnalyticSchema


class Cell(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class AreaCreate(BaseModel):
    name: str
    color: Optional[str] = None
    parent_id: Optional[int] = Field(default=None, gt=0)

class Area(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    areas: List['Area'] = Field(default_factory=list)
    cells: Optional[List[Cell]] = None
    analytics: Dict[AnalyticType, List[AnalyticSchema]]


    model_config = ConfigDict(from_attributes=True)

# Permet à Pydantic de gérer les références circulaires (Area dans Area)
Area.model_rebuild()