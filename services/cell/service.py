from typing import List, Dict, Optional
import uuid
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
import services.cell.repository as repositoryCell
from datetime import datetime
import services.area.repository as repositoryArea
import services.cell.schemas as schemas
import services.cell.errors as errors
from db.models import Analytic as AnalyticModel, AnalyticType
import asyncio
import json
from typing import AsyncGenerator

def create_cell(db: Session, cell_data: schemas.CellCreate, commit: bool = True) -> schemas.Cell:
    """
    Crée une nouvelle cellule (Cell) dans la base de données.
    """
    if cell_data.area_id:
        area = repositoryArea.get_by_id(db, cell_data.area_id)
        if not area:
            raise errors.ParentCellNotFoundError
            
    # On passe le paramètre 'commit' au repository
    cell = repositoryCell.create_cell(db, cell_data, commit=commit) 
    
    return cell

def delete_cell(db: Session, cell_id: uuid.UUID) -> bool:
    """
    Supprime une cellule de la base de données.
    """
    return repositoryCell.delete_cell(db, cell_id)

def update_cell(db: Session, cell_id: uuid.UUID, cell_data: schemas.CellUpdate) -> schemas.Cell:
    """
    Met à jour une cellule de la base de données.
    """
    # Validate area if provided
    if cell_data.area_id:
        area = repositoryArea.get_by_id(db, cell_data.area_id)
        if not area:
            raise errors.ParentCellNotFoundError
    
    return repositoryCell.update_cell(db, cell_id, cell_data)

