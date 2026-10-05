import pytest
from httpx import AsyncClient
from app.models.domain import UserRole

pytestmark = pytest.mark.asyncio


async def test_system_health_features(client: AsyncClient):
    """Test 1: Health & Readiness Endpoint Verification."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ASTRA"


async def test_auth_and_profile_features(client: AsyncClient, admin_headers: dict):
    """Test 2: Authentication & Profile Retrieval."""
    me_res = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert me_res.status_code == 200
    assert me_res.json()["role"] == UserRole.ADMIN
    assert me_res.json()["email"] == "admin@astra.local"


async def test_email_smtp_project_crud_features(client: AsyncClient, admin_headers: dict):
    """Test 3: Email SMTP Microservice Project Creation & CRUD Operations."""
    # Create Email SMTP Project
    project_payload = {
        "name": "email_smtp",
        "description": "Target repository for email SMTP service defect detection",
        "repository_url": "https://github.com/anshbhogal/email_smtp",
        "default_branch": "main",
        "language_framework": "PYTHON_FASTAPI"
    }

    create_res = await client.post("/api/v1/projects/", json=project_payload, headers=admin_headers)
    assert create_res.status_code == 201
    created = create_res.json()
    project_id = created["id"]
    assert created["name"] == "email_smtp"
    assert created["repository_url"] == "https://github.com/anshbhogal/email_smtp"

    # List Projects & Confirm
    list_res = await client.get("/api/v1/projects/", headers=admin_headers)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    found = any(p["id"] == project_id for p in items)
    assert found is True

    # Retrieve Project by ID
    get_res = await client.get(f"/api/v1/projects/{project_id}", headers=admin_headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "email_smtp"

    # Update Project
    update_res = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"description": "Updated SMTP service description for automated testing"},
        headers=admin_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated SMTP service description for automated testing"

    # Delete Project
    del_res = await client.delete(f"/api/v1/projects/{project_id}", headers=admin_headers)
    assert del_res.status_code == 204


async def test_rbac_matrix_on_smtp_project(client: AsyncClient, admin_headers: dict, viewer_headers: dict):
    """Test 4: RBAC Matrix Verification (Viewer permission enforcement)."""
    # Create target project as Admin
    create_res = await client.post(
        "/api/v1/projects/",
        json={
            "name": "email_smtp_rbac_test",
            "description": "RBAC verification target project",
            "repository_url": "https://github.com/anshbhogal/email_smtp",
            "default_branch": "main",
            "language_framework": "PYTHON_FASTAPI"
        },
        headers=admin_headers
    )
    assert create_res.status_code == 201
    project_id = create_res.json()["id"]

    # Viewer CANNOT create a project (403 Forbidden)
    forbidden_create = await client.post(
        "/api/v1/projects/",
        json={
            "name": "unauthorized_project",
            "repository_url": "https://github.com/test/repo",
            "language_framework": "OTHER"
        },
        headers=viewer_headers
    )
    assert forbidden_create.status_code == 403

    # Viewer CANNOT delete Admin's project (403/404 security guard)
    forbidden_del = await client.delete(f"/api/v1/projects/{project_id}", headers=viewer_headers)
    assert forbidden_del.status_code in [403, 404]

    # Clean up with Admin
    await client.delete(f"/api/v1/projects/{project_id}", headers=admin_headers)


async def test_celery_task_dispatch(client: AsyncClient, admin_headers: dict):
    """Test 5: Celery Background Task Dispatch."""
    task_res = await client.post("/api/v1/tasks/test", json={"triggered_by": "system_test"}, headers=admin_headers)
    assert task_res.status_code == 202
    data = task_res.json()
    assert "task_id" in data
    assert data["status"] in ["QUEUED", "DISPATCHED"]
