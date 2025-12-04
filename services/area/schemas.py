from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class Cell(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class Area(BaseModel):
    name: str
    color: Optional[str] = None
    areas: List['Area'] = Field(default_factory=list)
    cells: List[Cell] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

# Permet à Pydantic de gérer les références circulaires (Area dans Area)
Area.model_rebuild()