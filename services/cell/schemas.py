import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Dict, List
import re
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
    location: Optional[str] = None
    settings: Optional[Dict] = None
    
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
    location: Optional[str] = None  # Champ calculé pour l'affichage de la localisation de la cellule
    settings: Optional[Dict] = None # Ajouté pour les administrateurs
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_cell(cls, cell: Cell, include_settings: bool = False) -> "CellDTO":
        """Convertit un Cell interne en CellDTO pour l'API."""
        data = {
            "id": cell.id,
            "name": cell.name,
            "parent_id": cell.area_id,
            "updated_at": cell.updated_at,
            "is_tracked": cell.is_tracked,
            "analytics": cell.analytics,
            "location": cell.location
        }
        if include_settings:
            data['settings'] = cell.settings
        
        return cls(**data)


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


class CellSettingsUpdate(BaseModel):
    """Schéma pour la mise à jour des paramètres de plusieurs cellules."""
    cell_ids: List[uuid.UUID] = Field(..., description="Liste des IDs des cellules à mettre à jour.")
    daily_update_count: int = Field(..., ge=0, description="Nombre de mises à jour par jour.")
    update_times: List[str] = Field(..., description='Liste des horaires de mise à jour (format "HH:MM").')
    measurement_frequency: int = Field(..., gt=0, description="Fréquence de relevé des capteurs (en secondes).")

    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Valide que l'heure est bien au format HH:MM."""
        if not isinstance(v, str) or not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', v):
            raise ValueError('L\'heure doit être au format "HH:MM"')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cell_ids": ["a1b2c3d4-e5f6-7890-1234-567890abcdef"],
                "daily_update_count": 2,
                "update_times": ["08:00", "20:00"],
                "measurement_frequency": 900
            }
        }
    )
