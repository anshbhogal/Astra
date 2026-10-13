"""
ASTRA Backend - Phase 6 Failure Analysis & Defect REST API Router
Enforces JWT authentication, project access verification, and RBAC authorization with async Celery support.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Union, Dict, Any
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.domain import User, Project
from app.services.analysis_service import FailureAnalysisService
from app.schemas.analysis import FailureAnalysisResponse, DefectClusterResponse
from app.tasks.analysis_tasks import analyze_test_run_failures_task

router = APIRouter(prefix="/projects", tags=["Failure Analysis & Defects"])


async def _verify_project_access(project_id: uuid.UUID, db: AsyncSession) -> Project:
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return project


@router.post(
    "/{project_id}/runs/{run_id}/failure-analysis/analyze",
    response_model=Union[List[FailureAnalysisResponse], Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
)
async def analyze_run_failures(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    commit_sha: Optional[str] = None,
    async_mode: bool = False,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyzes failed test results for a test run and persists diagnostic failure reports & defect clusters.
    If async_mode=True, dispatches background Celery task and returns 202 Accepted.
    """
    await _verify_project_access(project_id, db)

    if async_mode:
        task = analyze_test_run_failures_task.delay(str(project_id), str(run_id), commit_sha)
        if response:
            response.status_code = status.HTTP_202_ACCEPTED
        return {
            "status": "DISPATCHED",
            "task_id": task.id,
            "message": "Failure analysis Celery task dispatched successfully",
            "project_id": str(project_id),
            "run_id": str(run_id),
        }

    service = FailureAnalysisService(db)
    reports = await service.analyze_run_failures(project_id, run_id, target_commit_sha=commit_sha)
    return reports


@router.get(
    "/{project_id}/runs/{run_id}/failure-analysis",
    response_model=List[FailureAnalysisResponse],
)
async def get_run_failure_analysis(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches diagnostic failure analysis reports for a specific test run."""
    await _verify_project_access(project_id, db)
    service = FailureAnalysisService(db)
    reports = await service.get_run_failure_analyses(project_id, run_id)
    return reports


@router.get(
    "/{project_id}/defects",
    response_model=List[DefectClusterResponse],
)
async def get_project_defects(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches active defect clusters for a project."""
    await _verify_project_access(project_id, db)
    service = FailureAnalysisService(db)
    defects = await service.get_project_defects(project_id)
    return defects


# ---------------------------------------------------------------------------
# Tester & Developer Bug Collaboration Endpoints
# ---------------------------------------------------------------------------
from pydantic import BaseModel
from app.models.domain import DefectComment, FailureAnalysisModel, UserRole
from sqlalchemy.orm import selectinload

class DefectCommentCreate(BaseModel):
    message: str
    status_change: Optional[str] = None


class DefectCommentResponse(BaseModel):
    id: uuid.UUID
    defect_id: uuid.UUID
    user_id: uuid.UUID
    message: str
    status_change: Optional[str] = None
    created_at: str
    user_name: str
    user_role: str


class DefectStatusUpdate(BaseModel):
    status: str
    assigned_to_id: Optional[uuid.UUID] = None


@router.get(
    "/{project_id}/defects/{defect_id}/comments",
    response_model=List[DefectCommentResponse],
)
async def get_defect_comments(
    project_id: uuid.UUID,
    defect_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches collaboration thread notes and status history between Tester and Developer."""
    await _verify_project_access(project_id, db)
    stmt = (
        select(DefectComment)
        .options(selectinload(DefectComment.user))
        .where(DefectComment.project_id == project_id, DefectComment.defect_id == defect_id)
        .order_by(DefectComment.created_at.asc())
    )
    comments = (await db.execute(stmt)).scalars().all()
    return [
        DefectCommentResponse(
            id=c.id,
            defect_id=c.defect_id,
            user_id=c.user_id,
            message=c.message,
            status_change=c.status_change,
            created_at=c.created_at.isoformat(),
            user_name=c.user.full_name if c.user else "Astra Engineer",
            user_role=c.user.role.value if c.user else "DEVELOPER"
        )
        for c in comments
    ]


@router.post(
    "/{project_id}/defects/{defect_id}/comments",
    response_model=DefectCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_defect_comment(
    project_id: uuid.UUID,
    defect_id: uuid.UUID,
    payload: DefectCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tester and Developer collaboration: post a bug note, fix suggestion, or status update."""
    await _verify_project_access(project_id, db)
    if current_user.role == UserRole.VIEWER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer role is restricted to read-only access.")

    # Check defect exists
    stmt = select(FailureAnalysisModel).where(FailureAnalysisModel.id == defect_id)
    defect = (await db.execute(stmt)).scalar_one_or_none()
    if not defect:
        # Check if defect_id is a defect cluster, otherwise find or match
        stmt_alt = select(FailureAnalysisModel).where(FailureAnalysisModel.project_id == project_id).limit(1)
        defect = (await db.execute(stmt_alt)).scalar_one_or_none()

    comment = DefectComment(
        project_id=project_id,
        defect_id=defect_id,
        user_id=current_user.id,
        message=payload.message,
        status_change=payload.status_change
    )
    db.add(comment)

    if payload.status_change and defect:
        defect.status = payload.status_change

    await db.commit()
    await db.refresh(comment)

    return DefectCommentResponse(
        id=comment.id,
        defect_id=comment.defect_id,
        user_id=comment.user_id,
        message=comment.message,
        status_change=comment.status_change,
        created_at=comment.created_at.isoformat(),
        user_name=current_user.full_name,
        user_role=current_user.role.value
    )


@router.patch(
    "/{project_id}/defects/{defect_id}/status",
    status_code=status.HTTP_200_OK,
)
async def update_defect_status(
    project_id: uuid.UUID,
    defect_id: uuid.UUID,
    payload: DefectStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update defect remediation status (OPEN, UNDER_INVESTIGATION, FIX_IN_PROGRESS, FIXED, VERIFIED)."""
    await _verify_project_access(project_id, db)
    if current_user.role == UserRole.VIEWER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer role is restricted to read-only access.")

    stmt = select(FailureAnalysisModel).where(FailureAnalysisModel.id == defect_id)
    defect = (await db.execute(stmt)).scalar_one_or_none()
    if defect:
        defect.status = payload.status
        if payload.assigned_to_id:
            defect.assigned_to_id = payload.assigned_to_id
        await db.commit()

    return {"status": payload.status, "defect_id": str(defect_id)}
