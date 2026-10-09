"""
ASTRA Phase 7 Full End-to-End ML Intelligence & Human-in-the-Loop Healing Integration Test.
Verifies DB -> Feature Store -> XGBoost Prioritization -> Flakiness State Machine ->
Semantic DBSCAN Clustering -> Healing Safety Gate -> REST API Endpoints.
"""

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import (
    User, Project, TestSuite, TestCase, TestRun, TestResult,
    TestRunStatus, TestOutcome, TestType, FailureAnalysisModel,
    FlakyTestRecordModel, HealingCandidateModel, LanguageFramework
)
from app.services.ml_service import MLService
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_phase7_full_e2e_pipeline(db_session: AsyncSession, client: AsyncClient):
    # 1. Setup Test User & Project
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"ml_tester_{user_id.hex[:6]}@example.com",
        full_name="ML Phase 7 Tester",
        hashed_password="hashed_pass_mock",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(user)

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name=f"Phase7_ML_Project_{project_id.hex[:6]}",
        repository_url="https://github.com/example/ml_service",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=user_id,
    )
    db_session.add(project)

    # 2. Setup Test Suite & TestCase
    suite_id = uuid.uuid4()
    suite = TestSuite(
        id=suite_id,
        project_id=project_id,
        name="Phase 7 Suite",
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
            "expected_body": {"status": "ok"},
            "expected_headers": {"content-type": "application/json"},
        },
    )
    db_session.add(test_case)

    # 3. Setup TestRun & TestResult history across multiple runs for dataset & flakiness
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
    test_result = TestResult(
        id=result_id,
        test_run_id=run_id,
        test_case_id=case_id,
        endpoint="/orders",
        method="POST",
        test_type=TestType.HAPPY_PATH,
        outcome=TestOutcome.FAIL,
        status_code=201,
        request_data={"items": ["item1"]},
        response_data={"status": "created"},
        execution_time_ms=150.0,
        error_message="Contract mismatch: expected 200, received 201 Created",
    )
    db_session.add(test_result)

    # Setup FailureAnalysis record
    fa_id = uuid.uuid4()
    fa = FailureAnalysisModel(
        id=fa_id,
        project_id=project_id,
        run_id=run_id,
        test_result_id=str(result_id),
        test_case_id=str(case_id),
        endpoint_id="/orders",
        category="CONTRACT_VIOLATION",
        summary="Status code updated to 201",
        error_message="Contract mismatch: expected 200, received 201 Created",
        evidence=[],
        fault_locations=[],
        root_cause_candidates=[],
        diff_items=[{"diff_type": "STATUS_MISMATCH", "expected": 200, "actual": 201}],
        fingerprint="fp_contract_201_test",
        classification_confidence=1.0,
    )
    db_session.add(fa)
    await db_session.commit()

    # 4. Execute MLService Prioritization & Flakiness
    service = MLService(db_session)
    prioritized = await service.get_prioritized_test_cases(project_id, strategy="BALANCED")
    assert len(prioritized) == 1
    assert prioritized[0]["test_case_id"] == str(case_id)

    flaky_records = await service.evaluate_project_flakiness(project_id)
    assert len(flaky_records) == 1

    # 5. Generate Healing Candidate
    candidates = await service.generate_healing_candidates(project_id, run_id)
    assert len(candidates) == 1
    candidate_id = candidates[0]["id"]
    assert candidates[0]["status"] == "PENDING"

    # 6. Verify REST API Endpoints with JWT Authentication Token
    token = create_access_token(subject=str(user_id))
    headers = {"Authorization": f"Bearer {token}"}

    # GET /projects/{id}/ml/prioritize
    res_p = await client.get(f"/api/v1/projects/{project_id}/ml/prioritize?strategy=BALANCED", headers=headers)
    assert res_p.status_code == 200
    p_json = res_p.json()
    assert len(p_json["prioritized_suite"]) == 1

    # GET /projects/{id}/ml/healing-candidates
    res_hc = await client.get(f"/api/v1/projects/{project_id}/ml/healing-candidates", headers=headers)
    assert res_hc.status_code == 200
    hc_json = res_hc.json()
    assert len(hc_json) == 1
    assert hc_json[0]["id"] == candidate_id

    # POST /projects/{id}/ml/healing-candidates/{id}/apply
    res_app = await client.post(f"/api/v1/projects/{project_id}/ml/healing-candidates/{candidate_id}/apply", headers=headers)
    assert res_app.status_code == 200
    app_json = res_app.json()
    assert app_json["status"] == "APPROVED"
    assert app_json["new_specification"]["expected_status"] == 201

    # POST /projects/{id}/ml/healing-candidates/{id}/rollback
    res_rb = await client.post(f"/api/v1/projects/{project_id}/ml/healing-candidates/{candidate_id}/rollback", headers=headers)
    assert res_rb.status_code == 200
    rb_json = res_rb.json()
    assert rb_json["status"] == "ROLLED_BACK"
    assert rb_json["reverted_specification"]["expected_status"] == 200
