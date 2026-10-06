import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_execution_engine_flow(client: AsyncClient, dev_headers: dict):
    # 1. Create project
    create_payload = {
        "name": "Target App Test Execution Project",
        "description": "Integration testing execution engine flow",
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

    # 3. Generate synthetic test suite
    suite_res = await client.post(
        f"/api/v1/projects/{project_id}/test-suites/generate",
        json={"name": "Integration Suite v1"},
        headers=dev_headers
    )
    assert suite_res.status_code == 201
    suite_data = suite_res.json()
    suite_id = suite_data["id"]
    assert suite_data["project_id"] == project_id
    assert suite_data["total_cases"] > 0

    # 4. List test suites
    suites_list_res = await client.get(f"/api/v1/projects/{project_id}/test-suites", headers=dev_headers)
    assert suites_list_res.status_code == 200
    assert suites_list_res.json()["total"] >= 1

    # 5. Dispatch test run
    run_res = await client.post(
        f"/api/v1/projects/{project_id}/test-runs",
        json={
            "suite_id": suite_id,
            "target_base_url": "http://localhost:8000",
            "environment_type": "LOCAL_SANDBOX",
            "health_check_path": "/health"
        },
        headers=dev_headers
    )
    assert run_res.status_code == 202
    run_data = run_res.json()
    run_id = run_data["id"]
    assert run_data["status"] in ["PENDING", "STARTING", "RUNNING", "COMPLETED", "FAILED"]

    # 6. Retrieve test run details
    run_detail_res = await client.get(f"/api/v1/test-runs/{run_id}", headers=dev_headers)
    assert run_detail_res.status_code == 200
    assert run_detail_res.json()["id"] == run_id

    # 7. Retrieve test run step results
    results_res = await client.get(f"/api/v1/test-runs/{run_id}/results", headers=dev_headers)
    assert results_res.status_code == 200
    assert "items" in results_res.json()

    # 8. Test cancellation API
    cancel_res = await client.post(f"/api/v1/test-runs/{run_id}/cancel", headers=dev_headers)
    assert cancel_res.status_code == 200
