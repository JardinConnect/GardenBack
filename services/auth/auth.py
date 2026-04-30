import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
from decouple import config
from sqlalchemy.orm import Session

from db.models import User, RefreshToken
from services.user.schemas import UserResponse

import jwt


JWT_ALGORITHM = config("JWT_ALGORITHM")
JWT_SECRET = config("JWT_SECRET")
REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_refresh_token(db: Session, user_id: int) -> str:
    """
    Crée, stocke et retourne un nouveau refresh token.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_refresh_token = RefreshToken(
        token=str(uuid.uuid4()),
        user_id=user_id,
        expires_at=expires_at
    )
    
    db.add(db_refresh_token)
    db.commit()
    db.refresh(db_refresh_token)
    
    return db_refresh_token.token


def token_response(access_token: str, refresh_token: str, user: User) -> Dict[str, Any]:
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": UserResponse.model_validate(user)
    }

def sign_jwt(db: Session, user: User) -> Dict[str, Any]:
    payload = {
        "user_id": user.email,
        "role": user.role.value,
        "expires": ((time.time() + 600) * 6) *24 # 10 minutes * 6 * 24 = 1 day
    }

    access_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    refresh_token = create_refresh_token(db, user.id)

    return token_response(access_token, refresh_token, user)

def decode_jwt(token: str) -> Optional[dict]:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token if decoded_token["expires"] >= time.time() else None
    except Exception as e:
        print("❌ Erreur de décodage du token JWT", e)
        return None # Return None on decoding errors to indicate invalid token