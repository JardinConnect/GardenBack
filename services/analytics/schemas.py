from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict
from db.models import AnalyticType


class AnalyticsFilter(BaseModel):
    analytic_type: Optional[AnalyticType] = Field(None, description="Type d'analytique")
    sensor_id: Optional[int] = Field(None, description="Identifiant du capteur")
    sensor_code: Optional[str] = Field(None, description="Code du capteur")
    start_date: datetime = Field(description="Date de début")
    end_date: datetime = Field(description="Date de fin")
    skip: int = Field(0, description="Nombre d'éléments à sauter (pour la pagination)")
    limit: int = Field(100, description="Nombre maximum d'éléments à retourner (pour la pagination)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analytic_type": AnalyticType.AIR_TEMPERATURE,
                "sensor_code": "AT-1",
                "sensor_id": 1,
                "start_date": "2025-11-03T00:00:00",
                "end_date": "2025-11-06T23:59:59",
                "skip": 0,     
                "limit": 50   
            }
        }
    )


class AnalyticSchema(BaseModel):
    analytic_type: AnalyticType
    value: float
    occured_at: datetime
    sensorCode: Optional[str] = None


class AnalyticResult(BaseModel):
    result: Dict[AnalyticType, List[AnalyticSchema]]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "result": {
                    "AIR_TEMPERATURE": [
                        {
                            "value": 22.5,
                            "occured_at": "2025-09-19T14:30:00",
                            "sensorCode": "AT-1"
                        },
                        {
                            "value": 23.1,
                            "occured_at": "2025-09-19T15:00:00",
                            "sensorCode": "AT-2"
                        }
                    ],
                    "SOIL_HUMIDITY": [
                        {
                            "value": 61.2,
                            "occured_at": "2025-09-19T14:30:00",
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
    limit: int
    data: Dict[AnalyticType, List[AnalyticSchema]]


class AnalyticCreate(BaseModel):
    sensor_code: str = Field(description="Code du capteur, ex: 'AT-1'")
    value: float = Field(description="Valeur de la mesure")
    timestamp: datetime = Field(description="Date et heure de la mesure")
    sensor_id: int = Field(description="Identifiant du capteur")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sensor_code": "AT-1",
                "value": 25.5,
                "timestamp": "2025-11-05T10:30:00",
                "sensor_id": 1
            }
        }
    )
