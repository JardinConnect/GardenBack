from typing import List, Tuple, Optional, Dict
import uuid
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from . import schemas, repository
from .errors import ParentAreaNotFoundError, AreaNotFoundError
from db.models import Area as AreaModel, Analytic as AnalyticModel, AnalyticType


def create_area(db: Session, area_data: schemas.AreaCreate) -> schemas.Area:
    """
    Crée une nouvelle zone (Area).
    La logique métier est de valider le parent et de calculer le niveau.
    L'enregistrement en base de données est délégué au repository.
    """
    level = 1
    if area_data.parent_id:
        parent_area = repository.get_by_id(db, area_data.parent_id)
        if not parent_area:
            raise ParentAreaNotFoundError
        level = repository.get_area_level(db, parent_area.id) + 1

    db_area_model = AreaModel(**area_data.model_dump())
    
    # Délégation de la création au repository
    created_area = repository.create(db, db_area_model)

    # Une nouvelle zone n'a pas encore d'enfants, de cellules ou d'historique analytique.
    # On retourne un schéma Area complet mais vide pour la cohérence de l'API.
    return schemas.Area(
        id=created_area.id,
        name=created_area.name,
        color=created_area.color,
        is_tracked=created_area.is_tracked,
        level=level,
        areas=[],
        cells=[],
        analytics={analytic_type: [] for analytic_type in AnalyticType}
    )


def update_area(db: Session, area_id: uuid.UUID, area_data: schemas.AreaUpdate) -> schemas.Area:
    """
    Met à jour une zone.
    Valide les changements (notamment le parent_id pour éviter les cycles)
    et délègue la persistance au repository.
    """
    # 1. Récupérer l'objet à mettre à jour
    area_to_update = repository.get_by_id(db, area_id)
    if not area_to_update:
        raise AreaNotFoundError()

    # 2. Obtenir les données de mise à jour, en excluant les champs non définis
    update_data = area_data.model_dump(exclude_unset=True)

    # 3. Gérer la validation complexe du changement de parent
    if "parent_id" in update_data:
        new_parent_id = update_data["parent_id"]

        # Un objet ne peut pas être son propre parent
        if new_parent_id == area_id:
            raise ValueError("An area cannot be its own parent.")

        if new_parent_id is not None:
            # Vérifier que le nouveau parent existe
            if not repository.get_by_id(db, new_parent_id):
                raise ParentAreaNotFoundError("The new parent area was not found.")

            # Vérifier la dépendance cyclique : on ne peut pas déplacer une zone dans un de ses enfants
            descendant_ids = repository.get_descendant_area_ids(db, area_id)
            if new_parent_id in descendant_ids:
                raise ValueError("Cannot move an area into one of its own descendants (cyclic dependency).")

    # 4. Appliquer les mises à jour sur le modèle SQLAlchemy
    for key, value in update_data.items():
        setattr(area_to_update, key, value)

    # 5. Persister les changements et retourner le schéma mis à jour
    repository.update(db, area_to_update)
    return get_area_with_analytics(db, area_id)


def delete_area(db: Session, area_id: uuid.UUID) -> bool:
    """
    Supprime une zone et toutes ses sous-zones.
    Vérifie d'abord l'existence de la zone, puis délègue la suppression au repository.
    """
    area_to_delete = repository.get_by_id(db, area_id)
    if not area_to_delete:
        raise AreaNotFoundError

    repository.delete_hierarchy(db, area_to_delete)
    return True


# --- Fonctions de logique métier (privées, pas d'accès DB) ---

def _calculate_daily_averages(all_analytics: List[AnalyticModel]) -> Dict[AnalyticType, List[schemas.AnalyticSchema]]:
    """
    Calcule les moyennes journalières pour chaque type d'analytique sur les 7 derniers jours.
    Retourne toujours une liste de 7 jours pour chaque type, avec une valeur de 0.0 si aucune donnée n'est disponible.
    """
    analytics_by_day_and_type = defaultdict(list)
    for analytic in all_analytics:
        day = analytic.occurred_at.date()
        key = (day, analytic.analytic_type)
        analytics_by_day_and_type[key].append(analytic.value)

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
                occurred_at=datetime.combine(current_day, datetime.min.time()),
            )
            daily_averages_for_type.append(daily_average_analytic)
        
        analytics_averages_by_type[analytic_type] = daily_averages_for_type
    
    return analytics_averages_by_type


