from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict
import uuid
from db.models import AnalyticType


class AnalyticsFilter(BaseModel):
    analytic_type: Optional[AnalyticType] = Field(None, description="Type d'analytique")
    sensor_id: Optional[uuid.UUID] = Field(None, description="Identifiant du capteur")
    sensor_code: Optional[str] = Field(None, description="Code du capteur")
    area_id: Optional[uuid.UUID] = Field(None, description="Identifiant de l'area (filtre sur la cellule parente)")
    start_date: datetime = Field(description="Date de début")
    end_date: datetime = Field(description="Date de fin")
    skip: int = Field(0, description="Nombre d'éléments à sauter (pour la pagination)")
    limit: Optional[int] = Field(None, ge=1, description="Nombre maximum d'éléments à retourner (pour la pagination)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analytic_type": AnalyticType.AIR_TEMPERATURE,
                "sensor_code": "AT-1",
                "sensor_id": "13fe605f-a3bd-4e66-8615-cb7ff99ba017",
                "area_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "start_date": "2025-11-03T00:00:00",
                "end_date": "2025-11-06T23:59:59",
                "skip": 0,
                "limit": 50
            }
        }
    )


class AnalyticSchema(BaseModel):
    value: float
    occurred_at: datetime
    sensorCode: Optional[str] = Field(None, alias='sensor_code')

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)



class AnalyticResult(BaseModel):
    result: Dict[AnalyticType, List[AnalyticSchema]]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "result": {
                    "AIR_TEMPERATURE": [
                        {
                            "value": 22.5,
                            "occurred_at": "2025-09-19T14:30:00",
                            "sensorCode": "AT-1"
                        },
                        {
                            "value": 23.1,
                            "occurred_at": "2025-09-19T15:00:00",
                            "sensorCode": "AT-2"
                        }
                    ],
                    "SOIL_HUMIDITY": [
                        {
                            "value": 61.2,
                            "occurred_at": "2025-09-19T14:30:00",
                            "sensorCode": "SH-1"
                        }
                    ]
                }
            }
        }
    )

class PaginatedAnalyticResult(BaseModel):
    """Schéma pour une réponse analytique paginée."""
    total: int
    skip: int
    limit: Optional[int]
    data: Dict[AnalyticType, List[AnalyticSchema]]


class AnalyticCreate(BaseModel):
    sensor_code: str = Field(description="Code du capteur, ex: 'AT-1'")
    value: float = Field(description="Valeur de la mesure")
    timestamp: datetime = Field(description="Date et heure de la mesure")
    sensor_id: uuid.UUID = Field(description="Identifiant du capteur")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sensor_code": "AT-1",
                "value": 25.5,
                "timestamp": "2025-11-05T10:30:00",
                "sensor_id": "8289d9e4-4469-43ac-b022-b93ceeea61ff"
            }
        }
    )