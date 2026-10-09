"""REST Router for Phase 8 Selective Regression Engine & Change Impact Analysis."""

import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.domain import User, UserRole, Project
from app.core.security import get_current_user
from app.services.regression_service import RegressionService
from app.tasks.regression_tasks import analyze_regression_impact_task

router = APIRouter()


class AnalyzeRegressionRequest(BaseModel):
    base_commit: str = Field(..., description="Base Git commit SHA or ref")
    target_commit: str = Field(..., description="Target Git commit SHA or ref")
    target_branch: Optional[str] = Field("main", description="Target git branch name")
    diff_text: Optional[str] = Field(None, description="Raw unified diff text (optional)")
    async_mode: bool = Field(False, description="Whether to dispatch to Celery background task")


async def _verify_project_access(project_id: uuid.UUID, current_user: User, db: AsyncSession) -> Project:
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to access this project.",
        )

    return project


@router.post("/projects/{project_id}/regression/analyze", status_code=status.HTTP_200_OK)
async def analyze_regression_impact(
    project_id: uuid.UUID,
    request: AnalyzeRegressionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Triggers AST impact analysis and selective regression partitioning for a commit comparison."""
    await _verify_project_access(project_id, current_user, db)

    if request.async_mode:
        task = analyze_regression_impact_task.delay(
            project_id_str=str(project_id),
            base_commit=request.base_commit,
            target_commit=request.target_commit,
            target_branch=request.target_branch or "main",
            diff_text=request.diff_text,
        )
        return {
            "status": "ACCEPTED",
            "message": "Regression analysis task dispatched to Celery background queue.",
            "task_id": task.id,
        }

    service = RegressionService(db)
    result = await service.analyze_regression_impact(
        project_id=project_id,
        base_commit=request.base_commit,
        target_commit=request.target_commit,
        target_branch=request.target_branch,
        diff_text=request.diff_text,
    )
    return result


@router.get("/projects/{project_id}/regression/analyses")
async def list_project_regression_analyses(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists historical selective regression analyses for a project."""
    await _verify_project_access(project_id, current_user, db)
    service = RegressionService(db)
    analyses = await service.list_project_analyses(project_id)
    return {"analyses": analyses}


@router.get("/regression/analyses/{analysis_id}")
async def get_regression_analysis_details(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetches full breakdown of code changes, impacted endpoints, and selective tier partitioning for an analysis."""
    service = RegressionService(db)
    analysis = await service.get_analysis_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regression analysis with ID '{analysis_id}' not found.",
        )
    return analysis
