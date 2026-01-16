from pydantic import BaseModel


class FarmStats(BaseModel):
    """Schéma pour les statistiques globales de la ferme."""
    total_users: int
    total_areas: int
    total_cells: int