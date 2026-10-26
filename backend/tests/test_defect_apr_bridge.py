"""Tests for Phase 2 Task P2-3: Dual Schema Bridge (FailureAnalysis to G2Defect APR)."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.canonical import Workspace, G2Defect
from app.models.domain import Project, LanguageFramework, User, FailureAnalysisModel


@pytest.mark.asyncio
async def test_failure_analysis_defect_can_trigger_program_repair(
    client: AsyncClient,
    db_session: AsyncSession,
    dev_user: User,
    dev_headers: dict
):
    """Defects discovered in FailureAnalysisModel must be repairable via APR without returning 404."""
    # 1. Setup Workspace & Project
    ws = Workspace(
        id=uuid.uuid4(),
        name="Bridge WS",
        slug="bridge-ws",
        plan_tier="ENTERPRISE",
        settings={}
    )
    db_session.add(ws)

    project = Project(
        id=uuid.uuid4(),
        owner_id=dev_user.id,
        workspace_id=ws.id,
        name="Bridge Target Project",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        repository_url="https://github.com/example/bridge-api"
    )
    db_session.add(project)

    # 2. Insert defect strictly as FailureAnalysisModel (Phase 6 defect detection)
    fa_defect = FailureAnalysisModel(
        id=uuid.uuid4(),
        project_id=project.id,
        run_id=None,
        test_result_id="tr-test-1",
        test_case_id="tc-test-1",
        endpoint_id="ep-1",
        category="APPLICATION_BUG",
        summary="AttributeError: 'NoneType' object has no attribute 'get'",
        error_message="NoneType error in service layer",
        exception_type="AttributeError",
        failing_file="app/services/user_service.py",
        failing_line=42,
        failing_function="get_user_profile",
        fingerprint="fa_fp_1234567890",
        classification_confidence=0.95,
        attribution_confidence=0.90,
        root_cause_confidence=0.88,
        status="OPEN"
    )
    db_session.add(fa_defect)
    await db_session.commit()

    # Verify G2Defect does not yet have this defect
    res = await db_session.execute(select(G2Defect).where(G2Defect.id == fa_defect.id))
    assert res.scalar_one_or_none() is None

    # 3. Trigger APR for this defect using its FailureAnalysis id
    trigger_res = await client.post(
        f"/api/v1/repair/defects/{fa_defect.id}/trigger",
        headers=dev_headers
    )

    # Must succeed with 201 Created instead of 404 Not Found
    assert trigger_res.status_code == 201, f"Expected 201, got {trigger_res.status_code}: {trigger_res.text}"
    job_data = trigger_res.json()
    assert job_data["defect_id"] == str(fa_defect.id)
    assert job_data["status"] in ("COMPLETED", "LOCALIZING")

    # Verify G2Defect was mirrored / bridged
    bridged_res = await db_session.execute(select(G2Defect).where(G2Defect.id == fa_defect.id))
    bridged_defect = bridged_res.scalar_one_or_none()
    assert bridged_defect is not None
    assert bridged_defect.project_id == project.id
    assert "user_service.py" in bridged_defect.description


@pytest.mark.asyncio
async def test_authorize_candidate_pr_produces_honest_commit(
    client: AsyncClient,
    db_session: AsyncSession,
    dev_user: User,
    dev_headers: dict
):
    """Verifies that authorizing a repair candidate generates an honest commit SHA without c0ffee or fake PRs."""
    # 1. Setup Workspace & Project
    ws = Workspace(
        id=uuid.uuid4(),
        name="PR WS",
        slug="pr-ws",
        plan_tier="ENTERPRISE",
        settings={}
    )
    db_session.add(ws)

    project = Project(
        id=uuid.uuid4(),
        owner_id=dev_user.id,
        workspace_id=ws.id,
        name="PR Target Project",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        repository_url="https://github.com/example/pr-api"
    )
    db_session.add(project)

    # 2. Insert G2Defect
    defect = G2Defect(
        id=uuid.uuid4(),
        project_id=project.id,
        defect_key="DEF-HONEST-01",
        title="Zero division error in order calculator",
        description="ZeroDivisionError\nLocation: app/calc.py:10 in divide",
        severity="MAJOR",
        priority="P2",
        status="NEW",
        fingerprint="fp_honest_123456",
        source="AUTOMATED_ANALYSIS",
        actor_type="SYSTEM",
    )
    db_session.add(defect)
    await db_session.commit()

    # 3. Trigger repair to generate candidates
    trigger_res = await client.post(
        f"/api/v1/repair/defects/{defect.id}/trigger",
        headers=dev_headers
    )
    assert trigger_res.status_code == 201

    # 4. Fetch candidate
    cands_res = await client.get(
        f"/api/v1/repair/defects/{defect.id}/candidates",
        headers=dev_headers
    )
    assert cands_res.status_code == 200
    candidates = cands_res.json()
    assert len(candidates) >= 1
    candidate_id = candidates[0]["id"]

    # 5. Authorize PR
    auth_res = await client.post(
        f"/api/v1/repair/candidates/{candidate_id}/authorize-pr",
        headers=dev_headers,
        json={"reviewer_comment": "Approved by senior developer."}
    )
    assert auth_res.status_code == 200
    pr_data = auth_res.json()

    # Verify commit SHA is genuine 40-character SHA and NOT fabricated 'c0ffee'
    commit_sha = pr_data["commit_sha"]
    assert len(commit_sha) == 40
    assert not commit_sha.startswith("c0ffee")

    # In unconfigured GitHub mode, PR number and URL must be None (no fake abs(hash) numbers)
    assert pr_data["github_pr_number"] is None
    assert pr_data["github_pr_url"] is None
    assert pr_data["pr_status"] == "LOCAL_COMMITTED"

