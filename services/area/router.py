from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from .schemas import Area, AreaCreate
from . import service
from .errors import AreaNotFoundError
from db.database import get_db
from services.auth.bearer import JWTBearer

router = APIRouter()

@router.post("/", response_model=Area, status_code=status.HTTP_201_CREATED, dependencies=[Depends(JWTBearer())])
def create_area(
    area_data: AreaCreate,
    db: Session = Depends(get_db),
) -> Area:
    """
    Crée une nouvelle zone de jardin.

    - **name**: Nom de la zone (obligatoire).
    - **color**: Couleur hexadécimale pour l'affichage (ex: "#FF5733").
    - **parent_id**: ID de la zone parente. Si omis, la zone est créée à la racine.
    """
    return service.create_area(db, area_data)


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(JWTBearer())])
def delete_area(
    area_id: int = Path(..., title="The ID of the area to delete", gt=0),
    db: Session = Depends(get_db),
) -> None:
    """
    Supprime une zone de jardin et toutes ses sous-zones.

    - Les sous-zones sont supprimées en cascade.
    - Les cellules qui étaient dans les zones supprimées ne sont PAS supprimées,
      mais sont détachées (leur `area_id` devient `null`).
    """
    service.delete_area(db, area_id)
    return None

@router.get("/{area_id}", response_model=Area, dependencies=[Depends(JWTBearer())])
def get_area(
    area_id: int = Path(..., title="The ID of the area to get", gt=0),
    db: Session = Depends(get_db),
) -> Area:
    """
    Récupère une zone de jardin spécifique par son ID, avec toute sa hiérarchie et les moyennes analytiques.
    """
    area = service.get_area_with_analytics(db, area_id)
    if not area:
        raise AreaNotFoundError
    return area
