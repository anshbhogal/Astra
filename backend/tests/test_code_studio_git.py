"""Tests for Code Studio IDE Git Operations (P4-1)."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import User, UserRole, Project, LanguageFramework, ProjectMember
from app.core.security import get_password_hash, create_access_token


@pytest.mark.asyncio
async def test_code_studio_git_lifecycle(
    client: AsyncClient,
    admin_headers: dict,
    dev_headers: dict,
    dev_user: User,
    db_session: AsyncSession
):
    """Verify Git status, branching, diffing, and real commit creation in Code Studio."""
    # 1. Create a Project owned by dev_user
    proj = Project(
        name="Git Studio Project",
        repository_url="https://github.com/example/git-studio",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        default_branch="main",
        owner_id=dev_user.id
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    # 2. Check initial Git Status
    status_res = await client.get(f"/api/v1/projects/{proj.id}/code/git/status", headers=dev_headers)
    assert status_res.status_code == 200, status_res.text
    status_data = status_res.json()
    assert "branch" in status_data
    assert "is_clean" in status_data

    # 3. Create a new file via Code Studio editor
    create_res = await client.post(
        f"/api/v1/projects/{proj.id}/code/file",
        json={"path": "calc.py", "content": "def add(x, y):\n    return x + y\n", "is_directory": False},
        headers=dev_headers
    )
    assert create_res.status_code == 201

    # 4. Verify Git Status now shows untracked file
    status_res2 = await client.get(f"/api/v1/projects/{proj.id}/code/git/status", headers=dev_headers)
    assert status_res2.status_code == 200
    assert status_res2.json()["is_clean"] is False
    assert "calc.py" in status_res2.json()["untracked_files"] or "calc.py" in status_res2.json()["modified_files"]

    # 5. Create and switch to a new Git feature branch
    branch_res = await client.post(
        f"/api/v1/projects/{proj.id}/code/git/branches",
        json={"branch_name": "feature/calc-addition", "create_and_checkout": True},
        headers=dev_headers
    )
    assert branch_res.status_code == 200
    assert branch_res.json()["current_branch"] == "feature/calc-addition"
    assert "feature/calc-addition" in branch_res.json()["branches"]

    # 6. Commit the new file with authenticated author attribution
    commit_res = await client.post(
        f"/api/v1/projects/{proj.id}/code/git/commit",
        json={"message": "feat: add calc.py addition helper", "files": ["calc.py"]},
        headers=dev_headers
    )
    assert commit_res.status_code == 200, commit_res.text
    commit_data = commit_res.json()
    assert len(commit_data["commit_sha"]) == 40
    assert commit_data["branch"] == "feature/calc-addition"
    assert commit_data["author_name"] == dev_user.full_name
    assert commit_data["author_email"] == dev_user.email
    assert commit_data["message"] == "feat: add calc.py addition helper"

    # 7. Modify calc.py to verify diff endpoint
    edit_res = await client.put(
        f"/api/v1/projects/{proj.id}/code/file",
        json={"path": "calc.py", "content": "def add(x, y):\n    # Optimized addition\n    return x + y\n"},
        headers=dev_headers
    )
    assert edit_res.status_code == 200

    # 8. Check Git Diff
    diff_res = await client.get(f"/api/v1/projects/{proj.id}/code/git/diff?path=calc.py", headers=dev_headers)
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert "Optimized addition" in diff_data["diff"]
    assert "calc.py" in diff_data["files_changed"]

    # 9. Commit the modification
    commit_res2 = await client.post(
        f"/api/v1/projects/{proj.id}/code/git/commit",
        json={"message": "refactor: add optimization comment to calc.py"},
        headers=dev_headers
    )
    assert commit_res2.status_code == 200
    assert len(commit_res2.json()["commit_sha"]) == 40

    # Working tree should now be clean
    status_res3 = await client.get(f"/api/v1/projects/{proj.id}/code/git/status", headers=dev_headers)
    assert status_res3.status_code == 200
    assert status_res3.json()["is_clean"] is True


@pytest.mark.asyncio
async def test_code_studio_git_rbac(
    client: AsyncClient,
    db_session: AsyncSession
):
    """Verify that VIEWER role is restricted from Git commit and branch creation."""
    # 1. Create Viewer User and Owner User
    owner = User(
        email="owner_git@example.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Git Owner",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True
    )
    viewer = User(
        email="viewer_git@example.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Git Viewer",
        role=UserRole.VIEWER,
        is_active=True,
        is_approved=True
    )
    db_session.add_all([owner, viewer])
    await db_session.commit()
    await db_session.refresh(owner)
    await db_session.refresh(viewer)

    proj = Project(
        name="RBAC Git Project",
        repository_url="https://github.com/example/rbac-git",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=owner.id
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    member = ProjectMember(project_id=proj.id, user_id=viewer.id, role=UserRole.VIEWER)
    db_session.add(member)
    await db_session.commit()

    viewer_token = create_access_token(subject=str(viewer.id))
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Viewer can view git status
    v_status = await client.get(f"/api/v1/projects/{proj.id}/code/git/status", headers=viewer_headers)
    assert v_status.status_code == 200

    # Viewer CANNOT commit changes (403 Forbidden)
    v_commit = await client.post(
        f"/api/v1/projects/{proj.id}/code/git/commit",
        json={"message": "Unauthorized commit"},
        headers=viewer_headers
    )
    assert v_commit.status_code == 403

    # Viewer CANNOT switch or create branches (403 Forbidden)
    v_branch = await client.post(
        f"/api/v1/projects/{proj.id}/code/git/branches",
        json={"branch_name": "viewer-hack"},
        headers=viewer_headers
    )
    assert v_branch.status_code == 403
