from fastapi import APIRouter
from services.system.service import system_service
from services.system.schemas import SystemMetrics

router = APIRouter()

@router.get("/metrics", response_model=SystemMetrics)
def get_system_metrics():
    return system_service.get_metrics()
