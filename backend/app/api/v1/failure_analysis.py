"""
ASTRA Backend - Phase 6 Failure Analysis & Defect REST API Router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.session import get_db
from app.services.analysis_service import FailureAnalysisService
from app.schemas.analysis import FailureAnalysisResponse, DefectClusterResponse

router = APIRouter(prefix="/projects", tags=["Failure Analysis & Defects"])


@router.post(
    "/{project_id}/runs/{run_id}/failure-analysis/analyze",
    response_model=List[FailureAnalysisResponse],
    status_code=status.HTTP_201_CREATED,
)
async def analyze_run_failures(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    commit_sha: str = None,
    db: AsyncSession = Depends(get_db),
):
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
):
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
):
    service = FailureAnalysisService(db)
    defects = await service.get_project_defects(project_id)
    return defects
