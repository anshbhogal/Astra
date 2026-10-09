"""Celery Background Tasks for Phase 8 Selective Regression Engine."""

import asyncio
import uuid
from typing import Dict, Any, Optional

from app.core.celery_app import celery_app
from app.db.session import async_session_factory
from app.services.regression_service import RegressionService


def _run_async(coro):
    """Utility to execute async coroutine within Celery worker thread loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.regression_tasks.analyze_regression_impact_task")
def analyze_regression_impact_task(
    project_id_str: str,
    base_commit: str,
    target_commit: str,
    target_branch: str = "main",
    diff_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Celery task running async AST impact analysis and selective test partitioning."""
    project_id = uuid.UUID(project_id_str)

    async def _impl():
        async with async_session_factory() as db:
            service = RegressionService(db)
            return await service.analyze_regression_impact(
                project_id=project_id,
                base_commit=base_commit,
                target_commit=target_commit,
                target_branch=target_branch,
                diff_text=diff_text,
            )

    return _run_async(_impl())
