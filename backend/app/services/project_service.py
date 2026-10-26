import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.domain import Project, User, UserRole, AuditLog, ProjectMember
from app.models.canonical import Workspace
from app.schemas.project import ProjectCreate, ProjectUpdate
from sqlalchemy import delete


async def create_new_project(db: AsyncSession, payload: ProjectCreate, owner: User) -> Project:
    workspace_id = getattr(payload, "workspace_id", None)
    if not workspace_id:
        ws_stmt = select(Workspace.id).limit(1)
        workspace_id = (await db.execute(ws_stmt)).scalar_one_or_none()

    project = Project(
        name=payload.name,
        description=payload.description,
        repository_url=payload.repository_url,
        default_branch=payload.default_branch,
        language_framework=payload.language_framework,
        owner_id=owner.id,
        workspace_id=workspace_id,
        actor_type="USER"
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
    
    # Reload with owner details and members
    stmt = (
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.members).selectinload(ProjectMember.user)
        )
        .where(Project.id == project.id)
    )
    return (await db.execute(stmt)).scalar_one()


async def get_accessible_projects(
    db: AsyncSession, current_user: User, skip: int = 0, limit: int = 50
) -> Tuple[List[Project], int]:
    limit = min(limit, 100) # enforce maximum page size of 100
    
    base_stmt = select(Project).options(
        selectinload(Project.owner),
        selectinload(Project.members).selectinload(ProjectMember.user)
    ).where(Project.is_deleted == False)
    count_stmt = select(func.count(Project.id)).where(Project.is_deleted == False)

    if current_user.role != UserRole.ADMIN:
        subq = select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id)
        condition = (Project.id.in_(subq)) | (Project.owner_id == current_user.id)
        base_stmt = base_stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = (await db.execute(count_stmt)).scalar_one()
    
    stmt = base_stmt.order_by(Project.created_at.desc()).offset(skip).limit(limit)
    items = (await db.execute(stmt)).scalars().all()
    
    return list(items), total


async def get_project_by_id(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> Project:
    from app.core.permissions import get_project_or_403
    return await get_project_or_403(project_id=project_id, current_user=current_user, db=db)


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
    project.is_deleted = True
    project.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def get_project_members(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> List[ProjectMember]:
    await get_project_by_id(db, project_id, current_user)
    stmt = (
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def assign_project_member(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, role: UserRole, current_user: User
) -> ProjectMember:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins can assign repository team members.")
    
    target_user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.role = role
        await db.commit()
        await db.refresh(existing)
        return existing

    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role
    )
    db.add(member)
    await db.commit()
    
    stmt_full = (
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.id == member.id)
    )
    return (await db.execute(stmt_full)).scalar_one()


async def remove_project_member(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, current_user: User
) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins can remove repository team members.")
    
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    )
    member = (await db.execute(stmt)).scalar_one_or_none()
    if member:
        await db.delete(member)
        await db.commit()


async def set_project_team(
    db: AsyncSession, project_id: uuid.UUID, members_list: List[dict], current_user: User
) -> List[ProjectMember]:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins can configure repository teams.")

    # Remove existing members
    await db.execute(
        delete(ProjectMember).where(ProjectMember.project_id == project_id)
    )
    
    for m in members_list:
        uid = m.get("user_id") if isinstance(m, dict) else getattr(m, "user_id", None)
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
        if uid and role:
            db.add(ProjectMember(
                project_id=project_id,
                user_id=uid,
                role=role
            ))
            
    await db.commit()
    return await get_project_members(db, project_id, current_user)
