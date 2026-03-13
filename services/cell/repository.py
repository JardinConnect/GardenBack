from sqlalchemy.orm import Session, joinedload
from typing import List
import uuid
from datetime import datetime, UTC
from db.models import Cell as CellModel, Sensor
from .schemas import Cell as CellSchema, CellUpdate, CellCreate
from .errors import CellNotFoundError
from services.area.service import get_full_location_path_for_cell

def get_cell_by_id(db: Session, cell_id: uuid.UUID) -> CellSchema:
    """
    Récupère une seule cellule par son ID, si elle n'est pas "soft-deleted".
    """
    cell = db.query(CellModel).options(joinedload(CellModel.area)).filter(
        CellModel.id == cell_id, CellModel.deleted_at.is_(None)).first()
    if not cell:
        raise CellNotFoundError
    
    cell_schema = CellSchema.model_validate(cell)
    cell_schema.location = get_full_location_path_for_cell(cell)
    return cell_schema

def get_cells(db: Session) -> List[CellSchema]:
    """
    Récupère toutes les cellules non "soft-deleted".
    """
    cells = db.query(CellModel).options(joinedload(CellModel.area)).filter(CellModel.deleted_at.is_(None)).all()
    
    cell_schemas = []
    for cell in cells:
        cell_schema = CellSchema.model_validate(cell)
        cell_schema.location = get_full_location_path_for_cell(cell)
        cell_schemas.append(cell_schema)

    return cell_schemas

def create_cell(db: Session, cell_data: CellCreate) -> CellSchema:
    """
    Crée une nouvelle cellule.
    """
    cell = CellModel(**cell_data.model_dump())
    db.add(cell)
    db.commit()
    
    return get_cell_by_id(db, cell.id)

def delete_cell(db: Session, cell_id: uuid.UUID) -> None:
    """
    Effectue un "soft delete" sur une cellule et ses capteurs associés.
    """
    cell = db.query(CellModel).filter(CellModel.id == cell_id, CellModel.deleted_at.is_(None)).first()
    if not cell:
        raise CellNotFoundError
    
    now = datetime.now(UTC)
    
    # Soft delete les capteurs associés
    db.query(Sensor).filter(Sensor.cell_id == cell.id, Sensor.deleted_at.is_(None)).update({"deleted_at": now}, synchronize_session=False)
    
    cell.deleted_at = now
    db.commit()
    
    return None

def update_cell(db: Session, cell_id: uuid.UUID, cell_data: CellUpdate) -> CellSchema:
    cell = db.query(CellModel).filter(CellModel.id == cell_id, CellModel.deleted_at.is_(None)).first()
    if not cell:
        raise CellNotFoundError
    
    # Update only the fields that were explicitly set in the request data.
    # This prevents accidentally setting non-nullable fields to None.
    for field, value in cell_data.model_dump(exclude_unset=True).items():
        setattr(cell, field, value)
    
    db.commit()
    
    return get_cell_by_id(db, cell.id)

def get_cells_by_ids(db: Session, cell_ids: List[uuid.UUID]) -> List[CellModel]:
    """Récupère une liste de cellules par leurs IDs, si elles ne sont pas "soft-deleted"."""
    if not cell_ids:
        return []
    return db.query(CellModel).filter(CellModel.id.in_(cell_ids), CellModel.deleted_at.is_(None)).all()
