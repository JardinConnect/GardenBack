from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict
from db.models import AnalyticType


class AnalyticsFilter(BaseModel):
    analytic_type: Optional[AnalyticType] = Field(None, description="Type d'analytique")
    node_id: Optional[int] = Field(None, description="Identifiant du noeud")
    sensor_code: Optional[str] = Field(None, description="Code du capteur")
    start_date: datetime = Field(description="Date de début")
    end_date: datetime = Field(description="Date de fin")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analytic_type": AnalyticType.AIR_TEMPERATURE,
                "sensor_code": "AT-1",
                "node_id": 1,
                "start_date": "2025-11-03T00:00:00",
                "end_date": "2025-11-06T23:59:59",
            }
        }
    )


class AnalyticSchema(BaseModel):
    value: float
    occured_at: datetime
    sensorCode: str


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


class AnalyticCreate(BaseModel):
    sensor_code: str = Field(description="Code du capteur, ex: 'AT-1'")
    value: float = Field(description="Valeur de la mesure")
    timestamp: datetime = Field(description="Date et heure de la mesure")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sensor_code": "AT-1",
                "value": 25.5,
                "timestamp": "2025-11-05T10:30:00"
            }
        }
    )
