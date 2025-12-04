from sqlalchemy.orm import Session
from sqlalchemy import desc
from db.models import Area as AreaModel
from .schemas import Area as AreaSchema, Cell as CellSchema
from .errors import AreaNotFoundError

def get_area_by_id(db: Session, area_id: int) -> AreaSchema:
    """
    Récupère une seule zone par son ID et construit sa hiérarchie.
    """
    area = db.query(AreaModel).filter(AreaModel.id == area_id).first()
    if not area:
        raise AreaNotFoundError
    
    return build_area_schema(area)

def build_area_schema(area: AreaModel) -> AreaSchema:
    """
    Construit récursivement le schéma Pydantic pour une zone donnée.
    """
    cell_schemas = [CellSchema.model_validate(cell) for cell in area.cells] if area.cells else []

    return AreaSchema(
        name=area.name,
        color=area.color,
        areas=[build_area_schema(child) for child in area.children] if area.children else [],
        cells=cell_schemas
    )