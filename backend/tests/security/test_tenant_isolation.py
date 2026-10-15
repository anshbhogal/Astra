import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.domain import User, UserRole, Project, ProjectMember, LanguageFramework
from app.core.security import get_password_hash, create_access_token


def get_project_routes():
    """Discover all GET endpoints in the FastAPI app containing {project_id}."""
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and "{project_id}" in route.path and hasattr(route, "methods"):
            if "GET" in route.methods:
                # Exclude routes with additional sub-resource path params requiring specific existing IDs
                # like {run_id}, {analysis_id}, {defect_id}, {channel_id}, {report_id}
                path = route.path
                if not any(param in path for param in ["{run_id}", "{analysis_id}", "{defect_id}", "{channel_id}", "{report_id}", "{file_path}"]):
                    routes.append(path)
    return sorted(list(set(routes)))


PROJECT_GET_ROUTES = get_project_routes()


@pytest.mark.asyncio
@pytest.mark.parametrize("route_template", PROJECT_GET_ROUTES)
async def test_tenant_isolation_unauthenticated(client: AsyncClient, route_template: str):
    """Unauthenticated access to any project-scoped GET route must return 401 Unauthorized."""
    random_pid = uuid.uuid4()
    target_url = route_template.replace("{project_id}", str(random_pid))
    resp = await client.get(target_url)
    assert resp.status_code == 401, f"Route {target_url} allowed unauthenticated access (status: {resp.status_code})"


@pytest.mark.asyncio
@pytest.mark.parametrize("route_template", PROJECT_GET_ROUTES)
async def test_tenant_isolation_unassigned_user_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
    route_template: str
):
    """A developer not assigned to Project A must be blocked with 403 Forbidden on Project A."""
    # 1. Create Project A owned by admin
    admin = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@astra.local",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_approved=True,
    )
    db_session.add(admin)
    await db_session.flush()

    project = Project(
        name=f"Project Alpha {uuid.uuid4().hex[:6]}",
        repository_url="https://github.com/example/alpha",
        default_branch="main",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=admin.id
    )
    db_session.add(project)
    await db_session.flush()

    # 2. Create User Unassigned (Developer with no membership in Project A)
    unassigned = User(
        email=f"dev_unassigned_{uuid.uuid4().hex[:6]}@astra.local",
        hashed_password=get_password_hash("DevPass123!"),
        full_name="Unassigned Developer",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True,
    )
    db_session.add(unassigned)
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(unassigned)

    token = create_access_token(subject=unassigned.id)
    headers = {"Authorization": f"Bearer {token}"}

    target_url = route_template.replace("{project_id}", str(project.id))
    resp = await client.get(target_url, headers=headers)

    # Must be 403 Forbidden (or 404 for project scoping)
    assert resp.status_code in (403, 404), (
        f"Route {target_url} allowed unassigned user access! Got status: {resp.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("route_template", PROJECT_GET_ROUTES)
async def test_tenant_isolation_assigned_member_permitted(
    client: AsyncClient,
    db_session: AsyncSession,
    route_template: str
):
    """An assigned developer member of Project A must be permitted (200 OK) on Project A."""
    # 1. Create Project A owned by admin
    admin = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@astra.local",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_approved=True,
    )
    db_session.add(admin)
    await db_session.flush()

    project = Project(
        name=f"Project Beta {uuid.uuid4().hex[:6]}",
        repository_url="https://github.com/example/beta",
        default_branch="main",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=admin.id
    )
    db_session.add(project)
    await db_session.flush()

    # 2. Create User Assigned and add ProjectMember
    assigned_user = User(
        email=f"dev_assigned_{uuid.uuid4().hex[:6]}@astra.local",
        hashed_password=get_password_hash("DevPass123!"),
        full_name="Assigned Developer",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True,
    )
    db_session.add(assigned_user)
    await db_session.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=assigned_user.id,
        role=UserRole.DEVELOPER
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(assigned_user)

    token = create_access_token(subject=assigned_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    target_url = route_template.replace("{project_id}", str(project.id))
    resp = await client.get(target_url, headers=headers)

    # Assigned member must NOT receive 403 Forbidden or 401 Unauthorized
    assert resp.status_code != 403, f"Assigned member blocked with 403 on {target_url}: {resp.text}"
    assert resp.status_code != 401, f"Assigned member blocked with 401 on {target_url}: {resp.text}"
