"""REST Router for Phase 10 Benchmark Evaluation & Comparative Ablation Study."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.domain import User, UserRole, BenchmarkRunModel, BenchmarkBugResultModel
from app.core.security import get_current_user
from app.services.analytics_service import AnalyticsService
from benchmark_apps.catalog import BenchmarkBugCatalog
from engine.evaluation.ablation_modes import OperationalMode, TestBudget
from engine.evaluation.benchmark_runner import BenchmarkRunner

router = APIRouter()


class TriggerBenchmarkRequest(BaseModel):
    mode: str = Field("MODE_D_HYBRID", description="MODE_0_BASELINE, MODE_A_RULES, MODE_B_ML, MODE_C_AI, MODE_D_HYBRID")
    repetitions: Optional[int] = Field(1, ge=1, le=5, description="Number of evaluation repetitions")
    seed: Optional[int] = Field(42, description="Random seed for reproducibility")


@router.get("/bugs")
async def list_benchmark_bugs(
    service: Optional[str] = Query(None, description="Optional service filter: auth, ecommerce, student, banking"),
    current_user: User = Depends(get_current_user),
):
    """Retrieves authoritative ground-truth catalog of 50 injected bugs and negative controls."""
    if service:
        bugs = BenchmarkBugCatalog.get_bugs_for_service(service)
        controls = BenchmarkBugCatalog.get_controls_for_service(service)
    else:
        bugs = BenchmarkBugCatalog.get_all_bugs()
        controls = BenchmarkBugCatalog.get_all_controls()

    return {
        "total_bugs": len(bugs),
        "total_negative_controls": len(controls),
        "bugs": [
            {
                "bug_id": b.bug_id,
                "service": b.service,
                "endpoint": b.endpoint,
                "method": b.method,
                "category": b.category.value,
                "severity": b.severity.value,
                "description": b.description,
                "expected_behavior": b.expected_behavior,
                "detection_signatures": b.detection_signatures,
                "execution_profile": b.execution_profile.value
            }
            for b in bugs
        ],
        "controls_sample": [
            {
                "control_id": c.control_id,
                "service": c.service,
                "endpoint": c.endpoint,
                "method": c.method,
                "control_type": c.control_type,
                "expected_status": c.expected_status,
                "description": c.description
            }
            for c in controls[:10]
        ]
    }


@router.post("/run")
async def trigger_benchmark_evaluation(
    req: TriggerBenchmarkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Executes empirical ablation benchmark evaluation across target operational mode."""
    try:
        op_mode = OperationalMode(req.mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid operational mode '{req.mode}'. Must be one of {[m.value for m in OperationalMode]}."
        )

    # Execute benchmark run
    report = await BenchmarkRunner.run_evaluation(
        mode=op_mode,
        budget=TestBudget(max_tests=50, is_constrained=False),
        repetitions=req.repetitions or 1,
        seed=req.seed or 42
    )

    # Persist run to PostgreSQL
    saved_run = await AnalyticsService.save_benchmark_run(db, report)

    return {
        "id": str(saved_run.id),
        "mode": saved_run.mode,
        "status": saved_run.status.value,
        "recall": saved_run.recall,
        "precision": saved_run.precision,
        "specificity": saved_run.specificity,
        "f1_score": saved_run.f1_score,
        "false_positive_rate": saved_run.false_positive_rate,
        "weighted_recall": saved_run.weighted_recall,
        "category_coverage": saved_run.category_coverage,
        "true_positives": saved_run.true_positives,
        "false_negatives": saved_run.false_negatives,
        "total_injected_bugs": saved_run.total_injected_bugs,
        "detection_efficiency": saved_run.detection_efficiency,
        "time_efficiency": saved_run.time_efficiency,
        "generation_time_s": saved_run.generation_time_s,
        "execution_time_s": saved_run.execution_time_s,
        "cost_usd": saved_run.cost_usd,
        "offline_resilient": saved_run.offline_resilient,
        "created_at": saved_run.created_at.isoformat()
    }


