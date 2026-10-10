"""Celery Background Worker Tasks for Phase 10 Analytics, Reports & Benchmark Runs."""

import asyncio
import uuid
from typing import Any, Dict, Optional

from app.core.celery_app import celery_app
from app.db.session import async_session_factory
from app.services.analytics_service import AnalyticsService
from engine.evaluation.ablation_modes import OperationalMode, TestBudget
from engine.evaluation.benchmark_runner import BenchmarkRunner
from engine.analytics.metrics_calculator import QualityScorePolicy
from engine.reporting.html_report_generator import HTMLReportGenerator


def _run_async(coro):
    """Utility to execute async coroutine within Celery worker thread loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.analytics_tasks.run_benchmark_ablation_task")
def run_benchmark_ablation_task(mode_str: str, repetitions: int = 1, seed: int = 42) -> Dict[str, Any]:
    """Background task to run empirical evaluation across operational modes."""
    mode = OperationalMode(mode_str)

    async def _impl():
        report = await BenchmarkRunner.run_evaluation(
            mode=mode,
            budget=TestBudget(max_tests=50, is_constrained=False),
            repetitions=repetitions,
            seed=seed
        )
        async with async_session_factory() as db:
            saved_run = await AnalyticsService.save_benchmark_run(db, report)
            return {
                "benchmark_run_id": str(saved_run.id),
                "mode": saved_run.mode,
                "recall": saved_run.recall,
                "precision": saved_run.precision,
                "f1_score": saved_run.f1_score,
                "true_positives": saved_run.true_positives,
                "total_injected_bugs": saved_run.total_injected_bugs
            }

    return _run_async(_impl())


@celery_app.task(name="app.tasks.analytics_tasks.compile_executive_report_task")
def compile_executive_report_task(
    project_id_str: str,
    project_name: str,
    report_title: str = "Executive Software Quality Audit Report"
) -> Dict[str, Any]:
    """Background task to calculate analytics and generate an executive audit report."""
    project_id = uuid.UUID(project_id_str)

    async def _impl():
        async with async_session_factory() as db:
            analytics = await AnalyticsService.get_project_analytics(db, project_id)
            html_content = HTMLReportGenerator.generate_report_html(
                project_name=project_name,
                analytics_data=analytics,
                report_title=report_title
            )
            saved_report = await AnalyticsService.create_quality_report(
                db=db,
                project_id=project_id,
                title=report_title,
                quality_score=analytics["quality_score"],
                summary_metrics=analytics,
                html_content=html_content
            )
            return {
                "report_id": str(saved_report.id),
                "title": saved_report.title,
                "quality_score": saved_report.quality_score,
                "created_at": saved_report.created_at.isoformat()
            }

    return _run_async(_impl())
