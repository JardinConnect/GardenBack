from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from .schemas import Area
from . import repository
from db.database import get_db
from services.auth.bearer import JWTBearer

router = APIRouter()

@router.get("/{area_id}", response_model=Area, dependencies=[Depends(JWTBearer())])
def get_area(
    area_id: int = Path(..., title="The ID of the area to get", gt=0),
    db: Session = Depends(get_db),
) -> Area:
    """
    Récupère une zone de jardin spécifique par son ID, avec toute sa hiérarchie.
    """
    return repository.get_area_by_id(db, area_id)