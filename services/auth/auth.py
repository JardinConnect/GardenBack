import time
from typing import Dict, Optional
from decouple import config
from sqlalchemy.orm import Session

from services.user.repository import get_userByEmail
from services.user.schemas import RoleEnum, UserSchema

import jwt



JWT_ALGORITHM = config("JWT_ALGORITHM")
JWT_SECRET = config("JWT_SECRET")


def token_response(token: str, user:UserSchema):
    return {
        "access_token": token,
        "user":user
    }

def sign_jwt(user_email: str, user_role: RoleEnum, db: Session) -> Dict[str, str]:
    payload = {
        "user_id": user_email,
        "role": user_role.value,
        "expires": time.time() + 600
    }


    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    user = get_userByEmail(db, user_email)

    return token_response(token, user)

def decode_jwt(token: str) -> Optional[dict]:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token if decoded_token["expires"] >= time.time() else None
    except Exception as e:
        print("❌ Erreur de décodage du token JWT", e)
        return None # Return None on decoding errors to indicate invalid token