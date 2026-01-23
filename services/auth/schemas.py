from pydantic import BaseModel
from services.user.schemas import UserResponse


class TokenResponse(BaseModel):
    """Modèle de réponse pour une authentification réussie, incluant le token et les informations utilisateur."""
    access_token: str
    refresh_token: str
    user: UserResponse


class RefreshTokenSchema(BaseModel):
    """Schéma pour la requête de rafraîchissement du token."""
    refresh_token: str