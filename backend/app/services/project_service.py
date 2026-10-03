import uuid
from typing import List, Tuple, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.domain import Project, User, UserRole, AuditLog
from app.schemas.project import ProjectCreate, ProjectUpdate


async def create_new_project(db: AsyncSession, payload: ProjectCreate, owner: User) -> Project:
    project = Project(
        name=payload.name,
        description=payload.description,
        repository_url=payload.repository_url,
        default_branch=payload.default_branch,
        language_framework=payload.language_framework,
        owner_id=owner.id
    )
    db.add(project)
    await db.flush()

    audit_entry = AuditLog(
        actor_id=owner.id,
        action="PROJECT_CREATED",
        resource_type="PROJECT",
        resource_id=str(project.id),
        details={"name": project.name, "framework": project.language_framework.value}
    )
    db.add(audit_entry)
    await db.commit()
    
    # Reload with owner details
    stmt = select(Project).options(selectinload(Project.owner)).where(Project.id == project.id)
    return (await db.execute(stmt)).scalar_one()


async def get_accessible_projects(
    db: AsyncSession, current_user: User, skip: int = 0, limit: int = 50
) -> Tuple[List[Project], int]:
    limit = min(limit, 100) # enforce maximum page size of 100
    
    base_stmt = select(Project).options(selectinload(Project.owner))
    count_stmt = select(func.count(Project.id))

    if current_user.role != UserRole.ADMIN:
        base_stmt = base_stmt.where(Project.owner_id == current_user.id)
        count_stmt = count_stmt.where(Project.owner_id == current_user.id)

    total = (await db.execute(count_stmt)).scalar_one()
    
    stmt = base_stmt.order_by(Project.created_at.desc()).offset(skip).limit(limit)
    items = (await db.execute(stmt)).scalars().all()
    
    return list(items), total


async def get_project_by_id(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> Project:
    stmt = select(Project).options(selectinload(Project.owner)).where(Project.id == project_id)
    project = (await db.execute(stmt)).scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check project visibility/ownership policy
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, # 404 for security to prevent project enumeration
            detail="Project not found"
        )

    return project


async def update_existing_project(
    db: AsyncSession, project_id: uuid.UUID, payload: ProjectUpdate, current_user: User
) -> Project:
    project = await get_project_by_id(db, project_id, current_user)

    # Ownership / permission check
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this project."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            setattr(project, field, val)

    audit_entry = AuditLog(
        actor_id=current_user.id,
        action="PROJECT_UPDATED",
        resource_type="PROJECT",
        resource_id=str(project.id),
        details=update_data
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project_by_id(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> None:
    project = await get_project_by_id(db, project_id, current_user)

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this project."
        )

    audit_entry = AuditLog(
        actor_id=current_user.id,
        action="PROJECT_DELETED",
        resource_type="PROJECT",
        resource_id=str(project.id),
        details={"name": project.name}
    )
    db.add(audit_entry)
    await db.delete(project)
    await db.commit()
