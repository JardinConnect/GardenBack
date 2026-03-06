from fastapi import APIRouter, Depends, Path, status, HTTPException, Query
import uuid
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from .schemas import CellCreate, CellUpdate, CellDTO
from . import service
from .errors import CellNotFoundError, ParentCellNotFoundError
from db.database import get_db
from db.models import User
from services.auth.bearer import JWTBearer
from services.auth.dependencies import get_current_user
from services.audit.service import log_action

router = APIRouter()

@router.get("/", response_model=list[CellDTO], dependencies=[Depends(JWTBearer())])
def get_cells(
    db: Session = Depends(get_db),
) -> list[CellDTO]:
    """
    Récupère toutes les cellules.
    """
    cells = service.get_cells(db)
    return [CellDTO.from_cell(cell) for cell in cells]

@router.get("/{cell_id}", response_model=CellDTO, dependencies=[Depends(JWTBearer())])
def get_cell(
    cell_id: uuid.UUID = Path(..., title="The ID of the cell to get"),
    db: Session = Depends(get_db),
    from_date: Optional[datetime] = Query(None, alias="from", description="Start date for analytics filter (ISO 8601 format)"),
    to_date: Optional[datetime] = Query(None, alias="to", description="End date for analytics filter (ISO 8601 format)"),
) -> CellDTO:
    """
    Récupère une cellule spécifique par son ID.
    Il est possible de filtrer les analytiques retournées par date avec les paramètres `from` et `to`.
    """
    try:
        cell = service.get_cell(db, cell_id, from_date=from_date, to_date=to_date)
        return CellDTO.from_cell(cell)
    except CellNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cell with id {cell_id} not found")

@router.post("/", response_model=CellDTO, status_code=status.HTTP_201_CREATED, dependencies=[Depends(JWTBearer())])
def create_cell(
    cell_data: CellCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CellDTO:
    """
    Crée une nouvelle cellule.
    """
    try:
        cell = service.create_cell(db, cell_data)
        log_action(db, current_user, "create", "cell", cell.id, details={"name": cell.name})
        return CellDTO.from_cell(cell)
    except ParentCellNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/{cell_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(JWTBearer())])
def delete_cell(
    cell_id: uuid.UUID = Path(..., title="The ID of the cell to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Supprime une cellule.
    """
    try:
        service.delete_cell(db, cell_id)
        log_action(db, current_user, "delete", "cell", cell_id)
    except CellNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return None

@router.put("/{cell_id}", response_model=CellDTO, dependencies=[Depends(JWTBearer())])
def update_cell(
    cell_data: CellUpdate,
    cell_id: uuid.UUID = Path(..., title="The ID of the cell to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CellDTO:
    try:
        cell = service.update_cell(db, cell_id, cell_data)
        log_action(db, current_user, "update", "cell", cell_id, details=cell_data.model_dump(exclude_unset=True))
        return CellDTO.from_cell(cell)
    except CellNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
