import uuid
from typing import Tuple, List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.domain import (
    Project, ProjectAnalysis, DiscoveredEndpoint, TestSuite, TestCase,
    TestRun, TestResult, User, AuditLog, TestRunStatus
)
from app.services.project_service import get_project_by_id
from engine.generator.suite_generator import SyntheticTestSuiteGenerator
from engine.compiler.test_compiler import TestCompiler
from engine.models.target_env import TargetEnvironmentConfig, EnvironmentType


async def generate_synthetic_suite(
    db: AsyncSession, project_id: uuid.UUID, custom_name: Optional[str], current_user: User
) -> TestSuite:
    project = await get_project_by_id(db, project_id, current_user)

    # Get latest completed project analysis
    stmt_analysis = (
        select(ProjectAnalysis)
        .where(ProjectAnalysis.project_id == project.id)
        .order_by(ProjectAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = (await db.execute(stmt_analysis)).scalar_one_or_none()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate test suite: Project has no static analysis records. Please analyze repository first."
        )

    # Fetch DiscoveredEndpoints for analysis
    stmt_endpoints = select(DiscoveredEndpoint).where(DiscoveredEndpoint.analysis_id == analysis.id)
    endpoints = (await db.execute(stmt_endpoints)).scalars().all()
    if not endpoints:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No API endpoints discovered in static analysis snapshot."
        )

    # Generate TestSpecification objects
    generator = SyntheticTestSuiteGenerator()
    suite_title = custom_name or f"Synthetic Suite v1 ({project.name})"
    specs = generator.generate_suite_for_endpoints(list(endpoints), suite_name=suite_title)

    # Create TestSuite record
    suite = TestSuite(
        project_id=project.id,
        analysis_id=analysis.id,
        name=suite_title,
        description=f"Generated {len(specs)} synthetic test cases from commit {analysis.commit_sha or 'HEAD'}.",
        total_cases=len(specs),
        version="1.0.0",
        is_immutable=True
    )
    db.add(suite)
    await db.flush()

    # Compile into TestCase records
    test_cases = TestCompiler.compile_specifications(suite.id, specs)
    for tc in test_cases:
        db.add(tc)

    audit_entry = AuditLog(
        actor_id=current_user.id,
        action="TEST_SUITE_GENERATED",
        resource_type="TEST_SUITE",
        resource_id=str(suite.id),
        details={"project_id": str(project.id), "total_cases": len(specs)}
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(suite)

    return suite


async def get_project_test_suites(
    db: AsyncSession, project_id: uuid.UUID, current_user: User, page: int = 1, page_size: int = 50
) -> Tuple[List[TestSuite], int]:
    await get_project_by_id(db, project_id, current_user)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    count_stmt = select(func.count(TestSuite.id)).where(TestSuite.project_id == project_id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(TestSuite)
        .where(TestSuite.project_id == project_id)
        .order_by(TestSuite.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), total


async def trigger_test_run(
    db: AsyncSession,
    project_id: uuid.UUID,
    suite_id: uuid.UUID,
    target_base_url: str,
    environment_type: str,
    health_check_path: str,
    current_user: User
) -> TestRun:
    project = await get_project_by_id(db, project_id, current_user)

    stmt_suite = select(TestSuite).where(TestSuite.id == suite_id, TestSuite.project_id == project.id)
    suite = (await db.execute(stmt_suite)).scalar_one_or_none()
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_444_NOT_FOUND if False else status.HTTP_404_NOT_FOUND,
            detail="Test Suite not found for this project."
        )

    env_config = TargetEnvironmentConfig(
        base_url=target_base_url,
        environment_type=EnvironmentType(environment_type) if environment_type in ["LOCAL_SANDBOX", "EXTERNAL"] else EnvironmentType.LOCAL_SANDBOX,
        health_check_path=health_check_path or "/health"
    )

    test_run = TestRun(
        project_id=project.id,
        suite_id=suite.id,
        status=TestRunStatus.PENDING,
        total_tests=suite.total_cases,
        passed_tests=0,
        failed_tests=0,
        error_tests=0,
        duration_ms=0.0,
        target_environment=env_config.to_dict(),
        triggered_by=current_user.id
    )
    db.add(test_run)
    await db.flush()

    audit_entry = AuditLog(
        actor_id=current_user.id,
        action="TEST_RUN_DISPATCHED",
        resource_type="TEST_RUN",
        resource_id=str(test_run.id),
        details={"suite_id": str(suite.id), "target_url": target_base_url}
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(test_run)

    # Dispatch Celery background task
    try:
        from app.tasks.execution_tasks import run_test_suite_execution_task
        run_test_suite_execution_task.delay(str(test_run.id))
    except Exception:
        pass

    return test_run


async def get_project_test_runs(
    db: AsyncSession, project_id: uuid.UUID, current_user: User, page: int = 1, page_size: int = 50
) -> Tuple[List[TestRun], int]:
    await get_project_by_id(db, project_id, current_user)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    count_stmt = select(func.count(TestRun.id)).where(TestRun.project_id == project_id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(TestRun)
        .where(TestRun.project_id == project_id)
        .order_by(TestRun.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), total


async def get_test_run_by_id(
    db: AsyncSession, test_run_id: uuid.UUID, current_user: User
) -> TestRun:
    stmt = select(TestRun).where(TestRun.id == test_run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test Run not found.")

    await get_project_by_id(db, run.project_id, current_user)
    return run


async def get_test_run_results(
    db: AsyncSession, test_run_id: uuid.UUID, current_user: User, page: int = 1, page_size: int = 50
) -> Tuple[List[TestResult], int]:
    run = await get_test_run_by_id(db, test_run_id, current_user)
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    count_stmt = select(func.count(TestResult.id)).where(TestResult.test_run_id == run.id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(TestResult)
        .where(TestResult.test_run_id == run.id)
        .order_by(TestResult.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), total


async def cancel_test_run(
    db: AsyncSession, test_run_id: uuid.UUID, current_user: User
) -> TestRun:
    run = await get_test_run_by_id(db, test_run_id, current_user)

    if run.status in [TestRunStatus.COMPLETED, TestRunStatus.FAILED, TestRunStatus.CANCELLED, TestRunStatus.ENVIRONMENT_ERROR]:
        return run

    run.status = TestRunStatus.CANCELLED
    await db.commit()
    await db.refresh(run)

    # Set Redis cancellation flag
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        r = aioredis.from_url(settings.REDIS_URL)
        await r.set(f"cancel_test_run:{run.id}", "1", ex=3600)
        await r.aclose()
    except Exception:
        pass

    return run