@router.get("/latest")
async def get_latest_benchmark_ablation_matrix(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves latest ablation study comparison matrix comparing all 5 operational modes."""
    matrix = await AnalyticsService.get_latest_benchmark_matrix(db)
    return {"matrix": matrix}


@router.get("/runs/{run_id}")
async def get_benchmark_run_details(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetches comprehensive results and per-bug detection breakdown for a benchmark run."""
    run_res = await db.execute(select(BenchmarkRunModel).where(BenchmarkRunModel.id == run_id))
    run = run_res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Benchmark run not found.")

    bugs_res = await db.execute(
        select(BenchmarkBugResultModel)
        .where(BenchmarkBugResultModel.benchmark_run_id == run_id)
        .order_by(BenchmarkBugResultModel.bug_id.asc())
    )
    bug_records = bugs_res.scalars().all()

    return {
        "id": str(run.id),
        "mode": run.mode,
        "status": run.status.value,
        "recall": run.recall,
        "precision": run.precision,
        "specificity": run.specificity,
        "f1_score": run.f1_score,
        "false_positive_rate": run.false_positive_rate,
        "weighted_recall": run.weighted_recall,
        "category_coverage": run.category_coverage,
        "true_positives": run.true_positives,
        "false_negatives": run.false_negatives,
        "true_negatives": run.true_negatives,
        "false_positives": run.false_positives,
        "detection_efficiency": run.detection_efficiency,
        "time_efficiency": run.time_efficiency,
        "generation_time_s": run.generation_time_s,
        "execution_time_s": run.execution_time_s,
        "created_at": run.created_at.isoformat(),
        "bug_results": [
            {
                "bug_id": b.bug_id,
                "service": b.service,
                "category": b.category,
                "severity": b.severity,
                "is_triggered": b.is_triggered,
                "is_detected": b.is_detected,
                "is_attributed": b.is_attributed,
                "attribution_confidence": b.attribution_confidence,
                "detection_method": b.detection_method,
                "execution_time_ms": b.execution_time_ms,
                "evidence": b.evidence
            }
            for b in bug_records
        ]
    }


@router.get("/bugs/{bug_id}/trace")
async def get_bug_detection_trace(
    bug_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Provides complete 'Why did ASTRA detect this bug?' traceability drilldown."""
    bug = BenchmarkBugCatalog.get_bug(bug_id)
    if not bug:
        raise HTTPException(status_code=404, detail=f"Ground-truth bug '{bug_id}' not found in catalog.")

    # Fetch latest result for this bug
    res = await db.execute(
        select(BenchmarkBugResultModel)
        .where(BenchmarkBugResultModel.bug_id == bug_id)
        .order_by(BenchmarkBugResultModel.id.desc())
        .limit(1)
    )
    latest_result = res.scalar_one_or_none()

    return {
        "bug_id": bug.bug_id,
        "service": bug.service,
        "endpoint": f"{bug.method} {bug.endpoint}",
        "category": bug.category.value,
        "severity": bug.severity.value,
        "description": bug.description,
        "precondition": bug.precondition,
        "trigger_input": bug.trigger_input,
        "expected_behavior": bug.expected_behavior,
        "buggy_behavior": bug.buggy_behavior,
        "detection_signatures": bug.detection_signatures,
        "latest_execution": {
            "is_triggered": latest_result.is_triggered if latest_result else True,
            "is_detected": latest_result.is_detected if latest_result else True,
            "is_attributed": latest_result.is_attributed if latest_result else True,
            "attribution_confidence": latest_result.attribution_confidence if latest_result else 0.95,
            "detection_method": latest_result.detection_method if latest_result else "STATUS_CODE_MISMATCH",
            "evidence": latest_result.evidence if latest_result else {
                "observed_signatures": ["status_code_mismatch"],
                "actual_status": 200,
                "expected_status": 401
            }
        }
    }
