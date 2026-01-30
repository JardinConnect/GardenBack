from sqlalchemy.orm import Session
from collections import Counter

from . import repository
from .schemas import FarmStateSummary, FarmDetails

def get_farm_details(db: Session, with_analytics: bool = False) -> FarmDetails:
    """
    Calculates and returns details of the entire farm.

    This includes the farm's name, a summary of total counts (areas, cells, sensors, users),
    a breakdown of sensors by type, and optionally the global average for each analytic type.
    """
    # Get farm name from repository
    farm = repository.get_farm(db)
    farm_name = farm.name if farm else "JardinConnect"  # Fallback name

    # Get summary counts from repository
    counts = repository.get_summary_counts(db)

    # Count sensors by type from repository
    sensor_types_query = repository.get_all_sensor_types(db)
    sensor_type_counts = Counter(st[0] for st in sensor_types_query)

    summary = FarmStateSummary(
        total_users=counts["total_users"],
        total_areas=counts["total_areas"],
        total_cells=counts["total_cells"],
        total_sensors=counts["total_sensors"],
        sensor_types=dict(sensor_type_counts),
    )

    # Calculate average analytics if requested, using repository
    average_analytics = None
    if with_analytics:
        avg_query = repository.get_average_analytics_by_type(db)
        average_analytics = {
            analytic_type.value: round(avg_value, 2)
            for analytic_type, avg_value in avg_query if avg_value is not None
        }

    return FarmDetails(
        name=farm_name,
        summary=summary,
        average_analytics=average_analytics,
    )