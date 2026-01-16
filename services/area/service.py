from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date, timezone
from collections import defaultdict

from . import schemas
from .errors import ParentAreaNotFoundError, AreaNotFoundError
from db.models import Area as AreaModel, Analytic as AnalyticModel, AnalyticType


def create_area(db: Session, area_data: schemas.AreaCreate) -> schemas.Area:
    """
    Crée une nouvelle zone (Area) dans la base de données.

    - Si un `parent_id` est fourni, la nouvelle zone devient un enfant de cette zone parente
      et son niveau hiérarchique est calculé en conséquence.
    - Si aucun `parent_id` n'est fourni, la zone est créée au niveau racine (niveau 1).
    - Lève une `ParentAreaNotFoundError` si le `parent_id` ne correspond à aucune zone existante.
    """
    level = 1
    if area_data.parent_id:
        parent_area = db.query(AreaModel).filter(AreaModel.id == area_data.parent_id).first()
        if not parent_area:
            raise ParentAreaNotFoundError
        level = parent_area.level + 1

    db_area = AreaModel(**area_data.model_dump(), level=level)
    db.add(db_area)
    db.commit()
    db.refresh(db_area)

    # Une nouvelle zone n'a pas encore d'enfants, de cellules ou d'historique analytique.
    # On retourne un schéma Area complet mais vide pour la cohérence de l'API.
    return schemas.Area(
        id=db_area.id,
        name=db_area.name,
        color=db_area.color,
        areas=[],
        cells=[],
        analytics={analytic_type: [] for analytic_type in AnalyticType}
    )


def delete_area(db: Session, area_id: int) -> None:
    """
    Supprime une zone et toutes ses sous-zones de manière récursive.

    - les cellules attachées aux zones supprimées ne sont pas supprimées, mais leur `area_id` est mis à None
    - Lève une `AreaNotFoundError` si l'ID de la zone n'existe pas.
    """
    area_to_delete = db.query(AreaModel).filter(AreaModel.id == area_id).first()
    if not area_to_delete:
        raise AreaNotFoundError

    # 1. Collecter la zone principale et toutes ses descendantes (parcours en largeur)
    areas_to_delete = []
    queue = [area_to_delete]
    while queue:
        current_area = queue.pop(0)
        areas_to_delete.append(current_area)
        # On charge explicitement les enfants pour le parcours
        db.refresh(current_area, ['children'])
        queue.extend(current_area.children)

    # 2. Détacher toutes les cellules de toutes les zones à supprimer
    for area in areas_to_delete:
        # On charge explicitement les cellules pour les détacher
        db.refresh(area, ['cells'])
        for cell in area.cells:
            cell.area_id = None
    
    # Le flush permet d'envoyer les UPDATE (cell.area_id = None) à la DB
    # avant les DELETE, pour éviter les conflits de contraintes.
    db.flush()

    # 3. Supprimer les zones en partant des plus profondes (ordre inverse de la collecte)
    for area in reversed(areas_to_delete):
        db.delete(area)

    db.commit()


def _get_analytics_for_area(db: Session, area: AreaModel) -> List[AnalyticModel]:
    """
    Récupère les analytiques des 7 derniers jours pour tous les capteurs d'une zone
    en une seule requête pour éviter le problème N+1.
    """
    sensor_ids = [sensor.id for cell in area.cells for sensor in cell.sensors]
    if not sensor_ids:
        return []

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    return db.query(AnalyticModel).filter(
        AnalyticModel.sensor_id.in_(sensor_ids),
        AnalyticModel.occured_at >= seven_days_ago
    ).all()


def _calculate_daily_averages(all_analytics: List[AnalyticModel]) -> Dict[AnalyticType, List[schemas.AnalyticSchema]]:
    """
    Calcule les moyennes journalières pour chaque type d'analytique sur les 7 derniers jours.
    Retourne toujours une liste de 7 jours pour chaque type, avec une valeur de 0.0 si aucune donnée n'est disponible.
    """
    # 1. Regrouper les valeurs par (jour, type) pour un calcul efficace
    analytics_by_day_and_type = defaultdict(list)
    for analytic in all_analytics:
        day = analytic.occured_at.date()
        key = (day, analytic.analytic_type)
        analytics_by_day_and_type[key].append(analytic.value)

    # 2. Pour chaque type, calculer les moyennes des 7 derniers jours
    analytics_averages_by_type = {}
    today = datetime.now(timezone.utc).date()
    
    for analytic_type in AnalyticType:
        daily_averages_for_type = []
        for i in range(7):
            current_day = today - timedelta(days=i)
            daily_values = analytics_by_day_and_type.get((current_day, analytic_type))

            average_value = 0.0
            if daily_values:
                average_value = sum(daily_values) / len(daily_values)

            daily_average_analytic = schemas.AnalyticSchema(
                value=round(average_value, 2),
                occured_at=datetime.combine(current_day, datetime.min.time()),
            )
            daily_averages_for_type.append(daily_average_analytic)
        
        analytics_averages_by_type[analytic_type] = daily_averages_for_type
    
    return analytics_averages_by_type


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
    # 1. Récupérer les dernières données analytiques des cellules directes de cette zone (optimisé)
    all_analytics: List[AnalyticModel] = _get_analytics_for_area(db, area)

    # 2. Traiter récursivement les sous-zones et agréger leurs données
    processed_sub_areas: List[schemas.Area] = []
    for sub_area in area.children:
        processed_sub_area_schema, sub_area_analytics = _process_area_recursively(db, sub_area)
        processed_sub_areas.append(processed_sub_area_schema)
        all_analytics.extend(sub_area_analytics)

    # 3. Calculer les moyennes pour la zone actuelle (logique extraite)
    analytics_averages_by_type = _calculate_daily_averages(all_analytics)

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
