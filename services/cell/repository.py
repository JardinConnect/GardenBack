from sqlalchemy.orm import Session
import uuid
from db.models import Cell as CellModel
from .schemas import Cell as CellSchema
from .errors import CellNotFoundError

def get_cell_by_id(db: Session, cell_id: uuid.UUID) -> CellSchema:
    """
    Récupère une seule cellule par son ID.
    """
    cell = db.query(CellModel).filter(CellModel.id == cell_id).first()
    if not cell:
        raise CellNotFoundError
    
    return CellSchema.model_validate(cell)

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

