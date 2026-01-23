
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from .auth import decode_jwt

class JWTBearer(HTTPBearer):
    """
    Dépendance FastAPI pour la vérification des tokens JWT.

    Hérite de `HTTPBearer` pour extraire le token de l'en-tête `Authorization`.
    Vérifie que le schéma est "Bearer" et que le token est valide et non expiré.

    En cas de succès, retourne le payload décodé du token.
    En cas d'échec, lève une `HTTPException` avec le code de statut 403.
    """
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[dict]:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)
        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            payload = decode_jwt(credentials.credentials)
            if payload is None:
                raise HTTPException(status_code=403, detail="Invalid or expired token.")
            return payload
        # Si auto_error=True, super().__call__ lèvera une exception avant d'arriver ici.
        # Cette exception est une sécurité supplémentaire si auto_error=False.
        raise HTTPException(status_code=403, detail="Invalid authorization code.")