def _build_area_schema_recursively(
    area: AreaModel, 
    level: int, 
    analytics_by_area: Dict[uuid.UUID, List[AnalyticModel]]
) -> Tuple[schemas.Area, List[AnalyticModel]]:
    """
    Construit récursivement le schéma Pydantic pour une zone et ses sous-zones
    en utilisant des données analytiques pré-chargées.
    """
    direct_analytics: List[AnalyticModel] = analytics_by_area.get(area.id, [])
    all_analytics = list(direct_analytics)

    processed_sub_areas: List[schemas.Area] = []
    for sub_area in area.children:
        processed_sub_area_schema, sub_area_analytics = _build_area_schema_recursively(
            sub_area, level + 1, analytics_by_area
        )
        processed_sub_areas.append(processed_sub_area_schema)
        all_analytics.extend(sub_area_analytics)

    analytics_averages_by_type = _calculate_daily_averages(all_analytics)

    area_schema = schemas.Area(
        id=area.id,
        name=area.name,
        color=area.color,
        is_tracked=area.is_tracked,
        level=level,
        areas=processed_sub_areas,
        cells=[schemas.Cell.model_validate(cell) for cell in area.cells],
        analytics=analytics_averages_by_type
    )

    return area_schema, all_analytics

def get_all_areas_with_analytics(db: Session) -> List[schemas.Area]:
    """
    Récupère toutes les zones racines et leur hiérarchie complète
    avec les analytiques agrégées, de manière optimisée.
    """
    # 1. Récupérer toutes les zones et leurs relations via le repository.
    all_areas = repository.get_all_areas_with_relations(db)
    if not all_areas:
        return []

    # 2. Créer des dictionnaires pour un accès rapide et identifier les racines (logique métier)
    areas_by_id = {area.id: area for area in all_areas}
    root_areas = [area for area in all_areas if area.parent_id is None]
    
    # 3. Récupérer toutes les analytiques pertinentes en une seule requête via le repository
    all_area_ids = list(areas_by_id.keys())
    analytics_by_area = repository.get_analytics_for_areas(db, all_area_ids)

    # 4. Construire l'arborescence pour chaque zone racine (logique métier)
    processed_areas = []
    for root_area in root_areas:
        # Le niveau de la racine est toujours 1
        processed_area, _ = _build_area_schema_recursively(root_area, 1, analytics_by_area)
        processed_areas.append(processed_area)
        
    return processed_areas

def get_area_with_analytics(db: Session, area_id: uuid.UUID) -> Optional[schemas.Area]:
    """
    Récupère une zone par son ID et sa hiérarchie complète avec les analytiques
    agrégées, de manière optimisée.
    """
    # 1. Récupérer tous les IDs de la sous-arborescence via le repository
    descendant_ids = repository.get_descendant_area_ids(db, area_id)
    if not descendant_ids:
        return None  # La zone n'existe pas

    # 2. Charger tous les objets Area de la sous-arborescence via le repository
    all_areas_in_subtree = repository.get_areas_by_ids_with_relations(db, descendant_ids)
    
    areas_by_id = {area.id: area for area in all_areas_in_subtree}
    area_db = areas_by_id.get(area_id)
    
    if not area_db:
        return None

    # 3. Récupérer toutes les analytiques pour cette sous-arborescence via le repository
    analytics_by_area = repository.get_analytics_for_areas(db, descendant_ids)

    # 4. Calculer le niveau de départ de la zone demandée via le repository
    start_level = repository.get_area_level(db, area_db.id)

    # 5. Construire l'arborescence de schémas récursivement (logique métier)
    processed_area, _ = _build_area_schema_recursively(area_db, start_level, analytics_by_area)
    return processed_area
