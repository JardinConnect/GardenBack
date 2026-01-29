''' [
  {
    "id": 1,
    "name": "Tomate Serre Nord $i",
    "is_tracked": true,
    "last_update_at": "2026-01-09 09:46:26",
    "location": "Champ #1 > Parcelle #3 > Planche A",
    "analytics": {
      "air_temperature": [
        {"value": 18, "occurredAt": "2025-11-05T08:00:00Z", "sensorId": 12, "alert_status":  "ALERT"}
      ],
      "soil_temperature": [
        {"value": 15, "occurredAt": "2025-11-05T08:00:00Z", "sensorId": 13, "alert_status":  "WARNING"}
      ],
      "air_humidity": [
        {"value": 65, "occurredAt": "2025-11-05T08:00:00Z", "sensorId": 12, "alert_status":  "OK"}
      ],
      "soil_humidity": [
        {"value": 45, "occurredAt": "2025-11-05T08:00:00Z", "sensorId": 12, "alert_status":  "WARNING"}
      ],
      "deep_soil_humidity": [
        {"value": 52, "occurredAt": "2025-11-05T08:00:00Z", "sensorId": 12, "alert_status":  "OK"}
      ],
      "light": [
        {"value": 35, "occurredAt": "2025-11-05T08:00:00Z", "sensorId": 12, "alert_status":  "ALERT"}
      ]
    }
  } 
] '''
import uuid
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, List
from db.models import AnalyticType
from services.analytics.schemas import AnalyticSchema

class Cell(BaseModel):
    id: uuid.UUID
    name: str
    battery: int
    is_tracked: Optional[bool] = False
    updated_at: str
    location: str
    analytics: Dict[AnalyticType, List[AnalyticSchema]]
    
    model_config = ConfigDict(from_attributes=True)

class CellCreate(BaseModel):
    name: str
    battery: int
    area_id: Optional[uuid.UUID] = Field(default=None)
