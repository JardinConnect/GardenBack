import uuid
from datetime import datetime, UTC
from typing import List
from sqlalchemy.orm import Session
 
from db.models import User, RoleEnum
from services.auth.utils.security import get_password_hash, verify_password 
 
from .schemas import UserSchema, UserUpdate, UserLoginSchema, UserPasswordUpdate
from .errors import UserAlreadyExistsError, UserNotFoundErrorID, InvalidPasswordError, CannotDeleteSuperAdminError

def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundErrorID(user_id=str(user_id))
    return user

def get_user_by_email(db: Session, email: str) -> User | None:
    """Récupère un utilisateur par son adresse email."""
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 10) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserSchema) -> User:
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise UserAlreadyExistsError(email=user.email)
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        email=user.email,
        password=hashed_password,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: uuid.UUID, user_data: UserUpdate) -> User:
    db_user = get_user(db, user_id=user_id)
    
    update_data = user_data.model_dump(exclude_unset=True)

    # Règle de sécurité : on ne peut pas changer le rôle d'un super administrateur.
    if db_user.role == RoleEnum.SUPERADMIN and 'role' in update_data:
        del update_data['role']

    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db_user.updated_at = datetime.now(UTC)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: uuid.UUID) -> bool:
    db_user = get_user(db, user_id=user_id)
    if db_user.role == RoleEnum.SUPERADMIN:
        raise CannotDeleteSuperAdminError()
    db.delete(db_user)
    db.commit()
    return True

def check_user(db: Session, login_data: UserLoginSchema) -> User | None:
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password):
        return None
    return user

def update_user_password(db: Session, user_id: uuid.UUID, password_data: UserPasswordUpdate) -> bool:
    """Met à jour le mot de passe d'un utilisateur."""
    user = get_user(db, user_id=user_id)

    if not verify_password(password_data.current_password, user.password):
        raise InvalidPasswordError("Le mot de passe actuel est incorrect.")

    hashed_password = get_password_hash(password_data.new_password)
    user.password = hashed_password
    user.updated_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    return True