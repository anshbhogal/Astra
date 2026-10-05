import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.domain import User, Project, LanguageFramework, UserRole
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_trigger_project_analysis_flow(async_client: AsyncClient, test_user: User, db_session):
    # Create test project
    project = Project(
        name="Email SMTP Test Repo",
        description="Static analysis test target",
        repository_url="https://github.com/anshbhogal/email_smtp",
        default_branch="main",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    token = create_access_token(data={"sub": str(test_user.id), "role": test_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Trigger Analysis
    response = await async_client.post(f"/api/v1/projects/{project.id}/analyze", headers=headers)
    assert response.status_code == 202
    data = response.json()
    assert data["project_id"] == str(project.id)
    assert data["status"] in ["QUEUED", "RUNNING", "COMPLETED"]

    # 2. Get Analysis Status
    res_status = await async_client.get(f"/api/v1/projects/{project.id}/analysis", headers=headers)
    assert res_status.status_code == 200
    analysis_data = res_status.json()
    assert analysis_data["project_id"] == str(project.id)

    # 3. Get Endpoints Catalog
    res_ep = await async_client.get(f"/api/v1/projects/{project.id}/endpoints", headers=headers)
    assert res_ep.status_code == 200
    assert "items" in res_ep.json()

    # 4. Get Knowledge Graph
    res_graph = await async_client.get(f"/api/v1/projects/{project.id}/graph", headers=headers)
    assert res_graph.status_code == 200
    assert "nodes" in res_graph.json()
    assert "edges" in res_graph.json()
