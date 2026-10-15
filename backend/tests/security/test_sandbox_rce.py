"""Security tests for Phase 1 Task P1-1: Elimination of Shell Injection & Arbitrary Commands in Sandbox."""

import ast
import os
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import User, UserRole, Project, ProjectMember, LanguageFramework
from app.core.security import get_password_hash, create_access_token


async def _create_project_and_user(db_session: AsyncSession):
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
        name=f"Project Sandbox {uuid.uuid4().hex[:6]}",
        repository_url="https://github.com/example/sandbox-repo",
        default_branch="main",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=admin.id
    )
    db_session.add(project)
    await db_session.flush()

    dev = User(
        email=f"dev_sandbox_{uuid.uuid4().hex[:6]}@astra.local",
        hashed_password=get_password_hash("DevPass123!"),
        full_name="Sandbox Developer",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True,
    )
    db_session.add(dev)
    await db_session.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=dev.id,
        role=UserRole.DEVELOPER
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(dev)

    token = create_access_token(subject=dev.id)
    headers = {"Authorization": f"Bearer {token}"}
    return project, dev, headers


@pytest.mark.asyncio
async def test_sandbox_custom_command_rejected_422(client: AsyncClient, db_session: AsyncSession):
    """Posting custom_command to /sandbox/start must be rejected with 422 Unprocessable Entity."""
    project, _, headers = await _create_project_and_user(db_session)

    # Attempt to pass custom_command
    payload = {
        "mode": "HYBRID",
        "custom_command": "whoami > /tmp/pwned.txt"
    }

    resp = await client.post(
        f"/api/v1/projects/{project.id}/sandbox/start",
        json=payload,
        headers=headers
    )
    assert resp.status_code == 422, (
        f"Expected 422 Unprocessable Entity when custom_command is supplied, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_sandbox_native_command_mode_rejected_422(client: AsyncClient, db_session: AsyncSession):
    """Posting NATIVE_COMMAND mode must be rejected with 422 Unprocessable Entity."""
    project, _, headers = await _create_project_and_user(db_session)

    payload = {
        "mode": "NATIVE_COMMAND"
    }

    resp = await client.post(
        f"/api/v1/projects/{project.id}/sandbox/start",
        json=payload,
        headers=headers
    )
    assert resp.status_code == 422, (
        f"Expected 422 Unprocessable Entity for NATIVE_COMMAND mode, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_sandbox_path_traversal_rejected(client: AsyncClient, db_session: AsyncSession):
    """Attempting path traversal ('../../etc/passwd') on file reading/saving must be rejected."""
    project, _, headers = await _create_project_and_user(db_session)

    # 1. Path traversal in GET file
    resp_get = await client.get(
        f"/api/v1/projects/{project.id}/code/file?path=../../etc/passwd",
        headers=headers
    )
    assert resp_get.status_code in [400, 422], (
        f"Expected 400/422 for path traversal in GET file, got {resp_get.status_code}: {resp_get.text}"
    )

    # 2. Path traversal in PUT file
    resp_put = await client.put(
        f"/api/v1/projects/{project.id}/code/file",
        json={"path": "../../etc/cron.d/malicious", "content": "* * * * * root echo pwned"},
        headers=headers
    )
    assert resp_put.status_code in [400, 422], (
        f"Expected 400/422 for path traversal in PUT file, got {resp_put.status_code}: {resp_put.text}"
    )


def test_no_shell_true_in_codebase():
    """Static AST check verifying that no production Python file calls subprocess with shell=True."""
    search_dirs = ["/app/app", "/app/engine"]
    violating_files = []

    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        for root, _, files in os.walk(sdir):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            tree = ast.parse(f.read(), filename=full_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Call):
                                for kw in node.keywords:
                                    if kw.arg == "shell":
                                        if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                            violating_files.append(f"{full_path}:{node.lineno}")
                    except Exception:
                        pass

    assert not violating_files, f"Found shell=True calls in production codebase: {violating_files}"
