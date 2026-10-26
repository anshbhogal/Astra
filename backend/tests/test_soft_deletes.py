"""Tests for Soft Deletes & Cascade Deletion Safeguards (P3-3)."""
import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import (
    User, UserRole, Project, LanguageFramework,
    TestSuite, TestCase, TestRun, TestRunStatus, TestResult, TestOutcome, AuditLog
)
from app.core.security import get_password_hash

TestSuite.__test__ = False
TestCase.__test__ = False
TestRun.__test__ = False
TestRunStatus.__test__ = False
TestResult.__test__ = False
TestOutcome.__test__ = False


@pytest.mark.asyncio
async def test_admin_delete_user_is_soft_delete(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession
):
    """Verify that deleting a user sets is_deleted=True without purging records or cascading."""
    # 1. Create Target Developer
    dev_user = User(
        email="dev_soft@example.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Dev Soft",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True
    )
    db_session.add(dev_user)
    await db_session.commit()
    await db_session.refresh(dev_user)

    # 2. Create Project owned by dev_user with TestSuite, TestRun, and AuditLog
    proj = Project(
        name="Dev Project",
        repository_url="https://github.com/example/dev-repo",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=dev_user.id
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    suite = TestSuite(
        project_id=proj.id,
        name="Dev Suite"
    )
    db_session.add(suite)
    await db_session.commit()
    await db_session.refresh(suite)

    test_run = TestRun(
        project_id=proj.id,
        suite_id=suite.id,
        status=TestRunStatus.COMPLETED
    )
    db_session.add(test_run)
    await db_session.commit()
    await db_session.refresh(test_run)

    audit = AuditLog(
        actor_id=dev_user.id,
        action="USER_LOGIN",
        resource_type="USER",
        resource_id=str(dev_user.id)
    )
    db_session.add(audit)
    await db_session.commit()

    # 3. Call DELETE /api/v1/admin/users/{user_id} with Admin headers
    del_resp = await client.delete(f"/api/v1/admin/users/{dev_user.id}", headers=admin_headers)
    assert del_resp.status_code == 204

    # Verify user is not listed in active users
    list_resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert list_resp.status_code == 200
    user_emails = [u["email"] for u in list_resp.json()]
    assert "dev_soft@example.com" not in user_emails

    # Verify deleted user cannot log in
    login_resp = await client.post("/api/v1/auth/login", json={"email": "dev_soft@example.com", "password": "Password123!"})
    assert login_resp.status_code == 401

    # 4. Verify in DB: User row still exists with is_deleted=True
    stmt_user = select(User).where(User.id == dev_user.id)
    db_user = (await db_session.execute(stmt_user)).scalar_one_or_none()
    assert db_user is not None
    assert db_user.is_deleted is True
    assert db_user.deleted_at is not None
    assert db_user.is_active is False

    # 5. Verify related project, test run, and audit log still exist (not cascade deleted)
    stmt_proj = select(Project).where(Project.id == proj.id)
    db_proj = (await db_session.execute(stmt_proj)).scalar_one_or_none()
    assert db_proj is not None

    stmt_run = select(TestRun).where(TestRun.id == test_run.id)
    db_run = (await db_session.execute(stmt_run)).scalar_one_or_none()
    assert db_run is not None

    stmt_audit = select(AuditLog).where(AuditLog.id == audit.id)
    db_audit = (await db_session.execute(stmt_audit)).scalar_one_or_none()
    assert db_audit is not None


@pytest.mark.asyncio
async def test_project_soft_delete_preserves_test_runs(
    client: AsyncClient,
    dev_headers: dict,
    dev_user: User,
    db_session: AsyncSession
):
    """Verify that deleting a project marks is_deleted=True and preserves runs and results."""
    proj = Project(
        name="Soft Delete Project",
        repository_url="https://github.com/example/soft-delete-proj",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=dev_user.id
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    suite = TestSuite(
        project_id=proj.id,
        name="Project Suite"
    )
    db_session.add(suite)
    await db_session.commit()
    await db_session.refresh(suite)

    test_run = TestRun(
        project_id=proj.id,
        suite_id=suite.id,
        status=TestRunStatus.COMPLETED
    )
    db_session.add(test_run)
    await db_session.commit()
    await db_session.refresh(test_run)

    tc = TestCase(
        suite_id=suite.id,
        name="test_canary",
        specification={"method": "GET", "path": "/api/health"}
    )
    db_session.add(tc)
    await db_session.commit()
    await db_session.refresh(tc)

    test_res = TestResult(
        test_run_id=test_run.id,
        test_case_id=tc.id,
        endpoint="/api/health",
        method="GET",
        outcome=TestOutcome.PASS,
        execution_time_ms=42.0
    )
    db_session.add(test_res)
    await db_session.commit()
    await db_session.refresh(test_res)

    # Delete project via API
    del_resp = await client.delete(f"/api/v1/projects/{proj.id}", headers=dev_headers)
    assert del_resp.status_code == 204

    # Listing projects does not return deleted project
    list_resp = await client.get("/api/v1/projects/", headers=dev_headers)
    assert list_resp.status_code == 200
    proj_ids = [p["id"] for p in list_resp.json()["items"]]
    assert str(proj.id) not in proj_ids

    # Fetching project by ID returns 404
    get_resp = await client.get(f"/api/v1/projects/{proj.id}", headers=dev_headers)
    assert get_resp.status_code == 404

    # Direct DB inspection: project row is preserved with is_deleted=True
    stmt_p = select(Project).where(Project.id == proj.id)
    db_p = (await db_session.execute(stmt_p)).scalar_one_or_none()
    assert db_p is not None
    assert db_p.is_deleted is True
    assert db_p.deleted_at is not None

    # TestRun and TestResult still exist intact
    stmt_r = select(TestRun).where(TestRun.id == test_run.id)
    db_r = (await db_session.execute(stmt_r)).scalar_one_or_none()
    assert db_r is not None
    assert db_r.project_id == proj.id

    stmt_res = select(TestResult).where(TestResult.id == test_res.id)
    db_res = (await db_session.execute(stmt_res)).scalar_one_or_none()
    assert db_res is not None
    assert db_res.outcome == TestOutcome.PASS
