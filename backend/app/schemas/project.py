import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.domain import LanguageFramework, UserRole
from app.schemas.auth import UserResponse


class ProjectMemberResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: UserRole
    created_at: datetime
    user: Optional[UserResponse] = None

    model_config = {"from_attributes": True}


class ProjectMemberAssign(BaseModel):
    user_id: uuid.UUID
    role: UserRole


class ProjectTeamBulkAssign(BaseModel):
    members: List[ProjectMemberAssign]


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    repository_url: str = Field(..., min_length=5, max_length=500)
    default_branch: str = Field(default="main", min_length=1, max_length=100)
    language_framework: LanguageFramework
    workspace_id: Optional[uuid.UUID] = None

    @field_validator("repository_url")
    def validate_repo_url(cls, v: str) -> str:
        v_str = str(v).strip()
        if not (v_str.startswith("http://") or v_str.startswith("https://") or v_str.startswith("git@") or v_str.startswith("file://") or v_str.startswith("/")):
            raise ValueError("Repository URL must begin with http://, https://, git@, file://, or absolute path /")
        return v_str


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    repository_url: Optional[str] = Field(None, min_length=5, max_length=500)
    default_branch: Optional[str] = Field(None, min_length=1, max_length=100)
    language_framework: Optional[LanguageFramework] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    repository_url: str
    default_branch: str
    language_framework: LanguageFramework
    owner_id: uuid.UUID
    owner: Optional[UserResponse] = None
    members: Optional[List[ProjectMemberResponse]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    skip: int
    limit: int
