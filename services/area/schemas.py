from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class Cell(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class AnalyticsAverage(BaseModel):
    air_temperature: Optional[float] = None
    soil_temperature: Optional[float] = None
    air_humidity: Optional[float] = None
    soil_humidity: Optional[float] = None
    light: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class Area(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    areas: List['Area'] = Field(default_factory=list)
    cells: Optional[List[Cell]] = None
    analytics_average: Optional[AnalyticsAverage] = None

    model_config = ConfigDict(from_attributes=True)

# Permet à Pydantic de gérer les références circulaires (Area dans Area)
Area.model_rebuild()