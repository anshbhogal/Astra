"""
Celery Worker Tasks for Advanced Test Suite Generation.
"""

import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.domain import (
    GenerationJob, GenerationJobStatus, ProjectAnalysis, DiscoveredEndpoint, TestSuite, TestCase
)
from sqlalchemy import select

from engine.generator.strategy import TestGenerationStrategy
from engine.generator.advanced_suite_generator import AdvancedTestSuiteGenerator
from engine.compiler.test_compiler import TestCompiler


def utc_now():
    return datetime.now(timezone.utc)


from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

async def execute_generation_job_pipeline(job_id_str: str) -> None:
    job_id = uuid.UUID(job_id_str)

    task_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    TaskSessionLocal = async_sessionmaker(bind=task_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with TaskSessionLocal() as db:
            stmt = select(GenerationJob).where(GenerationJob.id == job_id)
            result = await db.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                return

        try:
            job.status = GenerationJobStatus.RUNNING
            await db.commit()

            # 1. Fetch analysis & endpoints
            stmt_analysis = (
                select(ProjectAnalysis)
                .where(ProjectAnalysis.project_id == job.project_id)
                .order_by(ProjectAnalysis.created_at.desc())
            )
            analysis = (await db.execute(stmt_analysis)).scalars().first()

            if not analysis:
                job.status = GenerationJobStatus.FAILED
                job.error_message = "No ProjectAnalysis found for project."
                job.completed_at = utc_now()
                await db.commit()
                return

            job.analysis_id = analysis.id

            stmt_eps = select(DiscoveredEndpoint).where(DiscoveredEndpoint.analysis_id == analysis.id)
            endpoints = (await db.execute(stmt_eps)).scalars().all()

            if not endpoints:
                job.status = GenerationJobStatus.FAILED
                job.error_message = "No DiscoveredEndpoints found in project analysis."
                job.completed_at = utc_now()
                await db.commit()
                return

            # 2. Build Strategy Config
            cfg_dict = job.configuration or {}
            strategy = TestGenerationStrategy(
                include_happy_path=cfg_dict.get("include_happy_path", True),
                include_boundary_tests=cfg_dict.get("include_boundary_tests", True),
                include_missing_required=cfg_dict.get("include_missing_required", True),
                include_invalid_types=cfg_dict.get("include_invalid_types", True),
                include_format_violations=cfg_dict.get("include_format_violations", True),
                include_security_probes=cfg_dict.get("include_security_probes", False),
                pairwise_strength=cfg_dict.get("pairwise_strength", 2),
                max_cases_per_endpoint=cfg_dict.get("max_cases_per_endpoint", 20),
                max_total_cases=cfg_dict.get("max_total_cases", 500),
                seed=job.seed
            )

            # 3. Generate Specs
            generator = AdvancedTestSuiteGenerator()
            specs, report = generator.generate_suite_for_endpoints(endpoints, strategy, suite_name=cfg_dict.get("name", "Advanced Suite"))

            # 4. Save TestSuite & TestCases in DB
            suite_id = uuid.uuid4()
            suite = TestSuite(
                id=suite_id,
                project_id=job.project_id,
                name=cfg_dict.get("name", "Advanced Synthetic Suite"),
                description=f"Advanced generated suite (Seed: {job.seed}, Strategy: {strategy.preset.value})",
                analysis_id=analysis.id,
                total_cases=len(specs)
            )
            db.add(suite)

            test_cases = TestCompiler.compile_specs_to_test_cases(specs, suite_id)
            for tc in test_cases:
                db.add(tc)

            # 5. Update Job Record
            job.status = GenerationJobStatus.COMPLETED
            job.total_candidates = report.get("total_candidates", len(specs))
            job.total_generated = report.get("total_generated", len(specs))
            job.total_deduplicated = report.get("total_deduplicated", 0)
            job.total_truncated = report.get("total_truncated", 0)
            job.generation_report = report
            job.completed_at = utc_now()

            await db.commit()

        except Exception as exc:
            job.status = GenerationJobStatus.FAILED
            job.error_message = f"Generation Pipeline Failure: {str(exc)}"
            job.completed_at = utc_now()
            await db.commit()
    finally:
        await task_engine.dispose()


@celery_app.task(name="tasks.run_advanced_suite_generation_task")
def run_advanced_suite_generation_task(job_id_str: str) -> None:
    """Celery task entry point for advanced test suite generation."""
    asyncio.run(execute_generation_job_pipeline(job_id_str))
