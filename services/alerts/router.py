from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models import User
from services.auth.dependencies import get_current_user
from services.audit.service import log_action
from .schemas import (
    # Alerts
    AlertResponseSchema,
    AlertCreateSchema,
    AlertUpdatedResponseSchema,
    AlertCreatedResponseSchema,
    AlertToggleSchema,
    AlertToggleResponseSchema,
    AlertDeletedResponseSchema,
    # Validate
    AlertValidateInputSchema,
    AlertValidateResponseSchema,
    # Events
    AlertEventResponseSchema,
    AlertEventArchivedResponseSchema,
    AlertEventsArchiveAllResponseSchema,
    AlertEventsArchiveByCellInputSchema,
    AlertEventsArchiveByCellResponseSchema,
)
from . import service

router = APIRouter()

@router.get(
    "/",
    response_model=List[AlertResponseSchema],
    response_model_by_alias=True,
    summary="Lister toutes les alertes",
)
def get_all_alerts(
    cell_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
):
    """
    Récupère toutes les alertes configurées.

    - **cell_id** *(optionnel)* : filtre les alertes associées à une cellule donnée.
    """
    return service.get_all_alerts(db, cell_id)


# ⚠️  /validate et /events/* AVANT /{id} pour éviter toute ambiguïté de routage

@router.post(
    "/validate",
    response_model=AlertValidateResponseSchema,
    response_model_by_alias=True,
    summary="Vérifier les conflits avant création",
)
def validate_alert(
    payload: AlertValidateInputSchema,
    db: Session = Depends(get_db),
):
    """
    Vérifie si des alertes existent déjà pour les cellules et types de capteurs fournis.
    Retourne la liste des conflits détectés.
    """
    return service.validate_alert(db, payload)


@router.get(
    "/{alert_id}",
    response_model=AlertResponseSchema,
    response_model_by_alias=True,
    summary="Détail d'une alerte",
)
def get_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Récupère les détails complets d'une alerte (utilisé pour la modification).
    """
    return service.get_alert_by_id(db, alert_id)


@router.post(
    "/",
    response_model=AlertCreatedResponseSchema,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une alerte",
)
def create_alert(
    alert_data: AlertCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crée une nouvelle alerte.

    - Si des conflits existent et que **overwriteExisting** est `false`, retourne `409 Conflict`.
    - Si **overwriteExisting** est `true`, les alertes en conflit sont supprimées avant création.
    """
    result = service.create_alert(db, alert_data)
    log_action(db, current_user, "create", "alert", result["id"], details={"title": result["title"]})
    return result


@router.put(
    "/{alert_id}",
    response_model=AlertUpdatedResponseSchema,
    summary="Mettre à jour une alerte",
)
def update_alert(
    alert_id: uuid.UUID,
    alert_data: AlertUpdatedResponseSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Met à jour une alerte existante (titre, cellules, capteurs, plages).
    """
    result = service.update_alert(db, alert_id, alert_data)
    log_action(db, current_user, "update", "alert", alert_id)
    return result


@router.patch(
    "/{alert_id}/toggle",
    response_model=AlertToggleResponseSchema,
    response_model_by_alias=True,
    summary="Activer / désactiver une alerte",
)
def toggle_alert(
    alert_id: uuid.UUID,
    payload: AlertToggleSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Active ou désactive une alerte depuis la vue cards.
    """
    result = service.toggle_alert(db, alert_id, payload)
    log_action(db, current_user, "toggle", "alert", alert_id, details={"is_active": payload.is_active})
    return result


@router.delete(
    "/{alert_id}",
    response_model=AlertDeletedResponseSchema,
    summary="Supprimer une alerte",
)
def delete_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Supprime définitivement une alerte (zone de danger en mode édition).
    """
    service.delete_alert(db, alert_id)
    log_action(db, current_user, "delete", "alert", alert_id)
    return {"message": "Alerte supprimée avec succès."}


@router.get(
    "/events/",
    response_model=List[AlertEventResponseSchema],
    response_model_by_alias=True,
    summary="Historique des événements d'alerte",
)
def get_alert_events(
    cell_id: Optional[uuid.UUID] = None,
    severity: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    Récupère l'historique des événements d'alerte non archivés.

    Filtres disponibles : **cellId**, **severity** (`critical` | `warning`),
    **startDate** et **endDate** (ISO 8601).
    """
    return service.get_alert_events(db, cell_id, severity, start_date, end_date)


@router.post(
    "/events/archive-all",
    response_model=AlertEventsArchiveAllResponseSchema,
    response_model_by_alias=True,
    summary="Archiver tous les événements",
)
def archive_all_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Archive tous les événements d'alerte non encore archivés.
    """
    result = service.archive_all_events(db)
    log_action(db, current_user, "archive_all", "alert", details={"archived_count": result.get("archivedCount", 0)})
    return result


@router.post(
    "/events/archive-by-cell",
    response_model=AlertEventsArchiveByCellResponseSchema,
    response_model_by_alias=True,
    summary="Archiver les événements d'une cellule",
)
def archive_events_by_cell(
    payload: AlertEventsArchiveByCellInputSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Archive tous les événements non archivés d'une cellule spécifique.
    """
    result = service.archive_events_by_cell(db, payload.cell_id)
    log_action(db, current_user, "archive_by_cell", "alert", entity_id=payload.cell_id, details={"archived_count": result.get("archivedCount", 0)})
    return result


@router.patch(
    "/events/{event_id}/archive",
    response_model=AlertEventArchivedResponseSchema,
    summary="Archiver un événement",
)
def archive_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Archive un événement d'alerte spécifique.
    """
    result = service.archive_event(db, event_id)
    log_action(db, current_user, "archive", "alert", entity_id=event_id)
    return result
