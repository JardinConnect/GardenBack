import uuid
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from db.models import RoleEnum

# Schema for user login
class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

# This schema is used when creating a user. Password is required.
# It was named UserCreate, renamed to UserSchema for consistency with imports.
class UserSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    role: RoleEnum = RoleEnum.EMPLOYEES

# This schema is for updating a user. All fields are optional.
class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None

# This schema is used when returning a user from the API. Password should not be included.
class UserResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    role: RoleEnum

    model_config = ConfigDict(from_attributes=True)

# A generic message response for delete operations
class MessageResponse(BaseModel):
    message: str