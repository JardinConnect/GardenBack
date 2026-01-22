from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from services.farm_state.service import get_farm_summary
from services.farm_state.schemas import FarmStateSummary

router = APIRouter()

@router.get(
    "/farm-stats/",
    response_model=FarmStateSummary,
    tags=["Farm State"],
    summary="Get a summary of the farm's state"
)
def read_farm_summary(db: Session = Depends(get_db)):
    """
    Retrieves a summary of the farm's state, including counts of areas,
    cells, sensors, and a breakdown of sensor types.
    """
    return get_farm_summary(db)