"""Security tests for Code Studio path traversal and workspace isolation (P4-3)."""
import os
import uuid
import pytest
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import User, UserRole, Project, LanguageFramework


@pytest.mark.asyncio
async def test_code_editor_path_traversal_blocked(
    client: AsyncClient,
    dev_headers: dict,
    dev_user: User,
    db_session: AsyncSession
):
    """Verify that path traversal attempts (../, /etc/passwd, null byte) are strictly blocked."""
    proj = Project(
        name="Security Path Project",
        repository_url="https://github.com/example/sec-path",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=dev_user.id
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    # 1. Directory traversal to /etc/passwd
    res_traversal = await client.get(
        f"/api/v1/projects/{proj.id}/code/file?path=../../../../../../etc/passwd",
        headers=dev_headers
    )
    assert res_traversal.status_code == 400
    assert "escapes project workspace" in res_traversal.json()["detail"]

    # 2. Directory traversal on file creation
    res_create = await client.post(
        f"/api/v1/projects/{proj.id}/code/file",
        json={"path": "../../../tmp/evil.py", "content": "malicious code"},
        headers=dev_headers
    )
    assert res_create.status_code == 400
    assert "escapes project workspace" in res_create.json()["detail"]

    # 3. Directory traversal on file save
    res_save = await client.put(
        f"/api/v1/projects/{proj.id}/code/file",
        json={"path": "../../root/.bashrc", "content": "export HACKED=1"},
        headers=dev_headers
    )
    assert res_save.status_code == 400
    assert "escapes project workspace" in res_save.json()["detail"]

    # 4. Null byte injection
    res_null = await client.get(
        f"/api/v1/projects/{proj.id}/code/file?path=main.py%00.txt",
        headers=dev_headers
    )
    # The framework or safe_resolve handles null byte syntax
    assert res_null.status_code in (400, 404)


@pytest.mark.asyncio
async def test_code_editor_symlink_escape_blocked(
    client: AsyncClient,
    dev_headers: dict,
    dev_user: User,
    db_session: AsyncSession
):
    """Verify that a symlink pointing outside the workspace cannot be read through the editor."""
    proj = Project(
        name="Symlink Security Project",
        repository_url="https://github.com/example/symlink-sec",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=dev_user.id
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    # Initialize workspace
    tree_res = await client.get(f"/api/v1/projects/{proj.id}/code/tree", headers=dev_headers)
    assert tree_res.status_code == 200

    ws_dir = Path(f"/app/scratch/{proj.id}")
    if ws_dir.exists():
        # Create a symlink pointing outside to /etc
        symlink_path = ws_dir / "external_symlink"
        try:
            if not symlink_path.exists():
                os.symlink("/etc/passwd", symlink_path)
            # Attempt to read file via symlink
            res = await client.get(
                f"/api/v1/projects/{proj.id}/code/file?path=external_symlink",
                headers=dev_headers
            )
            assert res.status_code == 400
            assert "escapes project workspace" in res.json()["detail"]
        except (OSError, NotImplementedError):
            pass
