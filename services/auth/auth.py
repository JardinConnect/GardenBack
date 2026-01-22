import time
from typing import Dict, Optional, Any
from decouple import config

from db.models import User
from services.user.schemas import UserResponse

import jwt



JWT_ALGORITHM = config("JWT_ALGORITHM")
JWT_SECRET = config("JWT_SECRET")


def token_response(token: str, user: User) -> Dict[str, Any]:
    return {
        "access_token": token,
        "user": UserResponse.model_validate(user)
    }

def sign_jwt(user: User) -> Dict[str, Any]:
    payload = {
        "user_id": user.email,
        "role": user.role.value,
        "expires": time.time() + 600
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token_response(token, user)

def decode_jwt(token: str) -> Optional[dict]:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token if decoded_token["expires"] >= time.time() else None
    except Exception as e:
        print("❌ Erreur de décodage du token JWT", e)
        return None # Return None on decoding errors to indicate invalid token