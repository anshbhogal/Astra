import uuid
from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.services import project_service
from app.core.security import get_current_user
from app.core.rbac import require_roles
from app.models.domain import User, UserRole

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """Create a new software project."""
    return await project_service.create_new_project(db, payload, current_user)


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all projects accessible to the authenticated user."""
    items, total = await project_service.get_accessible_projects(db, current_user, skip=skip, limit=limit)
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in items],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details for a specific project."""
    project = await project_service.get_project_by_id(db, project_id, current_user)
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """Update project details."""
    return await project_service.update_existing_project(db, project_id, payload, current_user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """Delete a project."""
    await project_service.delete_project_by_id(db, project_id, current_user)
    return None
