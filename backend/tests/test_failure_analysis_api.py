"""
API integration unit tests for Phase 6 Failure Analysis & Defects REST API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_failure_analysis_api_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Test health endpoint
        res = await client.get("/api/v1/health")
        assert res.status_code == 200

        # 2. Test GET defects for non-existent project (should return empty list)
        dummy_project_id = "00000000-0000-0000-0000-000000000001"
        res = await client.get(f"/api/v1/projects/{dummy_project_id}/defects")
        assert res.status_code == 200
        assert res.json() == []
