from pydantic import BaseModel
from services.user.schemas import UserResponse


class TokenResponse(BaseModel):
    """Modèle de réponse pour une authentification réussie, incluant le token et les informations utilisateur."""
    access_token: str
    user: UserResponse