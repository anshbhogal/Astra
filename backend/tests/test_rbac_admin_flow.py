import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

from app.db.session import async_session_factory
from app.models.domain import FailureAnalysisModel

@pytest.mark.asyncio
async def test_admin_governance_and_rbac_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as Admin
        admin_res = await client.post("/api/v1/auth/login", json={"email": "admin@astra.local", "password": "Password123!"})
        assert admin_res.status_code == 200, admin_res.text
        admin_token = admin_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Unique email for run
        rand_id = uuid.uuid4().hex[:6]
        user_email = f"self_{rand_id}@example.com"

        # 2. Self-register a new user (pending approval)
        reg_res = await client.post("/api/v1/auth/register", json={
            "full_name": f"Dev User {rand_id}",
            "email": user_email,
            "password": "Password123!",
            "role": "DEVELOPER"
        })
        assert reg_res.status_code == 201
        registered_id = reg_res.json()["id"]

        # 3. Verify unapproved user cannot log in (403 Forbidden)
        login_unapproved = await client.post("/api/v1/auth/login", json={"email": user_email, "password": "Password123!"})
        assert login_unapproved.status_code == 403

        # 4. Admin lists pending users and approves the user
        pending_res = await client.get("/api/v1/admin/users/pending", headers=admin_headers)
        assert pending_res.status_code == 200
        pending_list = pending_res.json()
        target_pending = next((u for u in pending_list if u["id"] == registered_id), None)
        assert target_pending is not None

        approve_res = await client.post(f"/api/v1/admin/users/{registered_id}/approve", json={"role": "DEVELOPER"}, headers=admin_headers)
        assert approve_res.status_code == 200

        # 5. Approved user can now log in
        login_approved = await client.post("/api/v1/auth/login", json={"email": user_email, "password": "Password123!"})
        assert login_approved.status_code == 200
        dev_token = login_approved.json()["access_token"]
        dev_headers = {"Authorization": f"Bearer {dev_token}"}

        # 6. Verify non-admin Developer CANNOT add a repository
        dev_create_repo = await client.post("/api/v1/projects/", json={
            "name": f"Unauthorized Repo {rand_id}",
            "repository_url": "https://github.com/test/repo",
            "language_framework": "PYTHON_FASTAPI"
        }, headers=dev_headers)
        assert dev_create_repo.status_code == 403

        # 7. Admin directly generates a Tester ID
        tester_email = f"tester_{rand_id}@example.com"
        gen_tester_res = await client.post("/api/v1/admin/users", json={
            "full_name": f"Tester Pro {rand_id}",
            "email": tester_email,
            "password": "Password123!",
            "role": "TESTER"
        }, headers=admin_headers)
        assert gen_tester_res.status_code == 201

        # 8. Check Developer initially sees 0 assigned repositories
        dev_repos = await client.get("/api/v1/projects/", headers=dev_headers)
        assert dev_repos.status_code == 200
        assert dev_repos.json()["total"] == 0

        # 9. Admin assigns the Developer and Tester to a project
        all_repos = (await client.get("/api/v1/projects/", headers=admin_headers)).json()["items"]
        assert len(all_repos) > 0
        target_repo = all_repos[0]
        repo_id = target_repo["id"]

        assign_res = await client.post(f"/api/v1/projects/{repo_id}/members", json={
            "user_id": registered_id,
            "role": "DEVELOPER"
        }, headers=admin_headers)
        assert assign_res.status_code == 201

        # 10. Developer now sees only the assigned repository
        dev_repos_after = await client.get("/api/v1/projects/", headers=dev_headers)
        assert dev_repos_after.status_code == 200
        assert dev_repos_after.json()["total"] == 1
        assert dev_repos_after.json()["items"][0]["id"] == repo_id

        # 11. Developer CANNOT run unit tests (only Tester & Admin)
        dev_run_test = await client.post(f"/api/v1/projects/{repo_id}/unit-tests/run", headers=dev_headers)
        assert dev_run_test.status_code == 403

        # 12. Login as Tester
        tester_login = await client.post("/api/v1/auth/login", json={"email": tester_email, "password": "Password123!"})
        assert tester_login.status_code == 200
        tester_token = tester_login.json()["access_token"]
        tester_headers = {"Authorization": f"Bearer {tester_token}"}

        # Assign Tester to repo
        tester_id = gen_tester_res.json()["id"]
        await client.post(f"/api/v1/projects/{repo_id}/members", json={
            "user_id": tester_id,
            "role": "TESTER"
        }, headers=admin_headers)

        # 13. Tester and Developer collaborate on defect comment
        dummy_defect_id = uuid.uuid4()
        async with async_session_factory() as session:
            defect = FailureAnalysisModel(
                id=dummy_defect_id,
                project_id=uuid.UUID(repo_id),
                test_result_id="tr_101",
                test_case_id="tc_auth_edge",
                category="ASSERTION_ERROR",
                summary="Auth boundary validation failed on unicode chars",
                error_message="AssertionError: 400 != 200",
                fingerprint="fp_dummy_101",
                status="OPEN"
            )
            session.add(defect)
            await session.commit()

        post_comment_res = await client.post(f"/api/v1/projects/{repo_id}/defects/{dummy_defect_id}/comments", json={
            "message": "Tester: Observed boundary failure on edge input payload.",
            "status_change": "UNDER_INVESTIGATION"
        }, headers=tester_headers)
        assert post_comment_res.status_code == 201
        assert post_comment_res.json()["user_role"] == "TESTER"

        # Developer replies
        dev_comment_res = await client.post(f"/api/v1/projects/{repo_id}/defects/{dummy_defect_id}/comments", json={
            "message": "Developer: Verified edge case, patched input sanitizer.",
            "status_change": "FIXED"
        }, headers=dev_headers)
        assert dev_comment_res.status_code == 201
        assert dev_comment_res.json()["user_role"] == "DEVELOPER"

        # Fetch comments thread
        get_comments = await client.get(f"/api/v1/projects/{repo_id}/defects/{dummy_defect_id}/comments", headers=dev_headers)
        assert get_comments.status_code == 200
        comments_list = get_comments.json()
        assert len(comments_list) == 2

        print("\nALL 13 RBAC, ADMIN GOVERNANCE & TESTER-DEVELOPER COLLABORATION CHECKS PASSED!")
