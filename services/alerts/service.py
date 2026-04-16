from __future__ import annotations

import json
import uuid
from collections import defaultdict
from typing import AsyncGenerator, List, Optional

from sqlalchemy.orm import Session, attributes

from db.models import Alert, AlertEvent, Cell, SeverityEnum
from services.area.service import get_full_location_path_for_cell
from services.mqtt.client import publish
from services.mqtt.pending_acks import cancel_pending_ack, create_pending_ack, wait_for_ack
from services.sse.runtime import notify_alert_event_if_configured
from settings import settings

from .errors import AlertConflictError, AlertEventNotFoundError, AlertNotFoundError
from .schemas import (
    AlertCreateUpdateSchema,
    AlertResponseSchema,
    AlertSensorSchema,
    AlertToggleSchema,
    AlertValidateInputSchema,
    CellInfoSchema,
)


# ---------------------------------------------------------------------------
# Alerte batterie par défaut
# ---------------------------------------------------------------------------


def associate_cell_to_default_battery_alert(db: Session, cell_id: uuid.UUID) -> None:
    """Associe une cellule à l’alerte batterie faible par défaut (sans commit)."""
    default_alert_title = "Alerte Batterie Faible - " + str(cell_id)[:8]

    battery_alert_config = {
        "title": default_alert_title,
        "is_active": True,
        "warning_enabled": True,
        "sensors": [
            {
                "type": "battery",
                "index": 0,
                "criticalRange": {"min": 0.0, "max": 10.0},
                "warningRange": {"min": 10.1, "max": 20.0},
            }
        ],
    }

    alert = db.query(Alert).filter(Alert.title == default_alert_title).first()

    if alert:
        if str(cell_id) not in alert.cell_ids:
            alert.cell_ids.append(str(cell_id))
            attributes.flag_modified(alert, "cell_ids")
    else:
        new_alert = Alert(**battery_alert_config, cell_ids=[str(cell_id)])
        db.add(new_alert)


# ---------------------------------------------------------------------------
# Publication MQTT de la config alerte
# ---------------------------------------------------------------------------


def _publish_alert_to_mqtt(alert: Alert, db: Session) -> None:
    """Publie la configuration d’une alerte (deviceIDs + plages)."""
    device_ids: List[str] = []
    for cid_raw in alert.cell_ids or []:
        cid = uuid.UUID(cid_raw) if isinstance(cid_raw, str) else cid_raw
        cell = db.query(Cell).filter(Cell.id == cid).first()
        if cell:
            device_ids.append(cell.deviceID)
        else:
            print(f"[MQTT][alert] Cell {cid_raw} introuvable, ignorée pour MQTT.")

    mqtt_sensors = []
    for s in alert.sensors or []:
        sensor_entry = {
            "type": s["type"],
            "index": s["index"],
            "criticalRange": [s["criticalRange"]["min"], s["criticalRange"]["max"]],
        }
        if s.get("warningRange") and s["warningRange"].get("min") is not None:
            sensor_entry["warningRange"] = [s["warningRange"]["min"], s["warningRange"]["max"]]
        mqtt_sensors.append(sensor_entry)

    payload = json.dumps(
        {
            "id": str(alert.id),
            "is_active": alert.is_active,
            "cell_ids": device_ids,
            "sensors": mqtt_sensors,
        }
    )

    try:
        publish(settings.MQTT_TOPIC_ALERTS_CONFIG, payload)
        print(f"[MQTT][alert] Config publiée pour alerte '{alert.title}' → {device_ids}")
    except Exception as e:
        print(f"[MQTT][alert] Erreur publication config: {e}")


# ---------------------------------------------------------------------------
# Construction de réponses et conflits
# ---------------------------------------------------------------------------


