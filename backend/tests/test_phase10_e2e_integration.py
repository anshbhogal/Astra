"""ASTRA Phase 10 End-to-End Analytics, Reporting & Benchmark Integration Test.

Verifies:
1. Platform Overview Analytics API
2. Project-Level Quality Analytics & Historical Trends API
3. Executive Audit Report Generation & Export (HTML & PDF)
4. Benchmark Bug Catalog API (50 bugs + 100 negative controls)
5. Benchmark Ablation Study Run Execution & PostgreSQL Persistence
6. Ablation Comparison Matrix API
7. "Why did ASTRA detect this bug?" Traceability Drilldown API
"""

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import User, Project, LanguageFramework, TestRun, TestRunStatus
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_phase10_full_e2e_analytics_and_benchmarks(db_session: AsyncSession, client: AsyncClient):
    # 1. Setup Test User and Project
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"phase10_tester_{user_id.hex[:6]}@example.com",
        full_name="Phase 10 Evaluator",
        hashed_password="hashed_pass_mock",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(user)

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name="Phase 10 Benchmark Target Service",
        repository_url="https://github.com/astra-quality/benchmark-app.git",
        default_branch="main",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=user_id,
    )
    db_session.add(project)

    # Add a sample TestRun for project analytics
    run_id = uuid.uuid4()
    test_run = TestRun(
        id=run_id,
        project_id=project_id,
        suite_id=project_id,
        status=TestRunStatus.COMPLETED,
        total_tests=50,
        passed_tests=45,
        failed_tests=5,
        error_tests=0,
        duration_ms=1200.0,
        target_environment={"env": "local"}
    )
    db_session.add(test_run)
    await db_session.commit()

    token = create_access_token(subject=str(user_id))
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test Platform Overview Analytics
    resp_overview = await client.get("/api/v1/analytics/overview", headers=headers)
    assert resp_overview.status_code == 200
    overview_data = resp_overview.json()
    assert "total_projects" in overview_data
    assert "total_test_runs" in overview_data
    assert "overall_pass_rate" in overview_data

    # 3. Test Project Quality Analytics
    resp_analytics = await client.get(f"/api/v1/analytics/projects/{project_id}?time_range=30d", headers=headers)
    assert resp_analytics.status_code == 200
    analytics_data = resp_analytics.json()
    assert analytics_data["project_id"] == str(project_id)
    assert "quality_score" in analytics_data
    assert analytics_data["test_pass_rate"] == 90.0
    assert analytics_data["passed_tests"] == 45
    assert analytics_data["failed_tests"] == 5
    assert "pass_rate_trend" in analytics_data

    # 4. Test Executive Quality Report Generation
    resp_report = await client.post(
        f"/api/v1/analytics/projects/{project_id}/reports",
        json={"title": "Q4 Comprehensive Software Quality Audit"},
        headers=headers
    )
    assert resp_report.status_code == 200
    report_data = resp_report.json()
    assert "id" in report_data
    assert report_data["title"] == "Q4 Comprehensive Software Quality Audit"
    assert "sha256_hash" in report_data
    report_id = report_data["id"]

    # 5. Test List Project Reports
    resp_list_reports = await client.get(f"/api/v1/analytics/projects/{project_id}/reports", headers=headers)
    assert resp_list_reports.status_code == 200
    reports_list = resp_list_reports.json()
    assert len(reports_list) >= 1
    assert any(r["id"] == report_id for r in reports_list)

    # 6. Test Export Quality Report (HTML & PDF)
    resp_export_html = await client.get(f"/api/v1/analytics/reports/{report_id}/export?format=html", headers=headers)
    assert resp_export_html.status_code == 200
    assert "text/html" in resp_export_html.headers.get("content-type", "")
    assert "ASTRA QUALITY AUDIT" in resp_export_html.text

    resp_export_pdf = await client.get(f"/api/v1/analytics/reports/{report_id}/export?format=pdf", headers=headers)
    assert resp_export_pdf.status_code == 200
    assert len(resp_export_pdf.content) > 0

    # 7. Test Benchmark Bug Catalog API
    resp_bugs = await client.get("/api/v1/benchmarks/bugs", headers=headers)
    assert resp_bugs.status_code == 200
    bugs_data = resp_bugs.json()
    assert bugs_data["total_bugs"] == 50
    assert bugs_data["total_negative_controls"] == 100
    assert len(bugs_data["bugs"]) == 50

    # Filter by service
    resp_auth_bugs = await client.get("/api/v1/benchmarks/bugs?service=auth", headers=headers)
    assert resp_auth_bugs.status_code == 200
    assert resp_auth_bugs.json()["total_bugs"] == 10

    # 8. Test Trigger Benchmark Evaluation Run (Mode D: Hybrid ASTRA)
    resp_run = await client.post(
        "/api/v1/benchmarks/run",
        json={"mode": "MODE_D_HYBRID", "repetitions": 1, "seed": 42},
        headers=headers
    )
    assert resp_run.status_code == 200
    run_data = resp_run.json()
    assert run_data["mode"] == "MODE_D_HYBRID"
    assert run_data["status"] == "COMPLETED"
    assert run_data["total_injected_bugs"] == 50
    assert run_data["true_positives"] > 0
    assert run_data["recall"] > 80.0
    benchmark_run_id = run_data["id"]

    # 9. Test Latest Ablation Matrix API
    resp_matrix = await client.get("/api/v1/benchmarks/latest", headers=headers)
    assert resp_matrix.status_code == 200
    matrix_data = resp_matrix.json()
    assert "matrix" in matrix_data
    assert len(matrix_data["matrix"]) >= 1

    # 10. Test Benchmark Run Details API
    resp_details = await client.get(f"/api/v1/benchmarks/runs/{benchmark_run_id}", headers=headers)
    assert resp_details.status_code == 200
    details_data = resp_details.json()
    assert details_data["id"] == benchmark_run_id
    assert len(details_data["bug_results"]) == 50

    # 11. Test "Why did ASTRA detect this bug?" Traceability API
    resp_trace = await client.get("/api/v1/benchmarks/bugs/BUG-AUTH-001/trace", headers=headers)
    assert resp_trace.status_code == 200
    trace_data = resp_trace.json()
    assert trace_data["bug_id"] == "BUG-AUTH-001"
    assert "latest_execution" in trace_data
    assert trace_data["latest_execution"]["is_detected"] is True
    assert "detection_signatures" in trace_data
