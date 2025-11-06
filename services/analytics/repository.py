from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict
from db.models import Analytic

from services.analytics.errors import (
    InvalidDateRangeError, 
    DataNotFoundError
)
from services.analytics.schemas import (
    AnalyticsFilter, AnalyticSchema, AnalyticResult, AnalyticType
)

def validate_request(start: datetime, end: datetime):
    """Valide la requête d'analytics"""
    if start and end:
        if start >= end:
            raise InvalidDateRangeError()


def get_analytics(db: Session, request: AnalyticsFilter) -> AnalyticResult:
    # 1. Validation
    validate_request(request.start_date, request.end_date)

    # 2. Base query
    query = db.query(
        Analytic.value,
        Analytic.occured_at,
        Analytic.sensor_code,
        Analytic.analytic_type
    )

    # 3. Filters
    filters = []
    if request.node_id:
        filters.append(Analytic.node_id == request.node_id)
    if request.sensor_code:
        filters.append(Analytic.sensor_code == request.sensor_code)
    if request.analytic_type:
        filters.append(Analytic.analytic_type == request.analytic_type)
    if request.start_date:
        filters.append(Analytic.occured_at >= request.start_date)
    if request.end_date:
        filters.append(Analytic.occured_at <= request.end_date)

    if filters:
        query = query.filter(and_(*filters))

    # 4. Execution
    rows = query.all()
    if not rows:
        raise DataNotFoundError()

    # 5. Mapping -> Dict[AnalyticType, List[Analytic]]
    result: Dict[AnalyticType, List[AnalyticSchema]] = {}
    for value, occured_at, sensor_code, analytic_type in rows:
        analytic = AnalyticSchema(
            value=value,
            occured_at=occured_at,
            sensorCode=sensor_code
        )
        result.setdefault(analytic_type, []).append(analytic)

    return AnalyticResult(result=result)