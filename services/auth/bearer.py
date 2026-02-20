from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from .auth import decode_jwt

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[dict]:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)
        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(status_code=401, detail="Invalid authentication scheme.")
            payload = decode_jwt(credentials.credentials)
            if payload is None:
                raise HTTPException(status_code=401, detail="Invalid or expired token.")
            return payload
        raise HTTPException(status_code=401, detail="Invalid authorization code.")