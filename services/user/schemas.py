from datetime import datetime
import uuid
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from db.models import RoleEnum

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Email de l'utilisateur")

class UserLoginSchema(UserBase):
    password: str = Field(..., description="Mot de passe de l'utilisateur")

class UserSchema(UserBase):
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    password: str = Field(..., min_length=8)
    role: RoleEnum

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None

class UserPasswordUpdate(BaseModel):
    current_password: str = Field(..., description="Mot de passe actuel de l'utilisateur.")
    new_password: str = Field(..., min_length=8, description="Nouveau mot de passe (8 caractères minimum).")

class UserResponse(UserBase):
    id: uuid.UUID
    first_name: str
    last_name: str
    phone_number: Optional[str]
    role: RoleEnum
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class MessageResponse(BaseModel):
    message: str