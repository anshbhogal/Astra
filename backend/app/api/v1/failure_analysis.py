"""
ASTRA Backend - Phase 6 Failure Analysis & Defect REST API Router
Enforces JWT authentication, project access verification, and RBAC authorization.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.domain import User, Project
from app.services.analysis_service import FailureAnalysisService
from app.schemas.analysis import FailureAnalysisResponse, DefectClusterResponse

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
    response_model=List[FailureAnalysisResponse],
    status_code=status.HTTP_201_CREATED,
)
async def analyze_run_failures(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    commit_sha: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyzes failed test results for a test run and persists diagnostic failure reports & defect clusters."""
    await _verify_project_access(project_id, db)
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
