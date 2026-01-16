from sqlalchemy.orm import Session
from typing import Tuple

from db.models import User as UserModel, Area as AreaModel, Cell as CellModel


def get_counts(db: Session) -> Tuple[int, int, int]:
    """
    Compte le nombre total d'utilisateurs, de zones et de cellules dans la base de données.
    """
    total_users = db.query(UserModel).count()
    total_areas = db.query(AreaModel).count()
    total_cells = db.query(CellModel).count()
    return total_users, total_areas, total_cells