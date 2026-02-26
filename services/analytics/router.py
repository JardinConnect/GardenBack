from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# db
from db.database import get_db
# auth
from services.auth.bearer import JWTBearer
# analytics
from services.analytics import repository
from services.analytics.schemas import (
    AnalyticsFilter, PaginatedAnalyticResult, AnalyticCreate, AnalyticSchema
)

router = APIRouter()

@router.get("/analytics/", dependencies=[Depends(JWTBearer())], response_model=PaginatedAnalyticResult)
async def get_analytics(
    request: AnalyticsFilter = Depends(),
    db: Session = Depends(get_db)
):
    """
    Récupère les analytics filtrés via le repository.
    """
    try:
        return repository.get_analytics(db, request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analytics/", response_model=AnalyticSchema, status_code=201)
async def create_analytic(
    analytic_input: AnalyticCreate,
    db: Session = Depends(get_db)
):
    """
    Crée une nouvelle entrée d'analytique à partir des données d'un capteur.
    """
    try:
        created_analytic = repository.create_analytic(db, analytic_input)
        return created_analytic
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Une erreur inattendue est survenue: {e}")