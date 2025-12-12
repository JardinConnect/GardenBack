from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date, timezone

from . import schemas
from db.models import Area as AreaModel, Analytic as AnalyticModel, AnalyticType


def _process_area_recursively(db: Session, area: AreaModel) -> Tuple[schemas.Area, List[AnalyticModel]]:
    """
    Traite récursivement une zone et ses sous-zones pour calculer les moyennes analytiques.

    Cette fonction effectue un parcours de l'arbre des zones. Pour chaque zone, elle :
    1. Récupère les dernières données analytiques des capteurs de ses propres cellules.
    2. S'appelle récursivement sur toutes les sous-zones et collecte leurs résultats.
    3. Agrège toutes les données analytiques (les siennes et celles de tous ses descendants).
    4. Calcule la moyenne des analytiques pour les données agrégées.
    5. Construit le schéma Pydantic pour la zone actuelle, en y incluant la moyenne calculée.

    Retourne un tuple contenant :
    - L'objet schéma Area traité.
    - Une liste de tous les modèles Analytic trouvés dans cette zone et ses sous-zones.
    """
    # 1. Récupérer les dernières données analytiques des cellules directes de cette zone
    all_analytics: List[AnalyticModel] = []
    for cell in area.cells:
        for sensor in cell.sensors:
            # On ne prend que les analytiques des 7 derniers jours
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            analytics_for_sensor = db.query(AnalyticModel)\
                .filter(AnalyticModel.sensor_id == sensor.id, AnalyticModel.occured_at >= seven_days_ago)\
                .all()
            all_analytics.extend(analytics_for_sensor)

    # 2. Traiter récursivement les sous-zones et agréger leurs données
    processed_sub_areas: List[schemas.Area] = []
    # On itère sur `area.children` qui est la relation définie dans le modèle SQLAlchemy
    for sub_area in area.children:
        processed_sub_area_schema, sub_area_analytics = _process_area_recursively(db, sub_area)
        processed_sub_areas.append(processed_sub_area_schema)
        all_analytics.extend(sub_area_analytics)

    # 3. Calculer les moyennes pour la zone actuelle (incluant tous les enfants)
    analytics_averages_by_type: dict[AnalyticType, list[schemas.AnalyticSchema]] = {analytic_type: [] for analytic_type in AnalyticType}
    if all_analytics:
        # Regrouper les analytiques par jour
        analytics_by_day_and_type: dict[tuple[date, AnalyticType], list[float]] = {}
        for analytic in all_analytics:
            day = analytic.occured_at.date()
            key = (day, analytic.analytic_type)
            analytics_by_day_and_type.setdefault(key, []).append(analytic.value)

        # Pour chaque type d'analytique, calculer les moyennes des 7 derniers jours
        for analytic_type in AnalyticType:
            daily_averages_for_type = []
            today = datetime.now(timezone.utc).date()
            for i in range(7):
                current_day = today - timedelta(days=i)
                daily_values = analytics_by_day_and_type.get((current_day, analytic_type))

                average_value = 0.0
                if daily_values:
                    average_value = sum(daily_values) / len(daily_values)

                daily_average_analytic = schemas.AnalyticSchema(
                    value=average_value,
                    occured_at=datetime.combine(current_day, datetime.min.time()),
                )
                daily_averages_for_type.append(daily_average_analytic)
            
            # Ajouter la liste des 7 moyennes pour ce type au dictionnaire principal
            analytics_averages_by_type[analytic_type] = daily_averages_for_type

    # 4. Construire l'objet schéma Pydantic final pour cette zone
    area_schema = schemas.Area(
        id=area.id,
        name=area.name,
        color=area.color,
        areas=processed_sub_areas,
        cells=[schemas.Cell.model_validate(cell) for cell in area.cells],
        analytics=analytics_averages_by_type
    )

    return area_schema, all_analytics


def get_area_with_analytics(db: Session, area_id: int) -> Optional[schemas.Area]:
    """
    Fonction principale pour récupérer une zone par son ID, enrichie avec les moyennes analytiques.
    """
    area_db = db.query(AreaModel).filter(AreaModel.id == area_id).first()
    if not area_db:
        return None

    processed_area, _ = _process_area_recursively(db, area_db)
    return processed_area
