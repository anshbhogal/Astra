import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_project_crud_lifecycle(client: AsyncClient, dev_headers: dict):
    # 1. Create project
    create_payload = {
        "name": "E-Commerce Microservice",
        "description": "Main online store API",
        "repository_url": "https://github.com/example/ecommerce-api",
        "default_branch": "develop",
        "language_framework": "PYTHON_FASTAPI"
    }
    create_res = await client.post("/api/v1/projects/", json=create_payload, headers=dev_headers)
    assert create_res.status_code == 201
    project = create_res.json()
    project_id = project["id"]
    assert project["name"] == "E-Commerce Microservice"
    assert project["repository_url"] == "https://github.com/example/ecommerce-api"

    # 2. Retrieve project
    get_res = await client.get(f"/api/v1/projects/{project_id}", headers=dev_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == project_id

    # 3. Update project
    update_payload = {
        "name": "E-Commerce Microservice v2",
        "default_branch": "main"
    }
    put_res = await client.put(f"/api/v1/projects/{project_id}", json=update_payload, headers=dev_headers)
    assert put_res.status_code == 200
    assert put_res.json()["name"] == "E-Commerce Microservice v2"
    assert put_res.json()["default_branch"] == "main"

    # 4. List projects
    list_res = await client.get("/api/v1/projects/", headers=dev_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 5. Delete project
    del_res = await client.delete(f"/api/v1/projects/{project_id}", headers=dev_headers)
    assert del_res.status_code == 204

    # 6. Verify 404 after deletion
    get_again = await client.get(f"/api/v1/projects/{project_id}", headers=dev_headers)
    assert get_again.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_project_returns_404(client: AsyncClient, dev_headers: dict):
    random_id = str(uuid.uuid4())
    res = await client.get(f"/api/v1/projects/{random_id}", headers=dev_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_project_invalid_url_fails(client: AsyncClient, dev_headers: dict):
    payload = {
        "name": "Invalid Repo Project",
        "repository_url": "ftp://invalid-scheme.com/repo",
        "language_framework": "PYTHON_FASTAPI"
    }
    res = await client.post("/api/v1/projects/", json=payload, headers=dev_headers)
    assert res.status_code == 422
