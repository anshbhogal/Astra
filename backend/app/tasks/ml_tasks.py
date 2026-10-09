"""Celery Background Tasks for ML Model Training, Flakiness & Healing."""

import asyncio
import uuid
from typing import Dict, Any

from app.core.celery_app import celery_app
from app.db.session import async_session_factory
from app.services.ml_service import MLService


def _run_async(coro):
    """Utility to execute async coroutine within Celery worker thread loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.ml_tasks.train_prioritization_model_task")
def train_prioritization_model_task(project_id_str: str, version: str = "v1.0") -> Dict[str, Any]:
    """Celery task training XGBoost test prioritizer model."""
    project_id = uuid.UUID(project_id_str)

    async def _impl():
        async with async_session_factory() as db:
            service = MLService(db)
            return await service.train_project_prioritization_model(project_id, version=version)

    return _run_async(_impl())


@celery_app.task(name="app.tasks.ml_tasks.evaluate_flakiness_task")
def evaluate_flakiness_task(project_id_str: str) -> Dict[str, Any]:
    """Celery task evaluating flakiness histories and recommendations."""
    project_id = uuid.UUID(project_id_str)

    async def _impl():
        async with async_session_factory() as db:
            service = MLService(db)
            records = await service.evaluate_project_flakiness(project_id)
            return {"status": "COMPLETED", "flaky_count": len(records), "records": records}

    return _run_async(_impl())


@celery_app.task(name="app.tasks.ml_tasks.cluster_semantic_defects_task")
def cluster_semantic_defects_task(project_id_str: str, run_id_str: str) -> Dict[str, Any]:
    """Celery task clustering failure traces semantically using TF-IDF + Cosine DBSCAN."""
    project_id = uuid.UUID(project_id_str)
    run_id = uuid.UUID(run_id_str)

    async def _impl():
        async with async_session_factory() as db:
            service = MLService(db)
            clusters = await service.cluster_run_failures_semantic(project_id, run_id)
            return {"status": "COMPLETED", "cluster_count": len(clusters), "clusters": clusters}

    return _run_async(_impl())


@celery_app.task(name="app.tasks.ml_tasks.generate_healing_candidates_task")
def generate_healing_candidates_task(project_id_str: str, run_id_str: str) -> Dict[str, Any]:
    """Celery task generating safety-validated test specification healing candidates."""
    project_id = uuid.UUID(project_id_str)
    run_id = uuid.UUID(run_id_str)

    async def _impl():
        async with async_session_factory() as db:
            service = MLService(db)
            candidates = await service.generate_healing_candidates(project_id, run_id)
            return {"status": "COMPLETED", "candidate_count": len(candidates), "candidates": candidates}

    return _run_async(_impl())
