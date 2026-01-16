from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from . import service
from .schemas import FarmStats
from db.database import get_db
from services.auth.bearer import JWTBearer

router = APIRouter()


@router.get("/", response_model=FarmStats, dependencies=[Depends(JWTBearer())])
def read_farm_stats(db: Session = Depends(get_db)) -> FarmStats:
    """
    Récupère les statistiques globales de la ferme :
    - Nombre total d'utilisateurs
    - Nombre total d'espaces (areas)
    - Nombre total de cellules (cells)
    """
    return service.get_farm_stats(db)