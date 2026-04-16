from __future__ import annotations

from typing import List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
import uuid

from db.models import Alert, AlertEvent, Cell, SeverityEnum
from .schemas import (
    AlertCreateUpdateSchema, AlertSensorSchema, AlertToggleSchema, AlertValidateInputSchema, AlertResponseSchema, CellInfoSchema
)
from .errors import AlertNotFoundError, AlertEventNotFoundError, AlertConflictError
from services.area.service import get_full_location_path_for_cell
from services.sse.runtime import notify_alert_event_if_configured


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _build_alert_response(alert: Alert, db: Session) -> AlertResponseSchema:
    """
    Construit un schéma de réponse `AlertResponseSchema` à partir d'un modèle `Alert`.

    Cette fonction enrichit l'objet en :
    - Résolvant les `cell_ids` pour récupérer les noms et localisations des cellules.
    - S'assurant que la structure des capteurs (`sensors`) est conforme au schéma Pydantic.
    """
    cell_uuids = [uuid.UUID(c) if isinstance(c, str) else c for c in alert.cell_ids]

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


def _detect_conflicts(db: Session, cell_ids: List[uuid.UUID], sensor_types: List[str], exclude_alert_id: Optional[uuid.UUID] = None) -> List[dict]:
    """
    Détecte les conflits entre une configuration d'alerte potentielle et les alertes existantes.

    Un conflit se produit si une alerte existante surveille déjà le même type de capteur
    sur l'une des mêmes cellules.

    Args:
        db: La session de base de données.
        cell_ids: Liste des IDs de cellules pour la nouvelle alerte/mise à jour.
        sensor_types: Liste des types de capteurs pour la nouvelle alerte/mise à jour.
        exclude_alert_id: ID d'une alerte à exclure de la détection (utile lors d'une mise à jour).

    Returns:
        Une liste de dictionnaires, chaque dictionnaire représentant un conflit trouvé.
    """
    conflicts: List[dict] = []

    query = db.query(Alert)
    if exclude_alert_id:
        query = query.filter(Alert.id != exclude_alert_id)

    all_alerts = query.all()

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


def _resolve_conflicts(db: Session, conflicts: List[dict], new_alert_cell_ids: List[uuid.UUID]) -> List[uuid.UUID]:
    """
    Résout les conflits en "éclatant" l'alerte existante.

    Pour une alerte existante A sur (c1, c2, c3) pour le capteur S, si une nouvelle alerte B
    est créée sur (c1) pour le capteur S avec overwrite=true :
    1. La configuration du capteur S est retirée de l'alerte A.
    2. Une nouvelle alerte A' est créée, avec la configuration de S, pour les cellules (c2, c3) restantes.
       Son nom est "Nom de A (conflit)".
    3. Si l'alerte A devient vide (plus de capteurs), elle est supprimée.

    Args:
        db: La session de base de données.
        conflicts: La liste des conflits détectés par `_detect_conflicts`.
        new_alert_cell_ids: Liste des IDs de cellules de la nouvelle alerte en cours de création.

    Returns:
        La liste des IDs des alertes qui ont été entièrement supprimées (car devenues vides).
    """
    deleted_alert_ids: List[uuid.UUID] = []
    if not conflicts:
        return deleted_alert_ids

    conflicts_by_alert_id = defaultdict(list)
    for conflict in conflicts:
        conflicts_by_alert_id[conflict['existingAlertId']].append(conflict)

    new_alert_cell_ids_set = set(new_alert_cell_ids)

    for alert_id_str, alert_conflicts in conflicts_by_alert_id.items():
        alert_id = uuid.UUID(alert_id_str)
        existing_alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not existing_alert:
            continue

        conflicting_sensor_types = {c['sensorType'] for c in alert_conflicts}
        original_cell_ids = {uuid.UUID(cid) for cid in existing_alert.cell_ids}
        original_sensors = existing_alert.sensors or []

        remaining_cell_ids = original_cell_ids - new_alert_cell_ids_set

        if remaining_cell_ids:
            # Regrouper tous les capteurs en conflit qui doivent être éclatés
            split_off_sensors = [
                s for s in original_sensors if s.get('type') in conflicting_sensor_types
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

        updated_sensors = [s for s in original_sensors if s.get('type') not in conflicting_sensor_types]

        if not updated_sensors:
            deleted_alert_ids.append(existing_alert.id)
            db.delete(existing_alert)
        else:
            existing_alert.sensors = updated_sensors

    return deleted_alert_ids


# ---------------------------------------------------------------------------
# Alertes — CRUD
# ---------------------------------------------------------------------------

def get_all_alerts(db: Session, cell_id: Optional[uuid.UUID] = None) -> List[AlertResponseSchema]:
    """Récupère toutes les alertes, avec un filtre optionnel par cellule."""
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
    """Récupère une alerte par son ID."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise AlertNotFoundError(alert_id)
    return _build_alert_response(alert, db)


def validate_alert(db: Session, payload: AlertValidateInputSchema) -> dict:
    """
    Valide une configuration d'alerte potentielle pour détecter les conflits.
    Utilisé par le front-end avant de soumettre une création ou une mise à jour.
    """
    conflicts = _detect_conflicts(
        db, payload.cell_ids, payload.sensor_types, exclude_alert_id=payload.alert_id
    )
    return {
        "conflicts": conflicts,
        "hasConflicts": len(conflicts) > 0,
    }


def create_alert(db: Session, alert_data: AlertCreateUpdateSchema) -> dict:
    """
    Crée une nouvelle alerte.

    Gère les conflits avec les alertes existantes :
    - Si `overwriteExisting` est `False`, lève une exception `AlertConflictError`.
    - Si `overwriteExisting` est `True`, résout les conflits en modifiant ou supprimant
      les parties conflictuelles des alertes existantes via `_resolve_conflicts`.
    """
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

    return {
        "id": new_alert.id,
        "title": new_alert.title,
        "message": "Alerte créée avec succès.",
        "overwrittenAlerts": overwritten_alert_ids,
    }


def update_alert(db: Session, alert_id: uuid.UUID, alert_data: AlertCreateUpdateSchema) -> dict:
    """
    Met à jour une alerte existante.

    Gère les conflits avec d'autres alertes de la même manière que `create_alert` :
    - Si `overwriteExisting` est `False`, lève une exception `AlertConflictError`.
    - Si `overwriteExisting` est `True`, résout les conflits en modifiant ou supprimant
      les parties conflictuelles des autres alertes via `_resolve_conflicts`.
    """
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

    return {
        "id": alert.id,
        "title": alert.title,
        "message": "Alerte mise à jour avec succès.",
        "overwrittenAlerts": overwritten_alert_ids,
    }


def toggle_alert(db: Session, alert_id: uuid.UUID, payload: AlertToggleSchema) -> dict:
    """Active ou désactive une alerte."""
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
    """Supprime une alerte et ses événements associés (via cascade)."""
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
    """Récupère l'historique des événements d'alerte non archivés, avec filtres."""
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
    """Persiste un événement d’alerte et notifie les clients SSE."""
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
    """Archive un événement d'alerte spécifique."""
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
    """Archive tous les événements d'alerte non encore archivés."""
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
    """Archive tous les événements non archivés pour une cellule spécifique."""
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
