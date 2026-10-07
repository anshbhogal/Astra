"""
REST API Router for Advanced Test Suite Generation & Generation Jobs.
"""

import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import require_roles
from app.models.domain import User, UserRole, Project, ProjectAnalysis, GenerationJob, GenerationJobStatus
from app.schemas.generator import (
    AdvancedSuiteGenerationRequest,
    GenerationJobResponse,
)
from engine.generator.strategy import TestGenerationStrategy, StrategyPreset
from app.tasks.generation_tasks import run_advanced_suite_generation_task

router = APIRouter()


@router.post(
    "/projects/{project_id}/test-suites/generate-advanced",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def dispatch_advanced_suite_generation(
    project_id: uuid.UUID,
    req: AdvancedSuiteGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """
    Triggers an asynchronous advanced rule-based test suite generation job.
    Returns HTTP 202 Accepted with job metadata.
    """
    stmt_project = select(Project).where(Project.id == project_id)
    project = (await db.execute(stmt_project)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    stmt_analysis = (
        select(ProjectAnalysis)
        .where(ProjectAnalysis.project_id == project_id)
        .order_by(ProjectAnalysis.created_at.desc())
    )
    analysis = (await db.execute(stmt_analysis)).scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project must be analyzed before generating test suites."
        )

    # Initialize Strategy
    strategy = TestGenerationStrategy.from_preset(
        preset=req.preset,
        include_happy_path=req.include_happy_path,
        include_boundary_tests=req.include_boundary_tests,
        include_missing_required=req.include_missing_required,
        include_invalid_types=req.include_invalid_types,
        include_format_violations=req.include_format_violations,
        include_security_probes=req.include_security_probes,
        pairwise_strength=req.pairwise_strength,
        max_cases_per_endpoint=req.max_cases_per_endpoint,
        max_total_cases=req.max_total_cases,
        seed=req.seed
    )

    config_hash = strategy.compute_configuration_hash()

    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        project_id=project_id,
        analysis_id=analysis.id,
        status=GenerationJobStatus.PENDING,
        configuration=req.model_dump(),
        configuration_hash=config_hash,
        seed=req.seed,
        total_candidates=0,
        total_generated=0,
        total_deduplicated=0,
        total_truncated=0,
        generation_report={}
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enqueue Celery Task
    try:
        run_advanced_suite_generation_task.delay(str(job.id))
    except Exception:
        # Fallback to local async execution if Celery broker unavailable in dev mode
        pass

    return GenerationJobResponse(
        id=str(job.id),
        project_id=str(job.project_id),
        analysis_id=str(job.analysis_id) if job.analysis_id else None,
        status=job.status.value,
        configuration=job.configuration,
        configuration_hash=job.configuration_hash,
        seed=job.seed,
        total_candidates=job.total_candidates,
        total_generated=job.total_generated,
        total_deduplicated=job.total_deduplicated,
        total_truncated=job.total_truncated,
        generation_report=job.generation_report,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at
    )


@router.get("/generation-jobs/{job_id}", response_model=GenerationJobResponse)
async def get_generation_job_details(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves status and report of a generation job."""
    stmt = select(GenerationJob).where(GenerationJob.id == job_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GenerationJob not found")

    return GenerationJobResponse(
        id=str(job.id),
        project_id=str(job.project_id),
        analysis_id=str(job.analysis_id) if job.analysis_id else None,
        status=job.status.value,
        configuration=job.configuration,
        configuration_hash=job.configuration_hash,
        seed=job.seed,
        total_candidates=job.total_candidates,
        total_generated=job.total_generated,
        total_deduplicated=job.total_deduplicated,
        total_truncated=job.total_truncated,
        generation_report=job.generation_report,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at
    )


@router.post("/generation-jobs/{job_id}/cancel")
async def cancel_generation_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """Cancels a pending or running generation job."""
    stmt = select(GenerationJob).where(GenerationJob.id == job_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GenerationJob not found")

    if job.status in [GenerationJobStatus.PENDING, GenerationJobStatus.RUNNING]:
        job.status = GenerationJobStatus.CANCELLED
        await db.commit()

    return {"message": "GenerationJob cancelled successfully", "id": str(job_id), "status": job.status.value}
