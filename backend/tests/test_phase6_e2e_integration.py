"""
ASTRA Phase 6.5 Full End-to-End Pipeline Integration Test.
Verifies DB -> TestCase.specification -> TestResult -> FailureAnalysisService -> RootCauseAnalyzer ->
FailureAnalysisModel + DefectClusterModel -> REST API JSON serialization.
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.session import async_session_factory
from app.models.domain import (
    User, Project, TestSuite, TestCase, TestRun, TestResult,
    TestRunStatus, TestOutcome, TestType, FailureAnalysisModel, DefectClusterModel, LanguageFramework
)
from app.services.analysis_service import FailureAnalysisService
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_phase6_full_e2e_pipeline(db_session: AsyncSession, client: AsyncClient):
    # 1. Setup Test User
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"tester_{user_id.hex[:6]}@example.com",
        full_name="E2E Phase 6 Tester",
        hashed_password="hashed_pass_mock",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(user)

    # 2. Setup Project
    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name=f"E2E_Test_Project_{project_id.hex[:6]}",
        repository_url="https://github.com/example/orders_service",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=user_id,
    )
    db_session.add(project)

    # 3. Setup Test Suite & TestCase with real specification expectations
    suite_id = uuid.uuid4()
    suite = TestSuite(
        id=suite_id,
        project_id=project_id,
        name="Orders E2E Test Suite",
        total_cases=1,
    )
    db_session.add(suite)

    case_id = uuid.uuid4()
    test_case = TestCase(
        id=case_id,
        suite_id=suite_id,
        name="Create Order Test Case",
        test_type=TestType.HAPPY_PATH,
        execution_order=1,
        specification={
            "expected_status": 200,
            "expected_body": {"status": "ok", "total_amount": 500},
            "expected_headers": {"content-type": "application/json"},
            "max_latency_ms": 1000.0,
        },
    )
    db_session.add(test_case)

    # 4. Setup TestRun & failed TestResult
    run_id = uuid.uuid4()
    test_run = TestRun(
        id=run_id,
        project_id=project_id,
        suite_id=suite_id,
        status=TestRunStatus.COMPLETED,
        total_tests=1,
        failed_tests=1,
        triggered_by=user_id,
    )
    db_session.add(test_run)

    result_id = uuid.uuid4()
    raw_trace = """Traceback (most recent call last):
  File "/app/services/orders.py", line 143, in calculate_total
    discount = payload['discount']
KeyError: 'discount'"""

    test_result = TestResult(
        id=result_id,
        test_run_id=run_id,
        test_case_id=case_id,
        endpoint="/orders",
        method="POST",
        test_type=TestType.HAPPY_PATH,
        outcome=TestOutcome.FAIL,
        status_code=500,
        request_data={"items": ["item1"]},
        response_data={"detail": "Internal Server Error: KeyError 'discount'"},
        execution_time_ms=120.0,
        error_message=raw_trace,
    )
    db_session.add(test_result)
    await db_session.commit()

    # 5. Execute FailureAnalysisService
    service = FailureAnalysisService(db_session)
    analyses = await service.analyze_run_failures(
        project_id=project_id,
        run_id=run_id,
        target_commit_sha="abc123commit",
    )

    assert len(analyses) == 1
    fa = analyses[0]
    assert fa.category == "SERVER_CRASH"
    assert fa.exception_type == "KeyError"
    assert fa.failing_file == "/app/services/orders.py"
    assert fa.failing_line == 143
    assert fa.failing_function == "calculate_total"
    assert fa.commit_sha == "abc123commit"
    assert len(fa.evidence) >= 2
    assert len(fa.fault_locations) == 1
    assert len(fa.root_cause_candidates) >= 1

    # Verify DefectCluster created in DB
    cl_stmt = select(DefectClusterModel).where(DefectClusterModel.project_id == project_id)
    cl_res = await db_session.execute(cl_stmt)
    clusters = cl_res.scalars().all()
    assert len(clusters) == 1
    assert clusters[0].fingerprint == fa.fingerprint
    assert clusters[0].occurrence_count == 1

    # 6. Verify REST API endpoints with JWT authentication token
    token = create_access_token(subject=str(user_id))
    headers = {"Authorization": f"Bearer {token}"}

    # GET /failure-analysis
    res_fa = await client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/failure-analysis",
        headers=headers,
    )
    assert res_fa.status_code == 200
    fa_json = res_fa.json()
    assert len(fa_json) == 1
    assert fa_json[0]["category"] == "SERVER_CRASH"
    assert fa_json[0]["failing_file"] == "/app/services/orders.py"
    assert fa_json[0]["failing_line"] == 143

    # GET /defects
    res_def = await client.get(
        f"/api/v1/projects/{project_id}/defects",
        headers=headers,
    )
    assert res_def.status_code == 200
    def_json = res_def.json()
    assert len(def_json) == 1
    assert def_json[0]["fingerprint"] == fa.fingerprint
    assert def_json[0]["occurrence_count"] == 1

