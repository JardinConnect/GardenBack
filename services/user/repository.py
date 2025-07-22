from datetime import datetime
from sqlalchemy.orm import Session

from services.user.errors import UserAlreadyExistsError, UserNotFoundError
from db.models import User
from services.user.schemas import UserLoginSchema, UserSchema

from services.auth.utils.security import get_password_hash, verify_password


def check_user(db: Session, data: UserLoginSchema):
    user = db.query(User).filter(User.email == data.email).first()

    if not user: 
        raise UserNotFoundError(data.email)
    
    if verify_password(data.password, user.password):
        return True

def get_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError(user_id)
    return user


def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserSchema):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise UserAlreadyExistsError(user.email)
    
    now = datetime.now()

    db_user = User(
        username=user.username,
        email=user.email,
        password=get_password_hash(user.password),
        isAdmin=False,
        created_at=now,
        updated_at=now
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user



def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError(user_id)
    db.delete(user)
    db.commit()
    return True
