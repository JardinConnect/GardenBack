from datetime import datetime
from sqlalchemy.orm import Session

from services.user.errors import UserAlreadyExistsError, UserNotFoundErrorID, UserNotFoundErrorEmail
from db.models import User, RoleEnum
from services.user.schemas import UserLoginSchema, UserSchema, UserUpdate

from services.auth.utils.security import get_password_hash, verify_password


def check_user(db: Session, data: UserLoginSchema):
    user = db.query(User).filter(User.email == data.email).first()

    if not user: 
        raise UserNotFoundErrorEmail(data.email)
    
    if verify_password(data.password, user.password):
        return True

def get_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundErrorID(user_id)
    return user


def get_userByEmail(db: Session, user_email: str):
    print(f"[DEBUG] Recherche utilisateur avec email: {user_email}")
    user = db.query(User).filter(User.email == user_email).first()
    print(f"[DEBUG] Utilisateur trouvé: {user is not None}")

    if not user:
        raise UserNotFoundErrorEmail(user_email)
    return user



def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserSchema):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise UserAlreadyExistsError(user.email)
    
    now = datetime.now()

    db_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        email=user.email,
        password=get_password_hash(user.password),
        role=user.role,
        created_at=now,
        updated_at=now
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_data: UserUpdate) -> User:
    """Met à jour un utilisateur existant."""
    db_user = get_user(db, user_id)  # Réutilise get_user pour gérer le cas "non trouvé"

    update_data = user_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db_user.updated_at = datetime.now()
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundErrorID(user_id)
    db.delete(user)
    db.commit()
    return True
