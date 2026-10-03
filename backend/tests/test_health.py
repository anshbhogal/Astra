import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ASTRA"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_check_endpoint(client: AsyncClient):
    response = await client.get("/health/ready")
    assert response.status_code in [200, 53] # Returns 200 if ready or 503 if mock redis is offline
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
