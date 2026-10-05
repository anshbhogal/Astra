import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.domain import UserRole


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(..., min_length=2, max_length=255)
    role: Optional[UserRole] = UserRole.DEVELOPER

    @field_validator("email", mode="before")
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("role")
    def validate_public_registration_role(cls, v: Optional[UserRole]) -> UserRole:
        # Public registrations cannot grant themselves ADMIN role
        if v == UserRole.ADMIN:
            return UserRole.DEVELOPER
        return v or UserRole.DEVELOPER


class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email", mode="before")
    def normalize_email_or_username(cls, v: str) -> str:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean in ["admin", "dev", "tester", "viewer"]:
                return f"{v_clean}@astra.local"
            return v_clean
        return v


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
