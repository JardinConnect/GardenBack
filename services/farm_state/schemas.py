from pydantic import BaseModel
from typing import Dict, Optional, List

from services.user.schemas import UserSchema
from services.area.schemas import AreaCreate


class FarmCreate(BaseModel):
    """Schéma pour la création de la ferme."""
    name: str
    address: str
    zip_code: str
    city: str
    phone_number: str


class OnboardingPayload(BaseModel):
    """Schéma pour le payload de configuration initiale de la ferme."""
    farm: FarmCreate
    user: UserSchema
    areas: List[AreaCreate] = []


class FarmStateSummary(BaseModel):
    """Represents a high-level summary of the farm's state."""
    total_users: int
    total_areas: int
    total_cells: int
    total_sensors: int
    sensor_types: Dict[str, int]


class FarmDetails(BaseModel):
    """Represents detailed information about a specific farm."""
    name: str
    address: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    phone_number: Optional[str] = None
    summary: FarmStateSummary
    average_analytics: Optional[Dict[str, float]] = None