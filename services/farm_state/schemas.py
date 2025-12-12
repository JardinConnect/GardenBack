from pydantic import BaseModel
from typing import Dict


class FarmStateSummary(BaseModel):
    """Represents a high-level summary of the farm's state."""
    total_users: int
    total_areas: int
    total_cells: int
    total_sensors: int
    sensor_types: Dict[str, int]