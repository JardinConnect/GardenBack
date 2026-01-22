from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db

from services.user import repository
from services.user.errors import UserAlreadyExistsError
from ..user.schemas import UserSchema, UserLoginSchema
from .auth import sign_jwt
from .schemas import TokenResponse

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

    return sign_jwt(db_user)

@router.post("/login", status_code=200, response_model=TokenResponse)
async def login(
    user: UserLoginSchema,
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
        return sign_jwt(db_user)
    raise HTTPException(
        status_code=401,
        detail="Incorrect email or password",
    )