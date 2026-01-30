from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from services.farm_state.service import get_farm_details
from services.farm_state.schemas import FarmDetails

router = APIRouter()

@router.get(
    "/",
    response_model=FarmDetails,
    summary="Get details about the farm's state"
)
def read_farm_details(
    db: Session = Depends(get_db),
    with_analytics: bool = Query(False, description="Include average analytics for each type.")
):
    """
    Retrieves details of the farm's state, including its name and counts
    of areas, cells, sensors, and users.

    Optionally, it can include the average of all analytics, grouped by type.
    """
    return get_farm_details(db, with_analytics=with_analytics)