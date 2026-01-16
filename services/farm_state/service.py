from sqlalchemy.orm import Session
import logging

from . import schemas, repository
from .errors import FarmStatsError


def get_farm_stats(db: Session) -> schemas.FarmStats:
    """
    Récupère les statistiques de la ferme en appelant la couche repository
    et gère les erreurs potentielles.
    """
    try:
        total_users, total_areas, total_cells = repository.get_counts(db)
        return schemas.FarmStats(
            total_users=total_users,
            total_areas=total_areas,
            total_cells=total_cells,
        )
    except Exception as e:
        # Il est bon de logger l'erreur réelle pour le débogage
        logging.error(f"Erreur lors de la récupération des statistiques de la ferme : {e}")
        # Lève une exception HTTP standard pour le client
        raise FarmStatsError