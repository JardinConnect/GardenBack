from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class Cell(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class AnalyticsAverage(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    light: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class Area(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    areas: List['Area'] = Field(default_factory=list)
    cells: List[Cell] = Field(default_factory=list)
    analytics_average: Optional[AnalyticsAverage] = None

    model_config = ConfigDict(from_attributes=True)

# Permet à Pydantic de gérer les références circulaires (Area dans Area)
Area.model_rebuild()