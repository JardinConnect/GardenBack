from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# db
from db.database import get_db
# auth
from services.auth.bearer import JWTBearer
# user
from services.user import repository
from services.user.schemas import UserResponse, UserSchema, UserUpdate, MessageResponse
from services.user.errors import UserAlreadyExistsError, UserNotFoundErrorID

router = APIRouter()


@router.get("/users/", response_model=List[UserResponse])
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Récupère une liste paginée d'utilisateurs.
    
    - **skip**: Nombre d'utilisateurs à sauter (pour la pagination).
    - **limit**: Nombre maximum d'utilisateurs à retourner.
    
    Cette route est protégée et nécessite une authentification JWT.
    """
    users = repository.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Récupère un utilisateur par son ID.

    - **user_id**: L'ID de l'utilisateur à récupérer.

    Cette route est protégée et nécessite une authentification JWT.

    **Erreurs possibles :**
    - `404 Not Found`: Si aucun utilisateur ne correspond à l'ID fourni.
    """
    try:
        user = repository.get_user(db, user_id=user_id)
        return user
    except UserNotFoundErrorID as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/users/", response_model=UserResponse, status_code=201)
def create_user(user: UserSchema, db: Session = Depends(get_db)):
    """
    Crée un nouvel utilisateur (route protégée).

    - **user**: Les données du nouvel utilisateur à créer.

    Utilisée par un administrateur pour ajouter un utilisateur au système.
    Pour l'inscription publique, utilisez la route `/signup`.

    **Erreurs possibles :**
    - `400 Bad Request`: Si un utilisateur avec le même email existe déjà.
    """
    try:
        new_user = repository.create_user(db, user=user)
        return new_user
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    """
    Met à jour les informations d'un utilisateur existant.

    - **user_id**: L'ID de l'utilisateur à mettre à jour.
    - **user_data**: Les champs à mettre à jour.

    Seuls les champs présents dans le body de la requête seront mis à jour.

    **Erreurs possibles :**
    - `404 Not Found`: Si aucun utilisateur ne correspond à l'ID fourni.
    """
    try:
        updated_user = repository.update_user(db, user_id=user_id, user_data=user_data)
        return updated_user
    except UserNotFoundErrorID as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Supprime un utilisateur par son ID.

    - **user_id**: L'ID de l'utilisateur à supprimer.

    **Erreurs possibles :**
    - `404 Not Found`: Si aucun utilisateur ne correspond à l'ID fourni.
    """
    try:
        repository.delete_user(db, user_id=user_id)
        return {"message": f"Utilisateur {user_id} supprimé avec succès"}
    except UserNotFoundErrorID as e:
        raise HTTPException(status_code=404, detail=str(e))
