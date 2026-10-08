"""
ASTRA Backend - Phase 6 Celery Analysis Tasks

Background Celery tasks for asynchronous failure diagnosis and defect clustering.
"""

import uuid
import asyncio
from typing import Dict, Any, Optional

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.analysis_service import FailureAnalysisService
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


async def _run_failure_analysis_async(
    project_id_str: str,
    run_id_str: str,
    commit_sha: Optional[str] = None,
) -> int:
    project_id = uuid.UUID(project_id_str)
    run_id = uuid.UUID(run_id_str)

    task_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TaskSessionLocal = async_sessionmaker(bind=task_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with TaskSessionLocal() as db:
            service = FailureAnalysisService(db)
            reports = await service.analyze_run_failures(
                project_id=project_id,
                run_id=run_id,
                target_commit_sha=commit_sha,
            )
            return len(reports)
    finally:
        await task_engine.dispose()


@celery_app.task(name="analysis.analyze_test_run_failures", bind=True, max_retries=3)
def analyze_test_run_failures_task(
    self,
    project_id_str: str,
    run_id_str: str,
    commit_sha: Optional[str] = None,
) -> Dict[str, Any]:
    """Celery background task analyzing failed test results for a test run."""
    try:
        count = asyncio.run(_run_failure_analysis_async(project_id_str, run_id_str, commit_sha))
        return {
            "status": "COMPLETED",
            "project_id": project_id_str,
            "run_id": run_id_str,
            "analyzed_failures_count": count,
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)
