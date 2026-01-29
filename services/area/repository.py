from typing import List, Dict, Optional
from sqlalchemy.orm import Session, aliased, selectinload
from sqlalchemy import select, literal
import uuid
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from db.models import Area as AreaModel, Analytic as AnalyticModel, Cell as CellModel, Sensor as SensorModel


# --- Read Operations ---

def get_by_id(db: Session, area_id: uuid.UUID) -> Optional[AreaModel]:
    """Récupère une zone par son ID."""
    return db.query(AreaModel).filter(AreaModel.id == area_id).first()


def get_all_areas_with_relations(db: Session) -> List[AreaModel]:
    """
    Récupère toutes les zones, en pré-chargeant leurs cellules et enfants.
    SQLAlchemy reconstituera les relations en mémoire.
    """
    return db.query(AreaModel).options(
        selectinload(AreaModel.children),
        selectinload(AreaModel.cells)
    ).all()


def get_areas_by_ids_with_relations(db: Session, area_ids: List[uuid.UUID]) -> List[AreaModel]:
    """
    Charge tous les objets Area pour une liste d'IDs, en pré-chargeant leurs cellules
    et enfants pour éviter des requêtes ultérieures.
    """
    return db.query(AreaModel).options(
        selectinload(AreaModel.children),
        selectinload(AreaModel.cells)
    ).filter(AreaModel.id.in_(area_ids)).all()


def get_area_level(db: Session, area_id: uuid.UUID) -> int:
    """
    Calcule le niveau d'une zone en utilisant une CTE récursive SQL pour l'efficacité.
    """
    area_alias = aliased(AreaModel)
    cte = select(
        AreaModel.id.label('id'),
        literal(1).label('level')
    ).where(AreaModel.parent_id.is_(None)).cte(name='area_levels', recursive=True)
    cte_alias = aliased(cte)
    cte = cte.union_all(
        select(
            area_alias.id,
            (cte_alias.c.level + 1)
        ).where(area_alias.parent_id == cte_alias.c.id)
    )
    level_query = select(cte.c.level).where(cte.c.id == area_id)
    level = db.execute(level_query).scalar_one()
    return level


def get_descendant_area_ids(db: Session, area_id: uuid.UUID) -> List[uuid.UUID]:
    """
    Récupère l'ID de la zone donnée et tous ses descendants en utilisant une CTE récursive.
    """
    area_alias = aliased(AreaModel)
    cte = select(AreaModel.id).where(AreaModel.id == area_id).cte(name='area_hierarchy', recursive=True)
    cte_alias = aliased(cte)
    cte = cte.union_all(
        select(area_alias.id).where(area_alias.parent_id == cte_alias.c.id)
    )
    query = select(cte.c.id)
    result = db.execute(query).scalars().all()
    return result


def get_analytics_for_areas(db: Session, area_ids: List[uuid.UUID]) -> Dict[uuid.UUID, List[AnalyticModel]]:
    """
    Récupère les analytiques des 7 derniers jours pour une liste de zones
    et les regroupe par area_id pour un accès rapide.
    """
    if not area_ids:
        return {}

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    query = (
        select(CellModel.area_id, AnalyticModel)
        .join(CellModel.sensors)
        .join(SensorModel.analytics)
        .where(CellModel.area_id.in_(area_ids))
        .where(AnalyticModel.occured_at >= seven_days_ago)
    )
    results = db.execute(query).all()
    analytics_by_area = defaultdict(list)
    for area_id, analytic in results:
        analytics_by_area[area_id].append(analytic)
    return analytics_by_area


# --- Write Operations ---

def create(db: Session, area: AreaModel) -> AreaModel:
    """Ajoute, commit et refresh une nouvelle zone."""
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def delete_hierarchy(db: Session, area_to_delete: AreaModel):
    """
    Supprime une zone et toute sa hiérarchie, en détachant les cellules.
    """
    areas_to_delete = []
    queue = [area_to_delete]
    while queue:
        current_area = queue.pop(0)
        areas_to_delete.append(current_area)
        db.refresh(current_area, ['children'])
        queue.extend(current_area.children)

    for area in areas_to_delete:
        db.refresh(area, ['cells'])
        for cell in area.cells:
            cell.area_id = None
    
    db.flush()

    for area in reversed(areas_to_delete):
        db.delete(area)

    db.commit()


def update(db: Session, area: AreaModel) -> AreaModel:
    """Commit et refresh une zone mise à jour."""
    db.commit()
    db.refresh(area)
    return area