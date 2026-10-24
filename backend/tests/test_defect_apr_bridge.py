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
