"""
ASTRA Backend - Integration Tests for Phase 12 Automated Program Repair REST API
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical import G2Defect, Workspace
from app.models.domain import Project, LanguageFramework, User


@pytest.mark.asyncio
async def test_trigger_repair_for_defect(client: AsyncClient, db_session: AsyncSession, dev_user: User):
    # 1. Setup workspace & project & defect
    workspace = Workspace(
        id=uuid.uuid4(),
        name="Test WS",
        slug="test-ws",
        plan_tier="ENTERPRISE",
        settings={},
    )
    db_session.add(workspace)

    project = Project(
        id=uuid.uuid4(),
        owner_id=dev_user.id,
        workspace_id=workspace.id,
        name="Test API",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        repository_url="https://github.com/example/api",
    )
    db_session.add(project)

    defect = G2Defect(
        id=uuid.uuid4(),
        project_id=project.id,
        defect_key="DEF-101",
        title="NoneType dereference in user settings",
        description="AttributeError in app/services/user_service.py",
        severity="MAJOR",
        priority="P1",
        status="NEW",
    )
    db_session.add(defect)
    await db_session.commit()

    # 2. Trigger repair job
    res = await client.post(f"/api/v1/repair/defects/{defect.id}/trigger")
    assert res.status_code == 201
    data = res.json()
    assert data["defect_id"] == str(defect.id)
    assert data["status"] == "COMPLETED"
    job_id = data["id"]

    # 3. Fetch candidates
    c_res = await client.get(f"/api/v1/repair/defects/{defect.id}/candidates")
    assert c_res.status_code == 200
    candidates = c_res.json()
    assert len(candidates) >= 1
    selected_cand = candidates[0]
    assert selected_cand["mutator_type"] == "NULL_SAFETY_GUARD_MUTATOR"
    assert selected_cand["status"] == "VERIFIED"

    # 4. Authorize PR (Human Approval Gate)
    auth_res = await client.post(
        f"/api/v1/repair/candidates/{selected_cand['id']}/authorize-pr",
        json={"reviewer_comment": "LGTM, verified via Zero-Observed-Regression Gate."},
    )
    assert auth_res.status_code == 200
    pr_data = auth_res.json()
    assert pr_data["pr_status"] == "OPEN"
    assert "github_pr_number" in pr_data
    pr_number = pr_data["github_pr_number"]

    # 5. Closed-Loop Post-Merge Webhook
    hook_res = await client.post(
        "/api/v1/repair/webhooks/github/pr-merged",
        json={"pull_request": {"number": pr_number, "merged": True}},
    )
    assert hook_res.status_code == 200
    hook_data = hook_res.json()
    assert hook_data["status"] == "verified_and_closed"
    assert hook_data["defect_id"] == str(defect.id)
