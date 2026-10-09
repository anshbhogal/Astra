"""ASTRA Phase 8 End-to-End Selective Regression Engine Integration Test.
Verifies Git Diff Parsing -> AST Qualified Symbol Identity -> PKG Weighted Edge Reachability ->
TestCase Impact Mapping -> Safety Gate & Unknown Expander -> Dynamic Tiered Partitioning ->
DB Persistence -> REST API Endpoints.
"""

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import (
    User, Project, TestSuite, TestCase, LanguageFramework,
    RegressionAnalysisModel, CodeChangeManifestModel, EndpointImpactRecordModel, SelectiveExecutionRunModel
)
from app.services.regression_service import RegressionService
from app.core.security import create_access_token
from engine.regression.evaluators import RegressionOracleEvaluator


@pytest.mark.asyncio
async def test_phase8_full_e2e_pipeline(db_session: AsyncSession, client: AsyncClient):
    # 1. Setup Test User & Project
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"phase8_tester_{user_id.hex[:6]}@example.com",
        full_name="Phase 8 Regression Tester",
        hashed_password="hashed_pass_mock",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(user)

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name=f"Phase8_Regression_Project_{project_id.hex[:6]}",
        repository_url="https://github.com/example/regression_app",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=user_id,
    )
    db_session.add(project)

    # 2. Setup Test Suite & Test Cases
    suite_id = uuid.uuid4()
    suite = TestSuite(
        id=suite_id,
        project_id=project_id,
        name="Phase 8 Suite",
        total_cases=2,
    )
    db_session.add(suite)

    tc1_id = uuid.uuid4()
    tc1 = TestCase(
        id=tc1_id,
        suite_id=suite_id,
        name="Test Get User Profile",
        test_type="HAPPY_PATH",
        specification={
            "endpoint": "/api/v1/users",
            "method": "GET",
            "tags": ["smoke", "users"],
        },
    )
    db_session.add(tc1)

    tc2_id = uuid.uuid4()
    tc2 = TestCase(
        id=tc2_id,
        suite_id=suite_id,
        name="Test Delete Post",
        test_type="HAPPY_PATH",
        specification={
            "endpoint": "/api/v1/posts",
            "method": "DELETE",
            "tags": ["posts"],
        },
    )
    db_session.add(tc2)


    await db_session.commit()

    # 3. Perform Regression Service Analysis
    diff_text = """diff --git a/app/services/user_service.py b/app/services/user_service.py
@@ -10,2 +10,4 @@ class UserService:
-    def get_user(self, user_id: int):
-        return {"id": user_id}
+    def get_user(self, user_id: int, include_meta: bool = True):
+        return {"id": user_id, "meta": include_meta}
"""
    old_sources = {
        "app/services/user_service.py": "class UserService:\n    def get_user(self, user_id: int):\n        return {'id': user_id}\n"
    }
    new_sources = {
        "app/services/user_service.py": "class UserService:\n    def get_user(self, user_id: int, include_meta: bool = True):\n        return {'id': user_id, 'meta': include_meta}\n"
    }

    service = RegressionService(db_session)
    result = await service.analyze_regression_impact(
        project_id=project_id,
        base_commit="main~1",
        target_commit="HEAD",
        diff_text=diff_text,
        old_sources=old_sources,
        new_sources=new_sources,
    )

    assert result["status"] == "COMPLETED"
    assert result["analysis_id"] is not None
    assert result["summary"]["total_modified_files"] == 1
    assert result["summary"]["total_suite_tests"] == 2
    assert result["summary"]["selected_tier1_count"] == 1
    assert result["summary"]["deferred_tier2_count"] == 1
    assert result["summary"]["test_reduction_percent"] == 50.0

    # 4. Verify DB Records
    analysis_uuid = uuid.UUID(result["analysis_id"])
    analysis_stmt = select(RegressionAnalysisModel).where(RegressionAnalysisModel.id == analysis_uuid)
    db_analysis = (await db_session.execute(analysis_stmt)).scalar_one_or_none()
    assert db_analysis is not None
    assert db_analysis.selected_tier1_count == 1
    assert db_analysis.deferred_tier2_count == 1

    manifest_stmt = select(CodeChangeManifestModel).where(CodeChangeManifestModel.regression_analysis_id == analysis_uuid)
    manifests = list((await db_session.execute(manifest_stmt)).scalars().all())
    assert len(manifests) == 1
    assert manifests[0].new_path == "app/services/user_service.py"

    # 5. REST API Endpoint Tests
    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}


    # Trigger via API
    api_resp = await client.post(
        f"/api/v1/projects/{project_id}/regression/analyze",
        headers=headers,
        json={
            "base_commit": "main~1",
            "target_commit": "HEAD",
            "diff_text": diff_text,
            "async_mode": False,
        },
    )
    assert api_resp.status_code == 200
    api_json = api_resp.json()
    assert api_json["status"] == "COMPLETED"

    # List Analyses via API
    list_resp = await client.get(f"/api/v1/projects/{project_id}/regression/analyses", headers=headers)
    assert list_resp.status_code == 200
    list_json = list_resp.json()
    assert len(list_json["analyses"]) >= 2

    # Get Details via API
    get_resp = await client.get(f"/api/v1/regression/analyses/{result['analysis_id']}", headers=headers)
    assert get_resp.status_code == 200
    get_json = get_resp.json()
    assert get_json["id"] == result["analysis_id"]
    assert len(get_json["manifests"]) == 1
