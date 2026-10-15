"""Security tests for Phase 1 Task P1-4: API Rate Limiting."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.models.domain import User, UserRole
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_login_rate_limiting_blocks_after_5_attempts(
    client: AsyncClient,
    db_session: AsyncSession
):
    """The 6th login attempt within one minute must trigger HTTP 429 Too Many Requests."""
    prev_enabled = limiter.enabled
    limiter.enabled = True
    limiter.reset()

    try:
        # Create approved user
        user = User(
            email="ratelimit_user@example.com",
            hashed_password=get_password_hash("ValidPass123!"),
            full_name="Rate Limit Target",
            role=UserRole.DEVELOPER,
            is_active=True,
            is_approved=True,
            token_version=1
        )
        db_session.add(user)
        await db_session.commit()

        login_payload = {
            "email": "ratelimit_user@example.com",
            "password": "WrongPassword123!"
        }

        # First 5 login attempts should return 401 (Unauthorized)
        for i in range(5):
            resp = await client.post("/api/v1/auth/login", json=login_payload)
            assert resp.status_code == 401, f"Attempt {i+1} expected 401, got {resp.status_code}: {resp.text}"

        # 6th attempt must be rejected with 429 Too Many Requests
        blocked_resp = await client.post("/api/v1/auth/login", json=login_payload)
        assert blocked_resp.status_code == 429, f"Expected 429, got {blocked_resp.status_code}: {blocked_resp.text}"
        assert "rate limit exceeded" in blocked_resp.text.lower() or "too many requests" in blocked_resp.text.lower()
    finally:
        limiter.reset()
        limiter.enabled = prev_enabled
