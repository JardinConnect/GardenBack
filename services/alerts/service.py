from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session
import uuid

from db.models import Alert, AlertEvent, Cell
from .schemas import (
    AlertCreateSchema,
    AlertUpdateSchema,
    AlertToggleSchema,
    AlertValidateInputSchema,
    AlertSensorSchema,
    AlertResponseSchema,
    CellInfoSchema,
)
from .errors import AlertNotFoundError, AlertEventNotFoundError, AlertConflictError


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _build_alert_response(alert: Alert, db: Session) -> AlertResponseSchema:
    """Construit une AlertResponseSchema en enrichissant cells depuis la DB."""
    cell_uuids = [uuid.UUID(c) if isinstance(c, str) else c for c in alert.cell_ids]

    cells_data: List[CellInfoSchema] = []
    for cid in cell_uuids:
        cell = db.query(Cell).filter(Cell.id == cid).first()
        if cell:
            area_name = cell.area.name if cell.area else ""
            cells_data.append(
                CellInfoSchema(
                    id=cell.id,
                    name=cell.name,
                    location=area_name,
                )
            )

    sensors = [
        AlertSensorSchema(
            type=s["type"],
            index=s["index"],
            criticalRange=s["criticalRange"],
            warningRange=s.get("warningRange"),
        )
        for s in (alert.sensors or [])
    ]

    return AlertResponseSchema(
        id=alert.id,
        isActive=alert.is_active,
        title=alert.title,
        cellIds=cell_uuids,
        cells=cells_data,
        sensors=sensors,
        warningEnabled=alert.warning_enabled,
        createdAt=alert.created_at,
        updatedAt=alert.updated_at,
    )


def _detect_conflicts(db: Session, cell_ids: List[uuid.UUID], sensor_types: List[str]) -> List[dict]:
    """Retourne la liste des conflits (cellule × type de capteur déjà couverts par une alerte)."""
    conflicts: List[dict] = []

    all_alerts = db.query(Alert).all()

    for alert in all_alerts:
        existing_cell_ids = {
            uuid.UUID(c) if isinstance(c, str) else c
            for c in alert.cell_ids
        }
        existing_sensor_types = {s["type"] for s in (alert.sensors or [])}

        for cid in cell_ids:
            if cid not in existing_cell_ids:
                continue
            for stype in sensor_types:
                if stype not in existing_sensor_types:
                    continue
                # Conflict trouvé
                cell = db.query(Cell).filter(Cell.id == cid).first()
                cell_name = cell.name if cell else str(cid)
                conflicts.append(
                    {
                        "cellId": str(cid),
                        "cellName": cell_name,
                        "sensorType": stype,
                        "existingAlertId": str(alert.id),
                        "existingAlertTitle": alert.title,
                        "message": (
                            f"Cette cellule contient déjà une alerte sur le capteur '{stype}'."
                        ),
                    }
                )

    return conflicts


# ---------------------------------------------------------------------------
# Alertes — CRUD
# ---------------------------------------------------------------------------

def get_all_alerts(db: Session, cell_id: Optional[uuid.UUID] = None) -> List[AlertResponseSchema]:
    query = db.query(Alert)
    alerts = query.all()

    if cell_id:
        cell_id_str = str(cell_id)
        alerts = [
            a for a in alerts
            if cell_id_str in [str(c) for c in a.cell_ids]
        ]

    return [_build_alert_response(a, db) for a in alerts]


def get_alert_by_id(db: Session, alert_id: uuid.UUID) -> AlertResponseSchema:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise AlertNotFoundError(alert_id)
    return _build_alert_response(alert, db)


def validate_alert(db: Session, payload: AlertValidateInputSchema) -> dict:
    conflicts = _detect_conflicts(db, payload.cell_ids, payload.sensor_types)
    return {
        "conflicts": conflicts,
        "hasConflicts": len(conflicts) > 0,
    }


