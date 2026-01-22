from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from services.auth.bearer import JWTBearer
from services.user.repository import get_user_by_email


def get_current_user(
    db: Session = Depends(get_db),
    payload: dict = Depends(JWTBearer())
) -> User:
    """
    Dépendance pour obtenir l'utilisateur actuellement authentifié.

    1. Récupère le payload du token JWT via `JWTBearer`.
    2. Extrait l'email de l'utilisateur (stocké dans le champ `user_id` du payload).
    3. Récupère l'utilisateur correspondant depuis la base de données.
    4. Lève une exception `HTTPException` si l'utilisateur n'est pas trouvé ou si le token est invalide.

    :return: L'objet `User` (modèle SQLAlchemy) de l'utilisateur authentifié.
    """
    user_email = payload.get("user_id")
    if user_email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impossible de valider les informations d'identification.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_email(db, email=user_email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé.")
    return user