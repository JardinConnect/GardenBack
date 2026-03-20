from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from services.farm_state.service import get_farm_details, setup_farm
from services.farm_state.schemas import FarmDetails, OnboardingPayload
from services.farm_state.errors import FarmAlreadyExistsError
from services.user.errors import UserAlreadyExistsError as UserExistsError

# This router will contain protected endpoints for farm statistics.
router = APIRouter()
# This router will contain public endpoints, like the initial farm setup.
public_router = APIRouter()

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


@public_router.post(
    "/setup",
    status_code=status.HTTP_201_CREATED,
    summary="Configuration initiale de la ferme",
    response_model=dict,
)
def setup_farm_endpoint(payload: OnboardingPayload, db: Session = Depends(get_db)):
    """
    Effectue la configuration initiale de la ferme.

    Cette route ne doit être appelée qu'une seule fois et ne nécessite pas d'authentification.
    Elle crée :
    - La ferme elle-même.
    - Le premier utilisateur avec le rôle **SUPERADMIN**.
    - Un ensemble initial de zones (toutes à la racine).

    **Erreurs possibles :**
    - `409 Conflict`: Si la ferme a déjà été configurée.
    - `400 Bad Request`: Si l'email du superadmin fourni existe déjà.
    """
    try:
        return setup_farm(db, payload)
    except FarmAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except UserExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))