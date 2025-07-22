from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_data():
    return {"message": "Liste des datas"}
