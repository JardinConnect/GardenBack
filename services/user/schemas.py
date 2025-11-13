from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
from typing import Optional

class UserSchema(BaseModel):
    username: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "username": "Sam Gardener",
                "email": "sam@x.com",
                "password": "weakpassword"
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
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    isAdmin: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