def get_cell(db: Session, cell_id: uuid.UUID, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> schemas.Cell:
    """
    Récupère une cellule de la base de données.
    """
    if from_date and to_date and from_date > to_date:
        raise errors.InvalidDateRangeError("La date de début (from) ne peut pas être postérieure à la date de fin (to).")

    cell = repositoryCell.get_cell_by_id(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    analytics = get_all_analytics_for_cell(db, cell_id, from_date, to_date)
    cell.analytics = analytics
    return cell

def get_cells(db: Session) -> List[schemas.Cell]:
    """
    Récupère toutes les cellules de la base de données.
    """
    cells = repositoryCell.get_cells(db)
    for cell in cells:
        analytics = get_analytics_for_cell(db, cell.id)
        cell.analytics = analytics
    return cells


def get_analytics_for_cell(db: Session, cell_id: uuid.UUID) -> List[Dict[AnalyticType, AnalyticModel]]:
    """
    Récupère la dernière analytique de chaque type pour tous les capteurs d'une cellule.
    """
    cell = repositoryCell.get_cell_by_id(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    
    sensor_ids = [sensor.id for sensor in cell.sensors]
    if not sensor_ids:
        return {}

    # Sous-requête pour trouver la dernière analytique de chaque type
    subquery = db.query(
        AnalyticModel.analytic_type,
        func.max(AnalyticModel.occurred_at).label('last_date')
    ).filter(
        AnalyticModel.sensor_id.in_(sensor_ids)
    ).group_by(AnalyticModel.analytic_type).subquery()

    # Récupérer les analytiques correspondant à la sous-requête
    latest_analytics = db.query(AnalyticModel).join(
        subquery,
        and_(
            AnalyticModel.analytic_type == subquery.c.analytic_type,
            AnalyticModel.occurred_at == subquery.c.last_date
        )
    ).filter(
        AnalyticModel.sensor_id.in_(sensor_ids)
    ).all()

    # Construire le dictionnaire
    latest_by_type = {a.analytic_type: [schemas.AnalyticSchema.model_validate(a)] for a in latest_analytics}
    return latest_by_type

def get_all_analytics_for_cell(db: Session, cell_id: uuid.UUID, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> Dict[AnalyticType, List[schemas.AnalyticSchema]]:
    cell = repositoryCell.get_cell_by_id(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    
    sensor_ids = [sensor.id for sensor in cell.sensors]
    if not sensor_ids:
        return {}
    
    query = db.query(AnalyticModel).filter(
        AnalyticModel.sensor_id.in_(sensor_ids)
    )
    
    if from_date:
        query = query.filter(AnalyticModel.occurred_at >= from_date)
    if to_date:
        query = query.filter(AnalyticModel.occurred_at <= to_date)
    
    analytics = query.all()

    # Grouper par type et convertir en schémas
    analytics_by_type = {}
    for analytic in analytics:
        if analytic.analytic_type not in analytics_by_type:
            analytics_by_type[analytic.analytic_type] = []
        analytics_by_type[analytic.analytic_type].append(schemas.AnalyticSchema.model_validate(analytic))
    
    return analytics_by_type

def update_multiple_cells_settings(db: Session, settings_data: schemas.CellSettingsUpdate):
    """
    Logique métier pour mettre à jour les paramètres de plusieurs cellules.
    """
    # 1. Récupérer les cellules cibles
    cells_to_update = repositoryCell.get_cells_by_ids(db, settings_data.cell_ids)
    
    # 2. Vérifier que toutes les cellules demandées ont été trouvées
    found_ids = {cell.id for cell in cells_to_update}
    requested_ids = set(settings_data.cell_ids)
    
    if not_found_ids := requested_ids - found_ids:
        raise errors.CellsNotFoundError(list(not_found_ids))

    # 3. Préparer le dictionnaire de settings à appliquer
    settings_payload = {
        "daily_update_count": settings_data.daily_update_count,
        "update_times": settings_data.update_times,
        "measurement_frequency": settings_data.measurement_frequency,
    }

    # 4. Mettre à jour le champ 'settings' de chaque cellule
    for cell in cells_to_update:
        if cell.settings is None:
            cell.settings = {}
        cell.settings.update(settings_payload)
        flag_modified(cell, "settings")

    # 5. Appliquer la transaction
    db.commit()


async def _stub_scan_mqtt() -> dict:
    """
    STUB : Simule la détection d'un device IoT via MQTT.
 
    ⚠️  TODO (ticket MQTT) : Remplacer par le vrai scan MQTT.
          Cette fonction doit rester isolée ici pour faciliter le remplacement.
          Elle doit retourner un dict avec les clés : device_id, name, firmware_version.
    """
    await asyncio.sleep(2)  # simule le délai réseau / scan
    device_id = f"CELL-{uuid.uuid4().hex[:6].upper()}"
    return {
        "device_id": device_id,
        "name": f"Cellule {device_id}",
        "firmware_version": "1.0.0",
    }
 
 
async def pair_cell_stream(
    db: Session,
    area_id: Optional[uuid.UUID] = None,
) -> AsyncGenerator[dict, None]:
    """
    Générateur SSE pour le pairing d'une cellule IoT.
 
    Émet dans l'ordre :
      - event:status  step:scanning      — début du scan MQTT
      - event:status  step:device_found  — device détecté (données IoT)
      - event:status  step:creating      — écriture en base
      - event:completed step:completed   — cellule créée, payload complet
    En cas d'erreur à n'importe quelle étape :
      - rollback automatique de la transaction (annule l'insertion en base)
      - event:error step:failed
    """
 
    def _event(event_type: str, step: str, message: str, **extra) -> dict:
        """Helper interne — construit un dict compatible EventSourceResponse."""
        return {
            "event": event_type,
            "data": json.dumps({"step": step, "message": message, **extra}, default=str),
        }
 
    try:
        # ── Étape 1 : scan ────────────────────────────────────────────────
        yield _event("status", "scanning", "Recherche d'un device IoT en cours...")
 
        # ── Étape 2 : détection device (MQTT stub) ────────────────────────
        device_data = await _stub_scan_mqtt()
        yield _event(
            "status",
            "device_found",
            f"Device détecté : {device_data['device_id']}",
            device=device_data,
        )
 
        # ── Étape 3 : création en base ────────────────────────────────────
        yield _event("status", "creating", "Création de la cellule en base de données...")
 
        cell_data = schemas.CellCreate(name=device_data["name"], area_id=area_id)
        
        # On passe commit=False pour garder la transaction ouverte
        cell = create_cell(db, cell_data, commit=False)  # peut lever ParentCellNotFoundError
 
        cell_dto = schemas.CellDTO.from_cell(cell)
        
        # ── Étape 4 : Validation finale de la transaction ─────────────────
        db.commit()
        
        yield _event(
            "completed",
            "completed",
            "Cellule créée avec succès.",
            cell=cell_dto.model_dump(mode="json"),
        )
 
    except Exception as exc:
        # ── Rollback de la transaction en cas d'erreur ────────────────────
        db.rollback()
 
        yield _event("error", "failed", str(exc))
