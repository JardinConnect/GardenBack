from typing import List, Dict
import uuid
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
import services.cell.repository as repositoryCell
import services.area.repository as repositoryArea
import services.cell.schemas as schemas
import services.cell.errors as errors
from db.models import Analytic as AnalyticModel, AnalyticType

def create_cell(db: Session, cell_data: schemas.CellCreate) -> schemas.Cell:
    """
    Crée une nouvelle cellule (Cell) dans la base de données.
    """
    if cell_data.area_id:
        area = repositoryArea.get_by_id(db, cell_data.area_id)
        if not area:
            raise errors.ParentCellNotFoundError
    cell = repositoryCell.create_cell(db, cell_data)
    
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

def get_cell(db: Session, cell_id: uuid.UUID) -> schemas.Cell:
    """
    Récupère une cellule de la base de données.
    """
    cell = repositoryCell.get_cell_by_id(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    analytics = get_all_analytics_for_cell(db, cell_id)
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

def get_all_analytics_for_cell(db: Session, cell_id: uuid.UUID) -> Dict[AnalyticType, List[schemas.AnalyticSchema]]:
    cell = repositoryCell.get_cell_by_id(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    
    sensor_ids = [sensor.id for sensor in cell.sensors]
    if not sensor_ids:
        return {}
    
    analytics = db.query(AnalyticModel).filter(
        AnalyticModel.sensor_id.in_(sensor_ids)
    ).all()
    
    # Grouper par type et convertir en schémas
    analytics_by_type = {}
    for analytic in analytics:
        if analytic.analytic_type not in analytics_by_type:
            analytics_by_type[analytic.analytic_type] = []
        analytics_by_type[analytic.analytic_type].append(schemas.AnalyticSchema.model_validate(analytic))
    
    return analytics_by_type