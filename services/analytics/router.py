from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

# db
from db.database import get_db
# auth
from services.auth.bearer import JWTBearer
# analytics
from services.analytics import repository
from services.analytics.schemas import (
    AnalyticsFilter, AnalyticResult, AnalyticType
)

router = APIRouter()

@router.get("/analytics/", dependencies=[Depends(JWTBearer())], response_model=AnalyticResult)
async def get_analytics(
    request: AnalyticsFilter = Depends(),
    db: Session = Depends(get_db)
):
    """
    Récupère les analytics filtrés via le repository.
    """

    try:
        analytics_data = repository.get_analytics(db, request)
        return analytics_data


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))