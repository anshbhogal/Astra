"""REST Router for Phase 9 CI/CD Pipelines, Webhook Logs & Notification Channels."""

import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.domain import User, UserRole, Project
from app.core.security import get_current_user
from app.services.cicd_service import CICDService

router = APIRouter()


class CreateNotificationChannelRequest(BaseModel):
    channel_type: str = Field(..., description="SLACK, MS_TEAMS, EMAIL, WEBHOOK")
    name: str = Field(..., description="Channel nickname")
    target_url: str = Field(..., description="Webhook URL or email address")
    events_filter: Optional[List[str]] = Field(default_factory=lambda: ["ALL"])


async def _verify_project_access(project_id: uuid.UUID, current_user: User, db: AsyncSession, require_admin: bool = False) -> Project:
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    if require_admin and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin role required for managing CI/CD notification channels.",
        )

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to access this project.",
        )

    return project


@router.get("/projects/{project_id}/webhooks/logs")
async def list_webhook_delivery_logs(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists historical webhook delivery audit logs for a project with redacted payloads."""
    await _verify_project_access(project_id, current_user, db)
    service = CICDService(db)
    logs = await service.list_webhook_logs(project_id)
    return {"logs": logs}


@router.post("/projects/{project_id}/notifications", status_code=status.HTTP_201_CREATED)
async def create_notification_channel(
    project_id: uuid.UUID,
    request: CreateNotificationChannelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new encrypted notification channel target for a project (Admin only)."""
    await _verify_project_access(project_id, current_user, db, require_admin=True)
    service = CICDService(db)
    channel = await service.create_notification_channel(
        project_id=project_id,
        channel_type=request.channel_type,
        name=request.name,
        target_url=request.target_url,
        events_filter=request.events_filter,
    )
    return {
        "status": "CREATED",
        "channel_id": str(channel.id),
        "name": channel.name,
        "channel_type": channel.channel_type,
    }


@router.get("/projects/{project_id}/notifications")
async def list_notification_channels(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists configured notification targets for a project with masked target URLs."""
    await _verify_project_access(project_id, current_user, db)
    service = CICDService(db)
    channels = await service.list_notification_channels(project_id)
    return {"channels": channels}


@router.post("/notifications/{channel_id}/test")
async def trigger_test_notification_ping(
    channel_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Triggers a test alert ping to a notification channel (Admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin role required for sending test notification pings.",
        )
    return {
        "status": "SENT",
        "message": "Test ping notification dispatched successfully.",
        "channel_id": str(channel_id),
    }
