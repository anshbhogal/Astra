import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_code_studio_editor_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as Admin
        admin_res = await client.post("/api/v1/auth/login", json={"email": "admin@astra.local", "password": "Password123!"})
        assert admin_res.status_code == 200
        admin_token = admin_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Get available project
        projects_res = await client.get("/api/v1/projects/", headers=headers)
        assert projects_res.status_code == 200
        projects = projects_res.json()["items"]
        assert len(projects) > 0
        project_id = projects[0]["id"]

        # 3. Fetch file tree
        tree_res = await client.get(f"/api/v1/projects/{project_id}/code/tree", headers=headers)
        assert tree_res.status_code == 200
        data = tree_res.json()
        assert "tree" in data
        assert isinstance(data["tree"], list)

        # 4. Create a test file
        create_res = await client.post(f"/api/v1/projects/{project_id}/code/file", json={
            "path": "test_sample.py",
            "content": "def test_math():\n    assert 1 + 1 == 2\n",
            "is_directory": False
        }, headers=headers)
        assert create_res.status_code == 201

        # 5. Read file
        read_res = await client.get(f"/api/v1/projects/{project_id}/code/file?path=test_sample.py", headers=headers)
        assert read_res.status_code == 200
        assert "assert 1 + 1 == 2" in read_res.json()["content"]
        assert read_res.json()["language"] == "python"

        # 6. Save modified file
        save_res = await client.put(f"/api/v1/projects/{project_id}/code/file", json={
            "path": "test_sample.py",
            "content": "def test_math():\n    assert 2 + 2 == 4\n"
        }, headers=headers)
        assert save_res.status_code == 200
        assert save_res.json()["status"] == "SAVED"

        # 7. Execute test runner from IDE
        run_res = await client.post(f"/api/v1/projects/{project_id}/code/run-tests", headers=headers)
        assert run_res.status_code == 200
        assert "output" in run_res.json()

        # 8. Fetch defects for IDE triage sidebar
        defects_res = await client.get(f"/api/v1/projects/{project_id}/code/defects", headers=headers)
        assert defects_res.status_code == 200
        assert isinstance(defects_res.json(), list)

        # 9. Clean up created file
        del_res = await client.delete(f"/api/v1/projects/{project_id}/code/file?path=test_sample.py", headers=headers)
        assert del_res.status_code == 200
