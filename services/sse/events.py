"""Payloads Pydantic pour les messages SSE."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from db.models import AlertEvent


class HeartbeatPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["heartbeat"] = "heartbeat"


class AlertEventNotification(BaseModel):
    """Même périmètre public que l’API REST (événements d’alerte)."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    alert_id: uuid.UUID = Field(..., alias="alertId")
    alert_title: str = Field(..., alias="alertTitle")
    cell_id: uuid.UUID = Field(..., alias="cellId")
    cell_name: str = Field(..., alias="cellName")
    cell_location: str = Field(..., alias="cellLocation")
    sensor_type: str = Field(..., alias="sensorType")
    severity: str
    value: float
    threshold_min: float = Field(..., alias="thresholdMin")
    threshold_max: float = Field(..., alias="thresholdMax")
    timestamp: datetime
    is_archived: bool = Field(..., alias="isArchived")

    @classmethod
    def from_db(cls, event: AlertEvent) -> AlertEventNotification:
        sev = event.severity
        severity_str = sev.value if hasattr(sev, "value") else str(sev)
        return cls(
            id=event.id,
            alert_id=event.alert_id,
            alert_title=event.alert_title,
            cell_id=event.cell_id,
            cell_name=event.cell_name,
            cell_location=event.cell_location,
            sensor_type=event.sensor_type,
            severity=severity_str,
            value=event.value,
            threshold_min=event.threshold_min,
            threshold_max=event.threshold_max,
            timestamp=event.timestamp,
            is_archived=event.is_archived,
        )
