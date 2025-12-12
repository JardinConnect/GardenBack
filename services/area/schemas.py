from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

from services.analytics.schemas import AnalyticSchema


class Cell(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class Area(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    areas: List['Area'] = Field(default_factory=list)
    cells: Optional[List[Cell]] = None
    analytics_average: Optional[List[AnalyticSchema]] = None

    model_config = ConfigDict(from_attributes=True)

# Permet à Pydantic de gérer les références circulaires (Area dans Area)
Area.model_rebuild()