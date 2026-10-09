"""REST Router for ML Intelligence, Flakiness & Human-in-the-Loop Test Healing."""

import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.domain import User, UserRole, Project, FlakyTestRecordModel, HealingCandidateModel, HealingCandidateStatus
from app.core.security import get_current_user
from app.core.rbac import require_roles
from app.services.ml_service import MLService
from ml.healing.versioning import SpecVersionManager
from app.tasks.ml_tasks import (
    train_prioritization_model_task,
    evaluate_flakiness_task,
    cluster_semantic_defects_task,
    generate_healing_candidates_task
)

router = APIRouter()


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


@router.post("/projects/{project_id}/ml/train")
async def trigger_ml_training(
    project_id: uuid.UUID,
    async_mode: bool = Query(True, description="Run model training asynchronously via Celery"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    if async_mode:
        task = train_prioritization_model_task.delay(str(project_id))
        return {
            "status": "ACCEPTED",
            "message": "ML model training task dispatched to Celery background queue.",
            "task_id": task.id,
        }

    service = MLService(db)
    res = await service.train_project_prioritization_model(project_id)
    return res


@router.get("/projects/{project_id}/ml/prioritize")
async def get_prioritized_test_suite(
    project_id: uuid.UUID,
    strategy: str = Query("BALANCED", description="Ranking strategy: RISK_FIRST, FAST_FEEDBACK, SEVERITY_FIRST, BALANCED"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)
    service = MLService(db)
    items = await service.get_prioritized_test_cases(project_id, strategy=strategy)
    return {
        "project_id": str(project_id),
        "strategy": strategy,
        "total_test_cases": len(items),
        "prioritized_suite": items,
    }


@router.get("/projects/{project_id}/ml/flaky-tests")
async def get_flaky_test_records(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)
    service = MLService(db)
    records = await service.evaluate_project_flakiness(project_id)
    return {
        "project_id": str(project_id),
        "total_evaluated": len(records),
        "flaky_tests": records,
    }


@router.post("/projects/{project_id}/ml/flaky-tests/{test_case_id}/quarantine")
async def toggle_flaky_test_quarantine(
    project_id: uuid.UUID,
    test_case_id: uuid.UUID,
    quarantine: bool = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)
    service = MLService(db)
    res = await service.toggle_quarantine_status(project_id, test_case_id, quarantine=quarantine)
    return res


@router.get("/projects/{project_id}/ml/healing-candidates")
async def list_healing_candidates(
    project_id: uuid.UUID,
    status_filter: Optional[str] = Query("PENDING", description="Filter by status: PENDING, APPROVED, REJECTED"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)
    stmt = select(HealingCandidateModel).where(HealingCandidateModel.project_id == project_id)
    if status_filter:
        stmt = stmt.where(HealingCandidateModel.status == status_filter)

    res = await db.execute(stmt)
    candidates = res.scalars().all()

    return [
        {
            "id": str(c.id),
            "project_id": str(c.project_id),
            "test_case_id": str(c.test_case_id),
            "failure_analysis_id": str(c.failure_analysis_id),
            "source_run_id": str(c.source_run_id),
            "original_specification": c.original_specification,
            "proposed_specification": c.proposed_specification,
            "patch_operations": c.patch_operations,
            "confidence": c.confidence,
            "status": c.status.value,
            "resulting_spec_version": c.resulting_spec_version,
            "rollback_available": c.rollback_available,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in candidates
    ]


@router.post("/projects/{project_id}/ml/healing-candidates/{candidate_id}/apply")
async def approve_and_apply_healing_candidate(
    project_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)
    success, msg, new_spec = await SpecVersionManager.apply_healing_candidate(db, candidate_id, current_user.id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {
        "status": "APPROVED",
        "message": msg,
        "candidate_id": str(candidate_id),
        "new_specification": new_spec,
    }


@router.post("/projects/{project_id}/ml/healing-candidates/{candidate_id}/rollback")
async def rollback_healing_candidate(
    project_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)
    success, msg, reverted_spec = await SpecVersionManager.rollback_healing_candidate(db, candidate_id, current_user.id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {
        "status": "ROLLED_BACK",
        "message": msg,
        "candidate_id": str(candidate_id),
        "reverted_specification": reverted_spec,
    }
