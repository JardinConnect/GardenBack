from typing import List, Tuple, Optional, Dict
import uuid
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import services.cell.repository as repository
import services.cell.schemas as schemas
import services.cell.errors as errors
from db.models import Cell as CellModel, Analytic as AnalyticModel, AnalyticType, Area as AreaModel

def create_cell(db: Session, cell_data: schemas.CellCreate) -> schemas.Cell:
    """
    Crée une nouvelle cellule (Cell) dans la base de données.
    """
    if cell_data.area_id:
        area = db.query(AreaModel).filter(AreaModel.id == cell_data.area_id).first()
        if not area:
            raise errors.ParentCellNotFoundError
    return repository.create_cell(db, cell_data)

def delete_cell(db: Session, cell_id: uuid.UUID) -> bool:
    """
    Supprime une cellule de la base de données.
    """
    return repository.delete_cell(db, cell_id)

def get_cell(db: Session, cell_id: uuid.UUID) -> schemas.Cell:
    """
    Récupère une cellule de la base de données.
    """
    cell = repository.get_cell(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    return cell

def get_cells(db: Session) -> List[schemas.Cell]:
    """
    Récupère toutes les cellules de la base de données.
    """
    return repository.get_cells(db)

def get_analytics_for_cell(db: Session, cell_id: uuid.UUID) -> List[AnalyticModel]:
    """
    Récupère la première analytique de chaque type pour tous les capteurs d'une cellule
    en une seule requête pour éviter le problème N+1.
    """
    cell = repository.get_cell(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    
    sensor_ids = [sensor.id for sensor in cell.sensors]
    if not sensor_ids:
        return []

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    return db.query(AnalyticModel).filter(
        AnalyticModel.sensor_id.in_(sensor_ids),
        AnalyticModel.occured_at >= seven_days_ago
    ).order_by(AnalyticModel.occured_at.desc()).all()
