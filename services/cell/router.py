from fastapi import APIRouter, Depends, Path, status, HTTPException
import uuid
from sqlalchemy.orm import Session

from .schemas import Cell, CellCreate
from . import service
from .errors import CellNotFoundError, ParentCellNotFoundError
from db.database import get_db
from services.auth.bearer import JWTBearer

router = APIRouter()

@router.get("/", response_model=list[Cell], dependencies=[Depends(JWTBearer())])
def get_cells(
    db: Session = Depends(get_db),
) -> list[Cell]:
    """
    Récupère toutes les cellules.
    """
    return service.get_cells(db)

@router.get("/{cell_id}", response_model=Cell, dependencies=[Depends(JWTBearer())])
def get_cell(
    cell_id: uuid.UUID = Path(..., title="The ID of the cell to get"),
    db: Session = Depends(get_db),
) -> Cell:
    """
    Récupère une cellule spécifique par son ID.
    """
    try:
        return service.get_cell(db, cell_id)
    except CellNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cell with id {cell_id} not found")

@router.post("/", response_model=Cell, status_code=status.HTTP_201_CREATED, dependencies=[Depends(JWTBearer())])
def create_cell(
    cell_data: CellCreate,
    db: Session = Depends(get_db),
) -> Cell:
    """
    Crée une nouvelle cellule.
    """
    try:
        return service.create_cell(db, cell_data)
    except ParentCellNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/{cell_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(JWTBearer())])
def delete_cell(
    cell_id: uuid.UUID = Path(..., title="The ID of the cell to delete"),
    db: Session = Depends(get_db),
) -> None:
    """
    Supprime une cellule.
    """
    try:
        service.delete_cell(db, cell_id)
    except CellNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return None