def create_alert(db: Session, alert_data: AlertCreateSchema) -> dict:
    sensor_types = [s.type for s in alert_data.sensors]
    conflicts = _detect_conflicts(db, alert_data.cell_ids, sensor_types)

    overwritten_alert_ids: List[uuid.UUID] = []

    if conflicts and not alert_data.overwrite_existing:
        raise AlertConflictError(conflicts)

    if conflicts and alert_data.overwrite_existing:
        # Supprimer les alertes en conflit
        conflicting_ids = {uuid.UUID(c["existingAlertId"]) for c in conflicts}
        for aid in conflicting_ids:
            existing = db.query(Alert).filter(Alert.id == aid).first()
            if existing:
                overwritten_alert_ids.append(existing.id)
                db.delete(existing)

    new_alert = Alert(
        title=alert_data.title,
        is_active=alert_data.is_active,
        warning_enabled=alert_data.warning_enabled,
        cell_ids=[str(cid) for cid in alert_data.cell_ids],
        sensors=[s.to_json_dict() for s in alert_data.sensors],
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)

    return {
        "id": new_alert.id,
        "title": new_alert.title,
        "message": "Alerte créée avec succès.",
        "overwrittenAlerts": overwritten_alert_ids,
    }


def update_alert(db: Session, alert_id: uuid.UUID, alert_data: AlertUpdateSchema) -> dict:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise AlertNotFoundError(alert_id)

    alert.title = alert_data.title
    alert.is_active = alert_data.is_active
    alert.warning_enabled = alert_data.warning_enabled
    alert.cell_ids = [str(cid) for cid in alert_data.cell_ids]
    alert.sensors = [s.to_json_dict() for s in alert_data.sensors]

    db.commit()
    db.refresh(alert)

    return {
        "id": alert.id,
        "title": alert.title,
        "message": "Alerte mise à jour avec succès.",
    }


def toggle_alert(db: Session, alert_id: uuid.UUID, payload: AlertToggleSchema) -> dict:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise AlertNotFoundError(alert_id)

    alert.is_active = payload.is_active
    db.commit()
    db.refresh(alert)

    return {
        "id": alert.id,
        "isActive": alert.is_active,
        "message": "Statut de l'alerte mis à jour.",
    }


def delete_alert(db: Session, alert_id: uuid.UUID) -> None:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise AlertNotFoundError(alert_id)
    db.delete(alert)
    db.commit()


# ---------------------------------------------------------------------------
# Événements d'alerte
# ---------------------------------------------------------------------------

def get_alert_events(
    db: Session,
    cell_id: Optional[uuid.UUID] = None,
    severity: Optional[str] = None,
    start_date=None,
    end_date=None,
) -> List[AlertEvent]:
    query = db.query(AlertEvent).filter(AlertEvent.is_archived == False)  # noqa: E712

    if cell_id:
        query = query.filter(AlertEvent.cell_id == cell_id)
    if severity:
        query = query.filter(AlertEvent.severity == severity)
    if start_date:
        query = query.filter(AlertEvent.timestamp >= start_date)
    if end_date:
        query = query.filter(AlertEvent.timestamp <= end_date)

    return query.order_by(AlertEvent.timestamp.desc()).all()


def archive_event(db: Session, event_id: uuid.UUID) -> dict:
    event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if not event:
        raise AlertEventNotFoundError(event_id)

    event.is_archived = True
    db.commit()

    return {
        "id": event.id,
        "message": "Événement archivé avec succès.",
    }


def archive_all_events(db: Session) -> dict:
    result = (
        db.query(AlertEvent)
        .filter(AlertEvent.is_archived == False)  # noqa: E712
        .all()
    )
    count = len(result)
    for event in result:
        event.is_archived = True
    db.commit()

    return {
        "archivedCount": count,
        "message": "Tous les événements ont été archivés.",
    }


def archive_events_by_cell(db: Session, cell_id: uuid.UUID) -> dict:
    result = (
        db.query(AlertEvent)
        .filter(AlertEvent.cell_id == cell_id, AlertEvent.is_archived == False)  # noqa: E712
        .all()
    )
    count = len(result)
    for event in result:
        event.is_archived = True
    db.commit()

    return {
        "archivedCount": count,
        "cellId": cell_id,
        "message": "Événements de la cellule archivés avec succès.",
    }
