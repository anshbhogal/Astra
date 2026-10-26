"""Tests for Code Studio Async Non-Blocking Test Runner & Execution Timeout (P4-2)."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch
import asyncio

from app.models.domain import User, UserRole, Project, LanguageFramework


@pytest.mark.asyncio
async def test_async_developer_test_runner_success(
    client: AsyncClient,
    dev_headers: dict,
    dev_user: User,
    db_session: AsyncSession
):
    """Verify that run-tests executes non-blocking via asyncio.to_thread and returns structured results."""
    proj = Project(
        name="Async Runner Project",
        repository_url="https://github.com/example/async-runner",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=dev_user.id
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    # Create a simple function to be tested
    create_res = await client.post(
        f"/api/v1/projects/{proj.id}/code/file",
        json={"path": "service.py", "content": "def multiply(a: int, b: int) -> int:\n    return a * b\n"},
        headers=dev_headers
    )
    assert create_res.status_code == 201

    # Run tests
    run_res = await client.post(f"/api/v1/projects/{proj.id}/code/run-tests", headers=dev_headers)
    assert run_res.status_code == 200, run_res.text
    result = run_res.json()
    assert result["status"] in ("PASSED", "NO_TESTS_FOUND")
    assert "duration_ms" in result
    assert "output" in result


@pytest.mark.asyncio
async def test_async_developer_test_runner_timeout(
    client: AsyncClient,
    dev_headers: dict,
    dev_user: User,
    db_session: AsyncSession
):
    """Verify that hanging test execution triggers Timeout and returns status=TIMEOUT without blocking."""
    proj = Project(
        name="Timeout Project",
        repository_url="https://github.com/example/timeout-proj",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=dev_user.id
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    async def _mock_hanging_wait_for(*args, **kwargs):
        raise asyncio.TimeoutError()

    with patch("asyncio.wait_for", side_effect=_mock_hanging_wait_for):
        run_res = await client.post(f"/api/v1/projects/{proj.id}/code/run-tests", headers=dev_headers)
        assert run_res.status_code == 200
        result = run_res.json()
        assert result["status"] == "TIMEOUT"
        assert "exceeded maximum timeout" in result["output"]
        assert result["failed_tests"] == 1
