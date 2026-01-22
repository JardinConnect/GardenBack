from sqlalchemy.orm import Session
from collections import Counter

from db.models import Area, Cell, Sensor
from db.models import User as UserModel
from .schemas import FarmStateSummary


def get_farm_summary(db: Session) -> FarmStateSummary:
    """
    Calculates and returns a summary of the entire farm state.

    This includes the total count of areas, cells, and sensors, and a
    breakdown of sensors by their type.
    """
    total_areas = db.query(Area).count()
    total_cells = db.query(Cell).count()
    total_sensors = db.query(Sensor).count()
    total_users = db.query(UserModel).count()

    # Count sensors by type
    sensor_types_query = db.query(Sensor.sensor_type).all()
    sensor_type_counts = Counter(st[0] for st in sensor_types_query)


    return FarmStateSummary(
        total_users=total_users,
        total_areas=total_areas,
        total_cells=total_cells,
        total_sensors=total_sensors,
        sensor_types=dict(sensor_type_counts),
    )