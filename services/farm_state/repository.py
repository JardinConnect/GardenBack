from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Tuple, Dict, Optional

from db.models import (
    User as UserModel,
    Area,
    Cell,
    Sensor,
    Farm,
    Analytic,
    AnalyticType,
)


def get_farm(db: Session) -> Optional[Farm]:
    """
    Retrieves the single Farm instance from the database.
    """
    return db.query(Farm).first()


def get_summary_counts(db: Session) -> Dict[str, int]:
    """
    Counts the total number of users, areas, cells, and sensors.
    """
    return {
        "total_users": db.query(UserModel).count(),
        "total_areas": db.query(Area).count(),
        "total_cells": db.query(Cell).count(),
        "total_sensors": db.query(Sensor).count(),
    }


def get_all_sensor_types(db: Session) -> List[Tuple[str]]:
    """
    Retrieves a list of all sensor types from the sensors table.
    """
    return db.query(Sensor.sensor_type).all()


def get_average_analytics_by_type(db: Session) -> List[Tuple[AnalyticType, float]]:
    """
    Calculates the average value for each analytic type across all analytics.
    """
    return (
        db.query(Analytic.analytic_type, func.avg(Analytic.value))
        .group_by(Analytic.analytic_type)
        .all()
    )