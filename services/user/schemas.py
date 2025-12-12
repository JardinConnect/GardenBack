from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class RoleSchema(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True)

class RoleNameEnum(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    EMPLOYEES = "employees"
    TRAINEE = "trainee"

class UserSchema(BaseModel):
    first_name: str = Field(...)
    last_name: str = Field(...)
    phone_number: Optional[str] = None
    email: EmailStr = Field(...)
    password: str = Field(...)
    role_name: RoleNameEnum = Field(..., description="Le nom du rôle (superadmin, admin, employees, trainee)")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "first_name": "Sam",
                "last_name": "Gardener",
                "phone_number": "0612345678",
                "email": "sam@x.com",
                "password": "weakpassword",
                "role_name": "employees"
            }
        }
    )

class UserLoginSchema(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "email": "admin@garden.com",
                "password": "admin123"
            }
        }
    )

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Cena",
                "phone_number": "0687654321"
            }
        }
    )

class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    email: str
    role: RoleSchema
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
