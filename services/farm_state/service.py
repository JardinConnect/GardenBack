from sqlalchemy.orm import Session
from collections import Counter
from typing import Dict

from . import repository
from .schemas import FarmStateSummary, FarmDetails, OnboardingPayload
from .errors import FarmAlreadyExistsError
from db.models import Farm, RoleEnum
from services.user.repository import create_user as create_user_repo
from services.area.service import create_area as create_area_service

def get_farm_details(db: Session, with_analytics: bool = False) -> FarmDetails:
    """
    Calculates and returns details of the entire farm.

    This includes the farm's name, a summary of total counts (areas, cells, sensors, users),
    a breakdown of sensors by type, and optionally the global average for each analytic type.
    """
    # Get farm name from repository
    farm = repository.get_farm(db)

    # Get summary counts from repository
    counts = repository.get_summary_counts(db)

    # Count sensors by type from repository
    sensor_types_query = repository.get_all_sensor_types(db)
    sensor_type_counts = Counter(st[0] for st in sensor_types_query)

    summary = FarmStateSummary(
        total_users=counts["total_users"],
        total_areas=counts["total_areas"],
        total_cells=counts["total_cells"],
        total_sensors=counts["total_sensors"],
        sensor_types=dict(sensor_type_counts),
    )

    # Calculate average analytics if requested, using repository
    average_analytics = None
    if with_analytics:
        avg_query = repository.get_average_analytics_by_type(db)
        average_analytics = {
            analytic_type.value: round(avg_value, 2)
            for analytic_type, avg_value in avg_query if avg_value is not None
        }

    return FarmDetails(
        name=farm.name if farm else "JardinConnect",
        address=farm.address if farm else None,
        zip_code=farm.zip_code if farm else None,
        city=farm.city if farm else None,
        phone_number=farm.phone_number if farm else None,
        summary=summary,
        average_analytics=average_analytics,
    )

def setup_farm(db: Session, payload: OnboardingPayload) -> Dict[str, str]:
    """
    Effectue la configuration initiale de la ferme.
    Crée la ferme, le premier utilisateur SUPERADMIN, et les zones racines.
    """
    # 1. Vérifier si la ferme existe déjà
    if repository.get_farm(db):
        raise FarmAlreadyExistsError()

    try:
        # 2. Créer la ferme
        farm = Farm(**payload.farm.model_dump())
        db.add(farm)

        # 3. Créer l'utilisateur SUPERADMIN
        user_data = payload.user
        user_data.role = RoleEnum.SUPERADMIN  # Forcer le rôle pour la sécurité
        admin_user = create_user_repo(db, user=user_data)

        # 4. Créer les zones initiales comme zones racines
        for area_data in payload.areas:
            create_area_service(db, area_data=area_data, current_user=admin_user)

        return {"message": "Ferme configurée avec succès."}
    except Exception as e:
        # Note : les services appelés (create_user, create_area) committent individuellement.
        # Une gestion transactionnelle plus poussée nécessiterait une refonte de ces services.
        raise e