from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from db.database import get_db
from services.user import repository, schemas
from services.user.schemas import UserCreate, UserResponse
from services.user.errors import UserAlreadyExistsError, UserNotFoundError

router = APIRouter()

@router.get("/users/", response_model=List[UserResponse])
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Récupère la liste des utilisateurs avec pagination.
    """
    try:
        users = repository.get_users(db, skip=skip, limit=limit)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Récupère un utilisateur par son ID.
    """
    try:
        user = repository.get_user(db, user_id=user_id)
        return user
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Crée un nouvel utilisateur.
    """
    try:
        new_user = repository.create_user(db, user=user)
        return new_user
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Supprime un utilisateur par son ID.
    """
    try:
        result = repository.delete_user(db, user_id=user_id)
        return {"message": "Utilisateur supprimé avec succès"}
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))