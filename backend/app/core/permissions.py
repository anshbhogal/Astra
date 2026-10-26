import uuid
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.domain import User, UserRole, Project, ProjectMember


async def get_project_or_403(
    project_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
    min_role: Optional[UserRole] = None,
    allowed_roles: Optional[List[UserRole]] = None
) -> Project:
    """
    Centralized Project Authorization Helper.
    Guarantees strict tenant isolation across all project-scoped routes.

    Rules:
    1. 404 if project does not exist.
    2. ADMIN role always has global access across all projects.
    3. Project owner (owner_id == current_user.id) has access.
    4. Explicit ProjectMember assigned to the project has access.
    5. Any other authenticated user receives 403 Forbidden.
    6. If min_role or allowed_roles are specified:
       - VIEWER cannot perform actions requiring DEVELOPER, TESTER, or ADMIN.
       - Roles are strictly validated against permissions.
    """
    stmt = (
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.members).selectinload(ProjectMember.user)
        )
        .where(Project.id == project_id, Project.is_deleted == False)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )

    # 1. Superadmin has global access
    if current_user.role == UserRole.ADMIN:
        return project

    # 2. Check ownership or membership
    is_owner = (project.owner_id == current_user.id)
    membership = next((m for m in project.members if m.user_id == current_user.id), None)

    if not is_owner and not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to access this repository."
        )

    # Determine user's effective role on this project
    effective_role = membership.role if (membership and membership.role) else current_user.role

    # 3. Check allowed roles if specified
    if allowed_roles is not None:
        if effective_role not in allowed_roles and current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{effective_role.value}' is not permitted for this operation."
            )

    # 4. Check min_role if specified
    if min_role is not None:
        if min_role == UserRole.ADMIN and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Administrator role required."
            )
        if min_role in (UserRole.DEVELOPER, UserRole.TESTER):
            if effective_role == UserRole.VIEWER and current_user.role == UserRole.VIEWER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Viewer role is restricted to read-only access."
                )

    return project
