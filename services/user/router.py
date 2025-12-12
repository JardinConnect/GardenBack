from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# db
from db.database import get_db
# auth
from services.auth.bearer import JWTBearer
# user
from services.user import repository
from services.user.schemas import UserResponse, UserSchema, UserUpdate
from services.user.errors import UserAlreadyExistsError, UserNotFoundErrorID, UserNotFoundErrorEmail

router = APIRouter()


@router.get("/users/", dependencies=[Depends(JWTBearer())], response_model=List[UserResponse])
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Récupère la liste des utilisateurs avec pagination.
    """
    try:
        users = repository.get_users(db, skip=skip, limit=limit)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}", dependencies=[Depends(JWTBearer())], response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Récupère un utilisateur par son ID.
    """
    try:
        user = repository.get_user(db, user_id=user_id)
        return user
    except UserNotFoundErrorID as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UserNotFoundErrorEmail as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/", dependencies=[Depends(JWTBearer())], response_model=UserResponse)
def create_user(user: UserSchema, db: Session = Depends(get_db)):
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

@router.put("/users/{user_id}", dependencies=[Depends(JWTBearer())], response_model=UserResponse)
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    """
    Met à jour les informations d'un utilisateur.
    """
    try:
        updated_user = repository.update_user(db, user_id=user_id, user_data=user_data)
        return updated_user
    except UserNotFoundErrorID as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}", dependencies=[Depends(JWTBearer())])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Supprime un utilisateur par son ID.
    """
    try:
        repository.delete_user(db, user_id=user_id)
        return {"message": f"Utilisateur {user_id} supprimé avec succès"}
    except UserNotFoundErrorID as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UserNotFoundErrorEmail as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
