from fastapi import APIRouter, Depends, Path, status, HTTPException, Query, Response
import uuid
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from .schemas import CellCreate, CellUpdate, CellDTO, CellSettingsUpdate
from . import service
from .errors import CellNotFoundError, ParentCellNotFoundError, CellsNotFoundError
from db.database import get_db
from db.models import User, RoleEnum
from services.auth.dependencies import get_current_user
from services.audit.service import log_action

router = APIRouter()

@router.get("/", response_model=list[CellDTO])
def get_cells(
    db: Session = Depends(get_db),
) -> list[CellDTO]:
    """
    Récupère toutes les cellules.
    """
    cells = service.get_cells(db)
    return [CellDTO.from_cell(cell) for cell in cells]

@router.get("/{cell_id}", response_model=CellDTO)
def get_cell(
    cell_id: uuid.UUID = Path(..., title="The ID of the cell to get"),
    db: Session = Depends(get_db),
    from_date: Optional[datetime] = Query(None, alias="from", description="Start date for analytics filter (ISO 8601 format)"),
    to_date: Optional[datetime] = Query(None, alias="to", description="End date for analytics filter (ISO 8601 format)"),
    current_user: User = Depends(get_current_user),
) -> CellDTO:
    """
    Récupère une cellule spécifique par son ID.
    Il est possible de filtrer les analytiques retournées par date avec les paramètres `from` et `to`.
    """
    try:
        cell = service.get_cell(db, cell_id, from_date=from_date, to_date=to_date)
        # Inclure les settings uniquement si l'utilisateur est un admin
        include_settings = current_user.role in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN]
        return CellDTO.from_cell(cell, include_settings=include_settings)
    except CellNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cell with id {cell_id} not found")

@router.post("/", response_model=CellDTO, status_code=status.HTTP_201_CREATED)
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

@router.delete("/{cell_id}", status_code=status.HTTP_204_NO_CONTENT)
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

@router.put(
    "/settings",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Accès refusé"},
        status.HTTP_404_NOT_FOUND: {"description": "Une ou plusieurs cellules non trouvées"},
    }
)
def update_cells_settings(
    settings_data: CellSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Met à jour les paramètres de configuration pour une ou plusieurs cellules.

    - **daily_update_count**: Le nombre de fois où la cellule va se mettre à jour (par jour).
    - **update_times**: Liste d'horaires des mises à jour (ex: `["13:55", "22:15"]`).
    - **measurement_frequency**: La fréquence de relevé des capteurs de la cellule (en secondes).
    
    *Nécessite des droits d'administrateur.*
    """
    if current_user.role not in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un administrateur peut modifier les paramètres des cellules."
        )

    try:
        service.update_multiple_cells_settings(db, settings_data)
    except CellsNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    log_action(
        db=db,
        user=current_user,
        action="update",
        resource_type="cell",
        entity_id=None,  # Opération en masse
        details={"action": "bulk_settings_update", "cell_ids": [str(cid) for cid in settings_data.cell_ids]}
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.put("/{cell_id}", response_model=CellDTO)
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
