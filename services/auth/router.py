from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db

from .auth import sign_jwt

from services.user import repository
from services.user.errors import UserAlreadyExistsError
from ..user.schemas import UserSchema, UserLoginSchema

router = APIRouter()

users = []

@router.post("/signup", status_code=201)
async def create_user(
    user: UserSchema = Body(...),
    db: Session = Depends(get_db)
):
    try:
        repository.create_user(db, user)
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return sign_jwt(user.email, user.role, db)

@router.post("/login", status_code=201)
async def login(
    user: UserLoginSchema,
    db: Session = Depends(get_db)
): 
    if repository.check_user(db, user):
        db_user = repository.get_userByEmail(db, user.email) # Fetch user to get the role
        return sign_jwt(db_user.email, db_user.role, db)
    return {
        "error": "Wrong login details !"
    }