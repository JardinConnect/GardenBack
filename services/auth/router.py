from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from db.database import get_db
from db.models import RefreshToken, User

from services.user import repository
from services.user.errors import UserAlreadyExistsError
from ..user.schemas import UserSchema, UserLoginSchema
from .auth import sign_jwt
from .schemas import TokenResponse, RefreshTokenSchema

router = APIRouter()

@router.post("/signup", status_code=201, response_model=TokenResponse)
async def signup(
    user: UserSchema = Body(...),
    db: Session = Depends(get_db)
):
    """
    Inscrit un nouvel utilisateur dans le système.

    - **user**: Données du nouvel utilisateur à créer.

    Retourne un token d'accès et les informations de l'utilisateur créé en cas de succès.

    **Erreurs possibles :**
    - `400 Bad Request`: Si un utilisateur avec le même email existe déjà.
    - `500 Internal Server Error`: En cas d'erreur inattendue lors de la création.
    """
    try:
        db_user = repository.create_user(db, user)
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return sign_jwt(db, db_user)

@router.post("/login", status_code=200, response_model=TokenResponse)
async def login(
    user: UserLoginSchema = Body(..., examples=[{"email": "admin@garden.com", "password": "admin123"}]),
    db: Session = Depends(get_db)
): 
    """
    Authentifie un utilisateur et retourne un token JWT.

    - **user**: Identifiants de connexion (email et mot de passe).

    Retourne un token d'accès et les informations de l'utilisateur en cas de succès.

    **Erreurs possibles :**
    - `401 Unauthorized`: Si l'email ou le mot de passe est incorrect.
    """
    # check_user retourne l'objet User en cas de succès, ou None.
    # Cela fusionne la vérification des identifiants et la récupération de l'utilisateur en une seule requête.
    db_user = repository.check_user(db, user)
    if db_user:
        return sign_jwt(db, db_user)
    raise HTTPException(
        status_code=401,
        detail="Incorrect email or password",
    )

@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_access_token(
    body: RefreshTokenSchema,
    db: Session = Depends(get_db)
):
    """
    Génère une nouvelle paire de tokens (accès et rafraîchissement) à partir d'un refresh token valide.
    L'ancien refresh token est invalidé (rotation).
    """
    refresh_token_str = body.refresh_token
    
    db_refresh_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token_str).first()

    if not db_refresh_token:
        raise HTTPException(status_code=404, detail="Refresh token not found or already used.")

    if db_refresh_token.expires_at < datetime.now(timezone.utc):
        db.delete(db_refresh_token)
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token has expired.")

    user = db.query(User).filter(User.id == db_refresh_token.user_id).first()
    if not user:
        # Ce cas est peu probable si la DB est cohérente, mais c'est une sécurité.
        raise HTTPException(status_code=404, detail="User associated with token not found.")

    # Invalider l'ancien refresh token (rotation de token)
    db.delete(db_refresh_token)
    db.commit()

    # Générer et retourner une nouvelle paire de tokens
    return sign_jwt(db, user)

@router.post("/logout", status_code=200)
async def logout(
    body: RefreshTokenSchema,
    db: Session = Depends(get_db)
):
    """
    Déconnecte l'utilisateur en invalidant son refresh token.
    """
    db_refresh_token = db.query(RefreshToken).filter(RefreshToken.token == body.refresh_token).first()

    if db_refresh_token:
        db.delete(db_refresh_token)
        db.commit()
    
    return {"message": "Successfully logged out."}