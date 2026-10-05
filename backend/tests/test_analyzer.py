import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_trigger_project_analysis_flow(client: AsyncClient, dev_headers: dict):
    # 1. Create project
    create_payload = {
        "name": "Email SMTP Test Repo",
        "description": "Static analysis test target",
        "repository_url": "https://github.com/anshbhogal/email_smtp",
        "default_branch": "main",
        "language_framework": "PYTHON_FASTAPI"
    }
    create_res = await client.post("/api/v1/projects/", json=create_payload, headers=dev_headers)
    assert create_res.status_code == 201
    project_id = create_res.json()["id"]

    # 2. Trigger Analysis
    response = await client.post(f"/api/v1/projects/{project_id}/analyze", headers=dev_headers)
    assert response.status_code == 202
    data = response.json()
    assert data["project_id"] == project_id
    assert data["status"] in ["QUEUED", "RUNNING", "COMPLETED"]

    # 3. Get Analysis Status
    res_status = await client.get(f"/api/v1/projects/{project_id}/analysis", headers=dev_headers)
    assert res_status.status_code == 200
    analysis_data = res_status.json()
    assert analysis_data["project_id"] == project_id

    # 4. Get Endpoints Catalog
    res_ep = await client.get(f"/api/v1/projects/{project_id}/endpoints", headers=dev_headers)
    assert res_ep.status_code == 200
    assert "items" in res_ep.json()

    # 5. Get Knowledge Graph
    res_graph = await client.get(f"/api/v1/projects/{project_id}/graph", headers=dev_headers)
    assert res_graph.status_code == 200
    assert "nodes" in res_graph.json()
    assert "edges" in res_graph.json()
