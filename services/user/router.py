from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import List
import uuid

# db
from db.database import get_db
# user
from services.user import repository
from services.user.schemas import UserResponse, UserSchema, UserUpdate, MessageResponse, UserPasswordUpdate
from services.user.errors import UserAlreadyExistsError, UserNotFoundErrorID, InvalidPasswordError
from services.auth.dependencies import get_current_user
from services.audit.service import log_action
from db.models import User, RoleEnum

router = APIRouter()


@router.get("/users/", response_model=List[UserResponse])
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Récupère une liste paginée d'utilisateurs.
    
    - **skip**: Nombre d'utilisateurs à sauter (pour la pagination).
    - **limit**: Nombre maximum d'utilisateurs à retourner.
    
    Cette route est protégée et nécessite une authentification JWT.
    """
    users = repository.get_users(db, skip=skip, limit=limit)
    return users

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden", "model": MessageResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found", "model": MessageResponse},
    }
)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Récupère un utilisateur par son ID.

    - **user_id**: L'ID de l'utilisateur à récupérer.

    Cette route est protégée et nécessite une authentification JWT.

    **Erreurs possibles :**
    - `403 Forbidden`: Si l'utilisateur n'a pas les droits pour voir ce profil.
    - `404 Not Found`: Si aucun utilisateur ne correspond à l'ID fourni.
    """
    # Un admin peut voir n'importe qui, un utilisateur ne peut voir que son propre profil.
    if current_user.role not in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN] and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas la permission de voir ce profil."
        )
    try:
        user = repository.get_user(db, user_id=user_id)
        return user
    except UserNotFoundErrorID as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post(
    "/users/",
    response_model=UserResponse,
    status_code=201,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden", "model": MessageResponse},
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request", "model": MessageResponse},
    })
def create_user(user: UserSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Crée un nouvel utilisateur (route protégée).

    - **user**: Les données du nouvel utilisateur à créer.

    Utilisée par un administrateur pour ajouter un utilisateur au système.
    Pour l'inscription publique, utilisez la route `/signup`.

    **Erreurs possibles :**
    - `400 Bad Request`: Si un utilisateur avec le même email existe déjà.
    - `403 Forbidden`: Si l'utilisateur authentifié n'est pas un administrateur.
    """
    if current_user.role not in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un administrateur peut créer un nouvel utilisateur."
        )
    try:
        new_user = repository.create_user(db, user=user)
        log_action(db, current_user, "create", "user", new_user.id, details={"email": new_user.email})
        return new_user
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden", "model": MessageResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found", "model": MessageResponse},
    }
)
def update_user(user_id: uuid.UUID, user_data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Met à jour les informations d'un utilisateur existant.

    - **user_id**: L'ID de l'utilisateur à mettre à jour.
    - **user_data**: Les champs à mettre à jour.

    Seuls les champs présents dans le body de la requête seront mis à jour.
    Un utilisateur peut mettre à jour son propre profil. Un administrateur peut mettre à jour n'importe quel profil.

    **Erreurs possibles :**
    - `403 Forbidden`: Si l'utilisateur n'a pas les droits pour modifier ce profil.
    - `404 Not Found`: Si aucun utilisateur ne correspond à l'ID fourni.
    """
    if current_user.role not in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN] and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas la permission de modifier cet utilisateur."
        )

    try:
        updated_user = repository.update_user(db, user_id=user_id, user_data=user_data)
        log_action(db, current_user, "update", "user", user_id, details=user_data.model_dump(exclude_unset=True))
        return updated_user
    except UserNotFoundErrorID as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put(
    "/users/{user_id}/password",
    response_model=MessageResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden", "model": MessageResponse},
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request", "model": MessageResponse},
    }
)
def update_user_password( # Ajout de Path pour user_id pour une meilleure documentation
    password_data: UserPasswordUpdate,
    user_id: uuid.UUID = Path(..., title="L'ID de l'utilisateur dont le mot de passe doit être mis à jour"), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour le mot de passe de l'utilisateur authentifié.

    Seul l'utilisateur authentifié peut modifier son propre mot de passe.
    Le mot de passe actuel doit être fourni pour validation.

    - **user_id**: L'ID de l'utilisateur.
    - **password_data**: Le mot de passe actuel et le nouveau mot de passe.

    **Erreurs possibles :**
    - `403 Forbidden`: Si l'utilisateur authentifié n'a pas les droits.
    - `400 Bad Request`: Si le mot de passe actuel est incorrect.
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas la permission d'effectuer cette action."
        )

    try:
        repository.update_user_password(db, user_id=user_id, password_data=password_data)
        log_action(db, current_user, "update", "user", user_id, details={"field": "password"})
        return {"message": "Mot de passe mis à jour avec succès"}
    except InvalidPasswordError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Supprime un utilisateur par son ID.

    - **user_id**: L'ID de l'utilisateur à supprimer.

    **Erreurs possibles :**
    - `403 Forbidden`: Si l'utilisateur authentifié n'est pas un administrateur.
    - `404 Not Found`: Si aucun utilisateur ne correspond à l'ID fourni.
    """
    if current_user.role not in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un administrateur peut supprimer un utilisateur."
        )
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas supprimer votre propre compte."
        )
    try:
        repository.delete_user(db, user_id=user_id)
        log_action(db, current_user, "delete", "user", user_id)
        return {"message": f"Utilisateur {user_id} supprimé avec succès"}
    except UserNotFoundErrorID as e:
        raise HTTPException(status_code=404, detail=str(e))
