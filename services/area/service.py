from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

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
            latest_analytic = db.query(AnalyticModel)\
                .filter(AnalyticModel.sensor_id == sensor.id)\
                .order_by(desc(AnalyticModel.occured_at))\
                .first()
            if latest_analytic:
                all_analytics.append(latest_analytic)

    # 2. Traiter récursivement les sous-zones et agréger leurs données
    processed_sub_areas: List[schemas.Area] = []
    # On itère sur `area.children` qui est la relation définie dans le modèle SQLAlchemy
    for sub_area in area.children:
        processed_sub_area_schema, sub_area_analytics = _process_area_recursively(db, sub_area)
        processed_sub_areas.append(processed_sub_area_schema)
        all_analytics.extend(sub_area_analytics)

    # 3. Calculer les moyennes pour la zone actuelle (incluant tous les enfants)
    analytics_average = None
    if all_analytics:
        air_temps = [data.value for data in all_analytics if data.analytic_type == AnalyticType.AIR_TEMPERATURE]
        soil_temps = [data.value for data in all_analytics if data.analytic_type == AnalyticType.SOIL_TEMPERATURE]
        air_humids = [data.value for data in all_analytics if data.analytic_type == AnalyticType.AIR_HUMIDITY]
        soil_humids = [data.value for data in all_analytics if data.analytic_type == AnalyticType.SOIL_HUMIDITY]
        lights = [data.value for data in all_analytics if data.analytic_type == AnalyticType.LIGHT]

        analytics_average = schemas.AnalyticsAverage(
            air_temperature=sum(air_temps) / len(air_temps) if air_temps else None,
            soil_temperature=sum(soil_temps) / len(soil_temps) if soil_temps else None,
            air_humidity=sum(air_humids) / len(air_humids) if air_humids else None,
            soil_humidity=sum(soil_humids) / len(soil_humids) if soil_humids else None,
            light=sum(lights) / len(lights) if lights else None,
        )

    # 4. Construire l'objet schéma Pydantic final pour cette zone
    # Utiliser model_validate pour convertir l'objet ORM en modèle Pydantic
    area_schema = schemas.Area.model_validate(area)
    area_schema.areas = processed_sub_areas
    area_schema.analytics_average = analytics_average

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