def _build_alert_response(alert: Alert, db: Session) -> AlertResponseSchema:
    cell_uuids = [uuid.UUID(c) for c in alert.cell_ids if c is not None]

    cells_data: List[CellInfoSchema] = []
    for cid in cell_uuids:
        cell = db.query(Cell).filter(Cell.id == cid).first()
        if cell:
            full_location = get_full_location_path_for_cell(cell)
            cells_data.append(
                CellInfoSchema(
                    id=cell.id,
                    name=cell.name,
                    location=full_location,
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


def _detect_conflicts(
    db: Session,
    cell_ids: List[uuid.UUID],
    sensor_types: List[str],
    exclude_alert_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    conflicts: List[dict] = []

    query = db.query(Alert)
    if exclude_alert_id:
        query = query.filter(Alert.id != exclude_alert_id)

    all_alerts = query.all()

    for alert in all_alerts:
        existing_cell_ids = {
            uuid.UUID(c) if isinstance(c, str) else c for c in alert.cell_ids
        }
        existing_sensor_types = {s["type"] for s in (alert.sensors or [])}

        for cid in cell_ids:
            if cid not in existing_cell_ids:
                continue
            for stype in sensor_types:
                if stype not in existing_sensor_types:
                    continue
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


def _resolve_conflicts(
    db: Session, conflicts: List[dict], new_alert_cell_ids: List[uuid.UUID]
) -> List[uuid.UUID]:
    deleted_alert_ids: List[uuid.UUID] = []
    if not conflicts:
        return deleted_alert_ids

    conflicts_by_alert_id = defaultdict(list)
    for conflict in conflicts:
        conflicts_by_alert_id[conflict["existingAlertId"]].append(conflict)

    new_alert_cell_ids_set = set(new_alert_cell_ids)

    for alert_id_str, alert_conflicts in conflicts_by_alert_id.items():
        alert_id = uuid.UUID(alert_id_str)
        existing_alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not existing_alert:
            continue

        conflicting_sensor_types = {c["sensorType"] for c in alert_conflicts}
        original_cell_ids = {uuid.UUID(cid) for cid in existing_alert.cell_ids}
        original_sensors = existing_alert.sensors or []

        remaining_cell_ids = original_cell_ids - new_alert_cell_ids_set

        if remaining_cell_ids:
            split_off_sensors = [
                s for s in original_sensors if s.get("type") in conflicting_sensor_types
            ]
            if split_off_sensors:
                split_off_alert = Alert(
                    title=f"{existing_alert.title} (conflit)",
                    is_active=existing_alert.is_active,
                    warning_enabled=existing_alert.warning_enabled,
                    cell_ids=[str(cid) for cid in remaining_cell_ids],
                    sensors=split_off_sensors,
                )
                db.add(split_off_alert)

        updated_sensors = [s for s in original_sensors if s.get("type") not in conflicting_sensor_types]

        if not updated_sensors:
            deleted_alert_ids.append(existing_alert.id)
            db.delete(existing_alert)
        else:
            existing_alert.sensors = updated_sensors

    return deleted_alert_ids


# ---------------------------------------------------------------------------
# CRUD alertes
# ---------------------------------------------------------------------------


def get_all_alerts(db: Session, cell_id: Optional[uuid.UUID] = None) -> List[AlertResponseSchema]:
    query = db.query(Alert)
    alerts = query.all()

    if cell_id:
        cell_id_str = str(cell_id)
        alerts = [a for a in alerts if cell_id_str in [str(c) for c in a.cell_ids]]

    return [_build_alert_response(a, db) for a in alerts]


def get_alert_by_id(db: Session, alert_id: uuid.UUID) -> AlertResponseSchema:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise AlertNotFoundError(alert_id)
    return _build_alert_response(alert, db)


def validate_alert(db: Session, payload: AlertValidateInputSchema) -> dict:
    conflicts = _detect_conflicts(
        db, payload.cell_ids, payload.sensor_types, exclude_alert_id=payload.alert_id
    )
    return {
        "conflicts": conflicts,
        "hasConflicts": len(conflicts) > 0,
    }


def create_alert(db: Session, alert_data: AlertCreateUpdateSchema) -> dict:
    sensor_types = [s.type for s in alert_data.sensors]
    conflicts = _detect_conflicts(db, alert_data.cell_ids, sensor_types)

    overwritten_alert_ids: List[uuid.UUID] = []

    if conflicts and not alert_data.overwrite_existing:
        raise AlertConflictError(conflicts)

    if conflicts and alert_data.overwrite_existing:
        overwritten_alert_ids = _resolve_conflicts(db, conflicts, alert_data.cell_ids)

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

    _publish_alert_to_mqtt(new_alert, db)

    return {
        "id": new_alert.id,
        "title": new_alert.title,
        "message": "Alerte créée avec succès.",
        "overwrittenAlerts": overwritten_alert_ids,
    }


def update_alert(db: Session, alert_id: uuid.UUID, alert_data: AlertCreateUpdateSchema) -> dict:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise AlertNotFoundError(alert_id)

    sensor_types = [s.type for s in alert_data.sensors]
    conflicts = _detect_conflicts(
        db, alert_data.cell_ids, sensor_types, exclude_alert_id=alert_id
    )

    overwritten_alert_ids: List[uuid.UUID] = []

    if conflicts and not alert_data.overwrite_existing:
        raise AlertConflictError(conflicts)

    if conflicts and alert_data.overwrite_existing:
        overwritten_alert_ids = _resolve_conflicts(db, conflicts, alert_data.cell_ids)

    alert.title = alert_data.title
    alert.is_active = alert_data.is_active
    alert.warning_enabled = alert_data.warning_enabled
    alert.cell_ids = [str(cid) for cid in alert_data.cell_ids]
    alert.sensors = [s.to_json_dict() for s in alert_data.sensors]

    db.commit()
    db.refresh(alert)

    _publish_alert_to_mqtt(alert, db)

    return {
        "id": alert.id,
        "title": alert.title,
        "message": "Alerte mise à jour avec succès.",
        "overwrittenAlerts": overwritten_alert_ids,
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
# Événements d’alerte (historique + SSE)
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


def create_alert_event(
    db: Session,
    *,
    alert_id: uuid.UUID,
    alert_title: str,
    cell_id: uuid.UUID,
    cell_name: str,
    cell_location: str,
    sensor_type: str,
    severity: SeverityEnum,
    value: float,
    threshold_min: float,
    threshold_max: float,
) -> AlertEvent:
    """Persiste un événement et notifie les abonnés SSE."""
    event = AlertEvent(
        alert_id=alert_id,
        alert_title=alert_title,
        cell_id=cell_id,
        cell_name=cell_name,
        cell_location=cell_location,
        sensor_type=sensor_type,
        severity=severity,
        value=value,
        threshold_min=threshold_min,
        threshold_max=threshold_max,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    notify_alert_event_if_configured(event)
    return event


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


# ---------------------------------------------------------------------------
# Streaming : push config MQTT + attente d’ack device
# ---------------------------------------------------------------------------


async def push_alert_config_stream(
    db: Session,
    alert_id: uuid.UUID,
) -> AsyncGenerator[dict, None]:
    """Étapes de publication MQTT et attente d’acquittement (événements pour le client stream)."""

    def _event(event_type: str, step: str, message: str, **extra) -> dict:
        return {
            "event": event_type,
            "data": json.dumps({"step": step, "message": message, **extra}, default=str),
        }

    ack_id = str(uuid.uuid4())

    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            yield _event("error", "failed", f"Alerte {alert_id} non trouvée.")
            return

        yield _event("status", "publishing", "Envoi de la configuration sur MQTT...")

        device_ids: List[str] = []
        for cid_raw in alert.cell_ids or []:
            cid = uuid.UUID(cid_raw) if isinstance(cid_raw, str) else cid_raw
            cell = db.query(Cell).filter(Cell.id == cid).first()
            if cell:
                device_ids.append(cell.deviceID)

        mqtt_sensors = []
        for s in alert.sensors or []:
            sensor_entry = {
                "type": s["type"],
                "index": s["index"],
                "criticalRange": [s["criticalRange"]["min"], s["criticalRange"]["max"]],
            }
            if s.get("warningRange") and s["warningRange"].get("min") is not None:
                sensor_entry["warningRange"] = [s["warningRange"]["min"], s["warningRange"]["max"]]
            mqtt_sensors.append(sensor_entry)

        config_payload = json.dumps(
            {
                "ack_id": ack_id,
                "id": str(alert.id),
                "is_active": alert.is_active,
                "cell_ids": device_ids,
                "sensors": mqtt_sensors,
            }
        )

        create_pending_ack(ack_id)
        publish(settings.MQTT_TOPIC_ALERTS_CONFIG, config_payload)

        yield _event("status", "waiting_ack", "En attente de la confirmation du device...")

        result = await wait_for_ack(ack_id, timeout=15.0)

        if result is None:
            yield _event("error", "timeout", "Le device n'a pas répondu dans le délai imparti.")
            return

        if result.get("status") != "ok":
            error_msg = result.get("message", "Erreur inconnue du device.")
            yield _event("error", "device_error", error_msg, device_response=result)
            return

        yield _event(
            "completed",
            "completed",
            "Configuration appliquée avec succès.",
            alert_id=str(alert.id),
            device_response=result,
        )

    except Exception as exc:
        cancel_pending_ack(ack_id)
        yield _event("error", "failed", str(exc))
