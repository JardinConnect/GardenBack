from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_alerts():
    return {"message": "Liste des alertes"}

@router.post("/")
async def create_alert(alert: dict):
    return {"message": "Alerte créée", "data": alert} 
