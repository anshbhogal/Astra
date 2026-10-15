import uuid
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.domain import UserRole


def validate_strong_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter (A-Z).")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter (a-z).")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one number (0-9).")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~` ]", v):
        raise ValueError("Password must contain at least one special character (!@#$%^&* etc).")
    return v


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters with a mix of characters")
    full_name: str = Field(..., min_length=2, max_length=255)
    role: Optional[UserRole] = UserRole.DEVELOPER

    @field_validator("email", mode="before")
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("password")
    def validate_password_complexity(cls, v: str) -> str:
        return validate_strong_password(v)

    @field_validator("role")
    def validate_public_registration_role(cls, v: Optional[UserRole]) -> UserRole:
        # Public registrations cannot request or grant themselves ADMIN role
        if v == UserRole.ADMIN:
            raise ValueError("Registration for Administrator role is not permitted. Only existing Administrators can grant admin privileges.")
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
    is_approved: bool = True
    must_change_password: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Temporary password (must be changed upon first login)")
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = UserRole.DEVELOPER
    project_ids: Optional[list[uuid.UUID]] = None

    @field_validator("email", mode="before")
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class ChangePasswordRequest(BaseModel):
    current_password: Optional[str] = None
    new_password: str

    @field_validator("new_password")
    def validate_new_pwd(cls, v: str) -> str:
        return validate_strong_password(v)


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    user: UserResponse
