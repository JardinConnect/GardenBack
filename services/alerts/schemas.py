from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers partagés
# ---------------------------------------------------------------------------

class RangeSchema(BaseModel):
    min: float
    max: float


class RangeOptionalSchema(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None


class CellInfoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    location: Optional[str] = None


# ---------------------------------------------------------------------------
# Sensor
# ---------------------------------------------------------------------------

class AlertSensorSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    index: int
    critical_range: RangeSchema = Field(..., alias="criticalRange")
    warning_range: Optional[RangeOptionalSchema] = Field(None, alias="warningRange")

    def to_json_dict(self) -> dict:
        """Sérialise en camelCase pour stockage JSON."""
        return {
            "type": self.type,
            "index": self.index,
            "criticalRange": self.critical_range.model_dump(),
            "warningRange": self.warning_range.model_dump() if self.warning_range else None,
        }


# ---------------------------------------------------------------------------
# Alert — Entrées (Create / Update)
# ---------------------------------------------------------------------------

class AlertCreateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    is_active: bool = Field(True, alias="isActive")
    cell_ids: List[uuid.UUID] = Field(..., alias="cellIds")
    sensors: List[AlertSensorSchema]
    warning_enabled: bool = Field(False, alias="warningEnabled")
    overwrite_existing: bool = Field(False, alias="overwriteExisting")


class AlertUpdateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    is_active: bool = Field(..., alias="isActive")
    cell_ids: List[uuid.UUID] = Field(..., alias="cellIds")
    sensors: List[AlertSensorSchema]
    warning_enabled: bool = Field(False, alias="warningEnabled")


class AlertToggleSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_active: bool = Field(..., alias="isActive")


# ---------------------------------------------------------------------------
# Alert — Réponses
# ---------------------------------------------------------------------------

class AlertResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    title: str
    is_active: bool = Field(..., alias="isActive")
    cell_ids: List[uuid.UUID] = Field(..., alias="cellIds")
    cells: List[CellInfoSchema]
    sensors: List[AlertSensorSchema]
    warning_enabled: bool = Field(..., alias="warningEnabled")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class AlertCreatedResponseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    title: str
    message: str
    overwritten_alerts: List[uuid.UUID] = Field(default_factory=list, alias="overwrittenAlerts")


class AlertUpdatedResponseSchema(BaseModel):
    id: uuid.UUID
    title: str
    message: str


class AlertToggleResponseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    is_active: bool = Field(..., alias="isActive")
    message: str


class AlertDeletedResponseSchema(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Validate — Conflits
# ---------------------------------------------------------------------------

class AlertValidateInputSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cell_ids: List[uuid.UUID] = Field(..., alias="cellIds")
    sensor_types: List[str] = Field(..., alias="sensorTypes")


class AlertConflictItemSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cell_id: uuid.UUID = Field(..., alias="cellId")
    cell_name: str = Field(..., alias="cellName")
    sensor_type: str = Field(..., alias="sensorType")
    existing_alert_id: uuid.UUID = Field(..., alias="existingAlertId")
    existing_alert_title: str = Field(..., alias="existingAlertTitle")
    message: str


class AlertValidateResponseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    conflicts: List[AlertConflictItemSchema]
    has_conflicts: bool = Field(..., alias="hasConflicts")


# ---------------------------------------------------------------------------
# Alert Events
# ---------------------------------------------------------------------------

class AlertEventResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

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


class AlertEventArchivedResponseSchema(BaseModel):
    id: uuid.UUID
    message: str


class AlertEventsArchiveAllResponseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    archived_count: int = Field(..., alias="archivedCount")
    message: str


class AlertEventsArchiveByCellInputSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cell_id: uuid.UUID = Field(..., alias="cellId")


class AlertEventsArchiveByCellResponseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    archived_count: int = Field(..., alias="archivedCount")
    cell_id: uuid.UUID = Field(..., alias="cellId")
    message: str
