import uuid
from typing import Tuple, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.domain import Project, ProjectAnalysis, DiscoveredEndpoint, User, AuditLog, AnalysisStatus, AnalysisStage
from app.services.project_service import get_project_by_id


async def trigger_project_analysis(
    db: AsyncSession, project_id: uuid.UUID, branch_override: Optional[str], current_user: User
) -> ProjectAnalysis:
    project = await get_project_by_id(db, project_id, current_user)

    target_branch = branch_override or project.default_branch

    # Create new analysis snapshot record in QUEUED status
    analysis = ProjectAnalysis(
        project_id=project.id,
        repository_url=project.repository_url,
        branch=target_branch,
        status=AnalysisStatus.QUEUED,
        current_stage=AnalysisStage.CLONING,
        progress_percent=0,
        scanned_files_count=0,
        parsed_files_count=0,
        endpoint_count=0,
        graph_node_count=0,
        graph_edge_count=0,
        knowledge_graph={"nodes": [], "edges": []},
        analyzer_version="2.0.0"
    )
    db.add(analysis)
    await db.flush()

    audit_entry = AuditLog(
        actor_id=current_user.id,
        action="ANALYSIS_TRIGGERED",
        resource_type="PROJECT_ANALYSIS",
        resource_id=str(analysis.id),
        details={"project_id": str(project.id), "branch": target_branch}
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(analysis)

    # Dispatch Celery background task with asyncio fallback
    try:
        from app.tasks.analyzer_tasks import run_project_analysis_task
        run_project_analysis_task.delay(str(analysis.id))
    except Exception as e:
        import asyncio
        import logging
        logger = logging.getLogger("astra")
        logger.warning(f"Celery dispatch failed ({e}), executing via direct background task.")
        from app.tasks.analyzer_tasks import execute_analysis_pipeline
        asyncio.create_task(execute_analysis_pipeline(str(analysis.id)))

    return analysis


async def get_latest_project_analysis(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> Optional[ProjectAnalysis]:
    await get_project_by_id(db, project_id, current_user) # enforce access control

    stmt = (
        select(ProjectAnalysis)
        .where(ProjectAnalysis.project_id == project_id)
        .order_by(ProjectAnalysis.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_analysis_endpoints(
    db: AsyncSession, project_id: uuid.UUID, current_user: User, page: int = 1, page_size: int = 50
) -> Tuple[List[DiscoveredEndpoint], int]:
    await get_project_by_id(db, project_id, current_user)
    
    # 1. Prefer latest completed analysis with discovered endpoints
    stmt_comp = (
        select(ProjectAnalysis)
        .where(ProjectAnalysis.project_id == project_id)
        .where(ProjectAnalysis.status.in_([AnalysisStatus.COMPLETED, AnalysisStatus.COMPLETED_WITH_WARNINGS]))
        .order_by(ProjectAnalysis.created_at.desc())
        .limit(1)
    )
    res_comp = await db.execute(stmt_comp)
    analysis = res_comp.scalar_one_or_none()

    if not analysis:
        analysis = await get_latest_project_analysis(db, project_id, current_user)

    if not analysis:
        return [], 0

    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    count_stmt = select(func.count(DiscoveredEndpoint.id)).where(DiscoveredEndpoint.analysis_id == analysis.id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(DiscoveredEndpoint)
        .where(DiscoveredEndpoint.analysis_id == analysis.id)
        .order_by(DiscoveredEndpoint.path.asc(), DiscoveredEndpoint.method.asc())
        .offset(offset)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), total


async def get_analysis_graph(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> dict:
    await get_project_by_id(db, project_id, current_user)
    
    # 1. Prefer completed analysis with populated knowledge graph
    stmt_comp = (
        select(ProjectAnalysis)
        .where(ProjectAnalysis.project_id == project_id)
        .where(ProjectAnalysis.status.in_([AnalysisStatus.COMPLETED, AnalysisStatus.COMPLETED_WITH_WARNINGS]))
        .order_by(ProjectAnalysis.created_at.desc())
        .limit(1)
    )
    res_comp = await db.execute(stmt_comp)
    analysis = res_comp.scalar_one_or_none()

    if not analysis or not analysis.knowledge_graph or not analysis.knowledge_graph.get("nodes"):
        analysis = await get_latest_project_analysis(db, project_id, current_user)

    if not analysis or not analysis.knowledge_graph:
        return {"nodes": [], "edges": []}

    return analysis.knowledge_graph


async def get_analysis_functions(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> List[dict]:
    project = await get_project_by_id(db, project_id, current_user)
    analysis = await get_latest_project_analysis(db, project_id, current_user)
    
    # 1. Check if cached in knowledge_graph
    if analysis and analysis.knowledge_graph and "functions" in analysis.knowledge_graph:
        return analysis.knowledge_graph["functions"]

    # 2. Extract dynamically from repo directory
    import os
    repo_dir = None
    candidates = [
        f"/app/scratch/{project.id}",
        f"/app/workspaces/{project.id}/repository",
        "/app/scratch/lecturerag" if "lecturerag" in project.repository_url.lower() else None
    ]
    for c in candidates:
        if c and os.path.exists(c):
            repo_dir = c
            break

    if not repo_dir:
        # Clone repo to scratch if needed
        scratch_dir = f"/app/scratch/{project.id}"
        from engine.analyzer.repo_cloner import GitRepoCloner
        cloner = GitRepoCloner()
        try:
            cloner.clone(project.repository_url, scratch_dir, branch=project.default_branch)
            repo_dir = scratch_dir
        except Exception:
            return []

    from engine.analyzer.function_extractor import FunctionExtractor
    contracts = FunctionExtractor.extract_from_directory(repo_dir)
    func_dicts = [c.to_dict() for c in contracts]

    # Cache in analysis if exists
    if analysis:
        kg = dict(analysis.knowledge_graph or {})
        kg["functions"] = func_dicts
        kg["function_count"] = len(func_dicts)
        analysis.knowledge_graph = kg
        await db.commit()

    return func_dicts


async def run_project_unit_tests(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> dict:
    project = await get_project_by_id(db, project_id, current_user)
    
    import os
    repo_dir = None
    candidates = [
        f"/app/scratch/{project.id}",
        f"/app/workspaces/{project.id}/repository",
        "/app/scratch/lecturerag" if "lecturerag" in project.repository_url.lower() else None
    ]
    for c in candidates:
        if c and os.path.exists(c):
            repo_dir = c
            break

    if not repo_dir:
        scratch_dir = f"/app/scratch/{project.id}"
        from engine.analyzer.repo_cloner import GitRepoCloner
        cloner = GitRepoCloner()
        cloner.clone(project.repository_url, scratch_dir, branch=project.default_branch)
        repo_dir = scratch_dir

    from engine.analyzer.function_extractor import FunctionExtractor
    from engine.execution.unit_test_executor import UnitTestExecutor

    contracts = FunctionExtractor.extract_from_directory(repo_dir)
    if not contracts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No callable functions discovered in this repository for unit testing."
        )

    exec_result = UnitTestExecutor.execute_for_repo(repo_dir, contracts)

    # 1. Cache latest unit run in ProjectAnalysis knowledge graph
    analysis = await get_latest_project_analysis(db, project_id, current_user)
    if analysis:
        kg = dict(analysis.knowledge_graph or {})
        kg["latest_unit_run"] = {
            "total_tests": exec_result.total_tests,
            "passed_tests": exec_result.passed_tests,
            "failed_tests": exec_result.failed_tests,
            "duration_ms": exec_result.duration_ms,
            "exit_code": exec_result.exit_code,
            "test_outcomes": exec_result.test_outcomes
        }
        analysis.knowledge_graph = kg

    # 2. Persist TestSuite & TestRun records for analytics & reports
    try:
        from app.models.domain import (
            TestSuite, TestCase, TestRun, TestResult, TestRunStatus, TestOutcome, TestType, utc_now
        )
        stmt_suite = select(TestSuite).where(
            TestSuite.project_id == project.id,
            TestSuite.name == "Multi-Layer Unit Test Suite"
        )
        suite = (await db.execute(stmt_suite)).scalar_one_or_none()
        if not suite:
            suite = TestSuite(
                project_id=project.id,
                analysis_id=analysis.id if analysis else None,
                name="Multi-Layer Unit Test Suite",
                description="Autonomous spec-grounded invariant and boundary unit test suite.",
                total_cases=exec_result.total_tests,
                version="1.0.0",
                is_immutable=True
            )
            db.add(suite)
            await db.flush()
        else:
            suite.total_cases = exec_result.total_tests

        run_status = TestRunStatus.COMPLETED if exec_result.exit_code == 0 else TestRunStatus.FAILED
        test_run = TestRun(
            project_id=project.id,
            suite_id=suite.id,
            status=run_status,
            total_tests=exec_result.total_tests,
            passed_tests=exec_result.passed_tests,
            failed_tests=exec_result.failed_tests,
            error_tests=exec_result.skipped_tests,
            duration_ms=exec_result.duration_ms,
            target_environment={"type": "SANDBOX_UNIT", "framework": "pytest", "isolation": "0_EGRESS"},
            triggered_by=current_user.id,
            completed_at=utc_now()
        )
        db.add(test_run)
        await db.flush()

        for idx, t in enumerate(exec_result.test_outcomes):
            nodeid = t.get("nodeid") or f"test_unit_{idx}"
            fn_label = nodeid.split("::")[-1]
            test_case = TestCase(
                suite_id=suite.id,
                name=fn_label,
                test_type=TestType.HAPPY_PATH,
                execution_order=idx + 1,
                specification={"nodeid": nodeid, "duration": t.get("duration", 0.0)},
                depends_on=[]
            )
            db.add(test_case)
            await db.flush()

            outcome = TestOutcome.PASS if t.get("outcome") == "passed" else TestOutcome.FAIL
            result_rec = TestResult(
                test_run_id=test_run.id,
                test_case_id=test_case.id,
                endpoint=fn_label,
                method="UNIT",
                test_type=TestType.HAPPY_PATH,
                outcome=outcome,
                status_code=0 if outcome == TestOutcome.PASS else 1,
                request_data={"nodeid": nodeid},
                response_data={"outcome": t.get("outcome")},
                execution_time_ms=round(t.get("duration", 0.0) * 1000, 2),
                assertion_failures=[t.get("crash_message")] if t.get("crash_message") else [],
                error_message=t.get("crash_message")
            )
            db.add(result_rec)

        await db.commit()
    except Exception as e:
        import logging
        logging.getLogger("astra").warning(f"Could not persist unit test run to DB: {e}")

    return {
        "total_tests": exec_result.total_tests,
        "passed_tests": exec_result.passed_tests,
        "failed_tests": exec_result.failed_tests,
        "skipped_tests": exec_result.skipped_tests,
        "duration_ms": exec_result.duration_ms,
        "coverage_percent": exec_result.coverage_percent,
        "test_outcomes": exec_result.test_outcomes,
        "raw_stdout": exec_result.raw_stdout,
        "exit_code": exec_result.exit_code
    }
