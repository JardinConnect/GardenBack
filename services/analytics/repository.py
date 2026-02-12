from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, cast
from db.models import Analytic

from services.analytics.errors import (
    InvalidDateRangeError, 
    DataNotFoundError
)
from services.analytics.schemas import (
    AnalyticsFilter, AnalyticSchema, AnalyticType, AnalyticCreate, PaginatedAnalyticResult
)

def validate_request(start: datetime, end: datetime):
    """Valide la requête d'analytics"""
    if start and end:
        if start >= end:
            raise InvalidDateRangeError()


def get_analytics(db: Session, request: AnalyticsFilter) -> PaginatedAnalyticResult:
    # 1. Validation
    validate_request(request.start_date, request.end_date)

    # 2. Base query
    query = db.query(
        Analytic.value,
        Analytic.occurred_at,
        Analytic.sensor_code,
        Analytic.analytic_type
    )

    # 3. Filters
    filters = []
    if request.sensor_id:
        filters.append(Analytic.sensor_id == request.sensor_id)
    if request.sensor_code:
        filters.append(Analytic.sensor_code == request.sensor_code)
    if request.analytic_type:
        filters.append(Analytic.analytic_type == request.analytic_type)
    if request.start_date:
        filters.append(Analytic.occurred_at >= request.start_date)
    if request.end_date:
        filters.append(Analytic.occurred_at <= request.end_date)

    if filters:
        query = query.filter(and_(*filters))

    # 4. Compter le nombre total de résultats avant la pagination
    total_count = query.count()

    # 5. Appliquer la pagination
    paginated_query = query.offset(request.skip).limit(request.limit)

    # 6. Exécution
    rows = paginated_query.all()
    if not rows:
        raise DataNotFoundError()

    # 7. Mapping -> Dict[AnalyticType, List[Analytic]]
    result: Dict[AnalyticType, List[AnalyticSchema]] = {}
    for value, occurred_at, sensor_code, analytic_type in rows:
        analytic = AnalyticSchema(
            value=value,
            occurred_at=occurred_at,
            sensorCode=sensor_code
        )
        result.setdefault(analytic_type, []).append(analytic)

    return PaginatedAnalyticResult(
        total=total_count,
        skip=request.skip,
        limit=request.limit,
        data=result
    )


def create_analytic(db: Session, analytic_input: AnalyticCreate) -> AnalyticSchema:
    """Crée une nouvelle entrée d'analytique."""

    analytic_type_prefix = analytic_input.sensor_code.split('-')[0]
    
    try:
        analytic_type = AnalyticType.from_prefix(analytic_type_prefix)
    except ValueError as e:
        raise ValueError(f"Préfixe de capteur invalide: {analytic_type_prefix}") from e

    db_analytic = Analytic(
        value=analytic_input.value,
        occurred_at=analytic_input.timestamp,
        sensor_code=analytic_input.sensor_code,
        analytic_type=analytic_type,
        sensor_id=analytic_input.sensor_id
    )
    db.add(db_analytic)
    db.commit()
    db.refresh(db_analytic)

    return AnalyticSchema(
        value=cast(float, db_analytic.value),
        occurred_at=cast(datetime, db_analytic.occurred_at),
        sensorCode=cast(str, db_analytic.sensor_code)
    )