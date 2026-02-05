from sqlalchemy.orm import Session
from typing import List
import uuid
from db.models import Cell as CellModel
from .schemas import Cell as CellSchema, CellUpdate
from .errors import CellNotFoundError

def get_cell_by_id(db: Session, cell_id: uuid.UUID) -> CellSchema:
    """
    Récupère une seule cellule par son ID.
    """
    cell = db.query(CellModel).filter(CellModel.id == cell_id).first()
    if not cell:
        raise CellNotFoundError
    
    return CellSchema.model_validate(cell)

def get_cells(db: Session) -> List[CellSchema]:
    """
    Récupère toutes les cellules.
    """
    cells = db.query(CellModel).all()
    if not cells:
        raise CellNotFoundError
    
    return [CellSchema.model_validate(cell) for cell in cells]

def create_cell(db: Session, cell_data: CellSchema) -> CellSchema:
    """
    Crée une nouvelle cellule.
    """
    cell = CellModel(**cell_data.model_dump())
    db.add(cell)
    db.commit()
    db.refresh(cell)
    
    return CellSchema.model_validate(cell)

def delete_cell(db: Session, cell_id: uuid.UUID) -> None:
    """
    Supprime une cellule.
    """
    cell = db.query(CellModel).filter(CellModel.id == cell_id).first()
    if not cell:
        raise CellNotFoundError
    
    db.delete(cell)
    db.commit()
    
    return None

def update_cell(db: Session, cell_id: uuid.UUID, cell_data: CellUpdate) -> CellSchema:
    cell = db.query(CellModel).filter(CellModel.id == cell_id).first()
    if not cell:
        raise CellNotFoundError
    
    # Update all fields from the complete data
    for field, value in cell_data.model_dump(exclude={'sensors', 'analytics'}).items():
        setattr(cell, field, value)
    
    db.commit()
    db.refresh(cell)
    
    return CellSchema.model_validate(cell)
