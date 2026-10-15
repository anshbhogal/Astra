"""Security tests for Phase 0 Task P0-3: Repair Endpoints Authentication and Project Authorization."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import User, UserRole, Project, ProjectMember, LanguageFramework
from app.models.canonical import G2Defect, G2RepairJob, G2RepairCandidate
from app.core.security import get_password_hash, create_access_token


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _create_test_fixture(db_session: AsyncSession):
    # 1. Admin
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

    # 2. Project
    project = Project(
        name=f"Project Repair {uuid.uuid4().hex[:6]}",
        repository_url="https://github.com/example/repair-repo",
        default_branch="main",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=admin.id
    )
    db_session.add(project)
    await db_session.flush()

    # 3. Canonical Defect
    defect = G2Defect(
        id=uuid.uuid4(),
        project_id=project.id,
        defect_key=f"DEF-{uuid.uuid4().hex[:4].upper()}",
        title="NullPointer in calculate_metrics",
        description="app/services/metrics.py",
        severity="HIGH",
        status="OPEN",
        source="UNIT_TEST",
        created_at=utc_now()
    )
    db_session.add(defect)
    await db_session.flush()

    # 4. Assigned Developer
    dev_assigned = User(
        email=f"dev_assigned_{uuid.uuid4().hex[:6]}@astra.local",
        hashed_password=get_password_hash("DevPass123!"),
        full_name="Assigned Developer",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True,
    )
    db_session.add(dev_assigned)
    await db_session.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=dev_assigned.id,
        role=UserRole.DEVELOPER
    )
    db_session.add(member)

    # 5. Unassigned Developer (different project / no membership)
    dev_unassigned = User(
        email=f"dev_unassigned_{uuid.uuid4().hex[:6]}@astra.local",
        hashed_password=get_password_hash("DevPass123!"),
        full_name="Unassigned Developer",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True,
    )
    db_session.add(dev_unassigned)

    # 6. Assigned Viewer (read only)
    viewer_assigned = User(
        email=f"viewer_assigned_{uuid.uuid4().hex[:6]}@astra.local",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Assigned Viewer",
        role=UserRole.VIEWER,
        is_active=True,
        is_approved=True,
    )
    db_session.add(viewer_assigned)
    await db_session.flush()

    member_viewer = ProjectMember(
        project_id=project.id,
        user_id=viewer_assigned.id,
        role=UserRole.VIEWER
    )
    db_session.add(member_viewer)

    await db_session.commit()
    return project, defect, dev_assigned, dev_unassigned, viewer_assigned


@pytest.mark.asyncio
async def test_repair_unauthenticated_fails(client: AsyncClient, db_session: AsyncSession):
    """Calling repair endpoints without a token must return 401 Unauthorized."""
    _, defect, _, _, _ = await _create_test_fixture(db_session)
    dummy_uuid = uuid.uuid4()

    # POST /api/v1/repair/defects/{defect_id}/trigger
    resp1 = await client.post(f"/api/v1/repair/defects/{defect.id}/trigger")
    assert resp1.status_code == 401, f"Expected 401 on trigger, got {resp1.status_code}"

    # GET /api/v1/repair/defects/{defect_id}/candidates
    resp2 = await client.get(f"/api/v1/repair/defects/{defect.id}/candidates")
    assert resp2.status_code == 401, f"Expected 401 on candidates, got {resp2.status_code}"

    # POST /api/v1/repair/candidates/{candidate_id}/authorize-pr
    resp3 = await client.post(f"/api/v1/repair/candidates/{dummy_uuid}/authorize-pr", json={})
    assert resp3.status_code == 401, f"Expected 401 on authorize-pr, got {resp3.status_code}"

    # GET /api/v1/repair/jobs/{job_id}
    resp4 = await client.get(f"/api/v1/repair/jobs/{dummy_uuid}")
    assert resp4.status_code == 401, f"Expected 401 on jobs, got {resp4.status_code}"


@pytest.mark.asyncio
async def test_repair_wrong_role_fails(client: AsyncClient, db_session: AsyncSession):
    """Calling mutation repair endpoints as a VIEWER must return 403 Forbidden."""
    _, defect, _, _, viewer = await _create_test_fixture(db_session)
    token = create_access_token(subject=viewer.id)
    headers = {"Authorization": f"Bearer {token}"}

    # VIEWER cannot trigger repair
    resp = await client.post(f"/api/v1/repair/defects/{defect.id}/trigger", headers=headers)
    assert resp.status_code == 403, f"Expected 403 for viewer triggering repair, got {resp.status_code}: {resp.text}"

    # VIEWER cannot authorize PR
    resp2 = await client.post(f"/api/v1/repair/candidates/{uuid.uuid4()}/authorize-pr", headers=headers, json={})
    assert resp2.status_code == 403, f"Expected 403 for viewer authorizing PR, got {resp2.status_code}: {resp2.text}"


@pytest.mark.asyncio
async def test_repair_unassigned_developer_blocked(client: AsyncClient, db_session: AsyncSession):
    """A developer who is not a member of the project must be blocked with 403 Forbidden."""
    _, defect, _, unassigned_dev, _ = await _create_test_fixture(db_session)
    token = create_access_token(subject=unassigned_dev.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Unassigned dev cannot trigger repair on this defect
    resp = await client.post(f"/api/v1/repair/defects/{defect.id}/trigger", headers=headers)
    assert resp.status_code == 403, f"Expected 403 for unassigned developer, got {resp.status_code}: {resp.text}"

    # Unassigned dev cannot list candidates
    resp2 = await client.get(f"/api/v1/repair/defects/{defect.id}/candidates", headers=headers)
    assert resp2.status_code == 403, f"Expected 403 for unassigned developer, got {resp2.status_code}: {resp2.text}"


@pytest.mark.asyncio
async def test_repair_assigned_developer_succeeds(client: AsyncClient, db_session: AsyncSession):
    """An assigned developer must be able to trigger repair, view candidates, and authorize PR."""
    _, defect, assigned_dev, _, _ = await _create_test_fixture(db_session)
    token = create_access_token(subject=assigned_dev.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Trigger repair
    resp_trigger = await client.post(f"/api/v1/repair/defects/{defect.id}/trigger", headers=headers)
    assert resp_trigger.status_code == 201, f"Expected 201 Created on trigger, got {resp_trigger.status_code}: {resp_trigger.text}"
    job_data = resp_trigger.json()
    job_id = job_data["id"]

    # 2. Get repair job
    resp_job = await client.get(f"/api/v1/repair/jobs/{job_id}", headers=headers)
    assert resp_job.status_code == 200, f"Expected 200 OK on get job, got {resp_job.status_code}"

    # 3. List candidates
    resp_cands = await client.get(f"/api/v1/repair/defects/{defect.id}/candidates", headers=headers)
    assert resp_cands.status_code == 200, f"Expected 200 OK on list candidates, got {resp_cands.status_code}"
    cands = resp_cands.json()
    assert len(cands) >= 1
    cand_id = cands[0]["id"]

    # 4. Authorize PR
    resp_auth = await client.post(
        f"/api/v1/repair/candidates/{cand_id}/authorize-pr",
        headers=headers,
        json={"reviewer_comment": "Verified by assigned developer."}
    )
    assert resp_auth.status_code == 200, f"Expected 200 OK on authorize PR, got {resp_auth.status_code}: {resp_auth.text}"
