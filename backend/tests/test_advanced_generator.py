"""
E2E Integration Test Suite for Phase 4 Advanced Rule-Based Generator Engine.
"""

import pytest
import uuid
from httpx import AsyncClient
from app.models.domain import DiscoveredEndpoint, ProjectAnalysis


@pytest.mark.asyncio
async def test_advanced_suite_generation_e2e(client: AsyncClient, dev_headers: dict, db_session):
    # 1. Create project
    create_payload = {
        "name": "Phase 4 Advanced Generator Test Project",
        "description": "Integration testing Phase 4 advanced suite generation pipeline",
        "repository_url": "https://github.com/anshbhogal/email_smtp",
        "default_branch": "main",
        "language_framework": "PYTHON_FASTAPI"
    }
    create_res = await client.post("/api/v1/projects/", json=create_payload, headers=dev_headers)
    assert create_res.status_code == 201
    project_id = create_res.json()["id"]

    # 2. Trigger static analysis
    analyze_res = await client.post(f"/api/v1/projects/{project_id}/analyze", headers=dev_headers)
    assert analyze_res.status_code == 202
    analysis_id = analyze_res.json()["id"]

    # Seed DiscoveredEndpoint with constraints in db
    ep1 = DiscoveredEndpoint(
        analysis_id=uuid.UUID(analysis_id),
        method="POST",
        path="/users",
        function_name="create_user",
        parameters=[
            {"name": "username", "type": "str", "location": "body", "min_length": 3, "max_length": 20},
            {"name": "age", "type": "int", "location": "body", "ge": 18, "le": 60},
            {"name": "score", "type": "float", "location": "body", "gt": 0.0, "lt": 100.0},
            {"name": "role", "type": "str", "location": "body", "enum_values": ["user", "admin"]}
        ],
        request_model="UserCreateSchema",
        response_model="dict",
        framework="PYTHON_FASTAPI",
        confidence=0.98,
        file_path="main.py",
        line_number=15
    )
    db_session.add(ep1)
    await db_session.commit()

    # 3. Trigger Advanced Suite Generation API (HTTP 202 Accepted)
    gen_payload = {
        "name": "Advanced E2E Test Suite v4",
        "preset": "STANDARD",
        "include_happy_path": True,
        "include_boundary_tests": True,
        "include_missing_required": True,
        "include_invalid_types": True,
        "include_format_violations": True,
        "include_security_probes": True,  # Opt-in
        "pairwise_strength": 2,
        "max_cases_per_endpoint": 25,
        "max_total_cases": 200,
        "seed": 42
    }

    gen_res = await client.post(
        f"/api/v1/projects/{project_id}/test-suites/generate-advanced",
        json=gen_payload,
        headers=dev_headers
    )
    assert gen_res.status_code == 202
    job_data = gen_res.json()
    job_id = job_data["id"]
    assert job_data["project_id"] == project_id
    assert job_data["seed"] == 42
    assert "configuration_hash" in job_data

    # 4. Fetch GenerationJob status
    job_detail_res = await client.get(f"/api/v1/generation-jobs/{job_id}", headers=dev_headers)
    assert job_detail_res.status_code == 200
    assert job_detail_res.json()["id"] == job_id

    # 5. Cancel endpoint API test
    cancel_res = await client.post(f"/api/v1/generation-jobs/{job_id}/cancel", headers=dev_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"
