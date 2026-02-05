import uuid
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, List
from datetime import datetime
from db.models import AnalyticType
from services.analytics.schemas import AnalyticSchema


# =========================================================
# SENSOR SCHEMAS
# =========================================================
class Sensor(BaseModel):
    id: uuid.UUID
    sensor_id: str
    sensor_type: str
    status: Optional[str] = None
    cell_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# =========================================================
# CELL SCHEMAS - Internal (Full Model)
# =========================================================
class Cell(BaseModel):
    """Schéma interne avec toutes les relations de la base de données."""
    id: uuid.UUID
    name: str
    area_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    is_tracked: bool
    sensors: List[Sensor] = Field(default_factory=list)
    analytics: Dict[AnalyticType, List[AnalyticSchema]] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True)


# =========================================================
# CELL DTO - API Response (What frontend sees)
# =========================================================
class CellDTO(BaseModel):
    """Schéma exposé au frontend avec les informations essentielles."""
    id: uuid.UUID
    name: str
    parent_id: Optional[uuid.UUID] = None
    updated_at: datetime
    is_tracked: bool
    analytics: Dict[AnalyticType, List[AnalyticSchema]] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_cell(cls, cell: Cell) -> "CellDTO":
        """Convertit un Cell interne en CellDTO pour l'API."""
        return cls(
            id=cell.id,
            name=cell.name,
            parent_id=cell.area_id,
            updated_at=cell.updated_at,
            is_tracked=cell.is_tracked,
            analytics=cell.analytics
        )


# =========================================================
# CELL REQUEST SCHEMAS
# =========================================================
class CellCreate(BaseModel):
    """Schéma pour créer une nouvelle cellule."""
    name: str = Field(..., min_length=1, description="Nom de la cellule")
    area_id: Optional[uuid.UUID] = Field(default=None, description="ID de la zone parente")


class CellUpdate(BaseModel):
    """Schéma pour mettre à jour une cellule."""
    name: Optional[str] = Field(None, min_length=1, description="Nom de la cellule")
    area_id: Optional[uuid.UUID] = Field(None, description="ID de la zone parente")
    is_tracked: Optional[bool] = Field(None, description="Si la cellule est suivie")
    model_config = ConfigDict(from_attributes=True)
