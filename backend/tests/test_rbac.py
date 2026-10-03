import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_can_create_project(client: AsyncClient, admin_headers: dict):
    payload = {
        "name": "Admin Project",
        "description": "Admin owned project",
        "repository_url": "https://github.com/example/admin-app",
        "default_branch": "main",
        "language_framework": "PYTHON_FASTAPI"
    }
    response = await client.post("/api/v1/projects/", json=payload, headers=admin_headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_developer_can_create_project(client: AsyncClient, dev_headers: dict):
    payload = {
        "name": "Dev Project",
        "repository_url": "https://github.com/example/dev-app",
        "language_framework": "NODE_EXPRESS"
    }
    response = await client.post("/api/v1/projects/", json=payload, headers=dev_headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_viewer_cannot_create_project(client: AsyncClient, viewer_headers: dict):
    payload = {
        "name": "Viewer Attempt",
        "repository_url": "https://github.com/example/viewer-app",
        "language_framework": "JAVA_SPRING"
    }
    response = await client.post("/api/v1/projects/", json=payload, headers=viewer_headers)
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_viewer_can_list_projects(client: AsyncClient, viewer_headers: dict):
    response = await client.get("/api/v1/projects/", headers=viewer_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
