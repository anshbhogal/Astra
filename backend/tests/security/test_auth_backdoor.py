import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.domain import User, UserRole
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_admin_backdoor_bypass_fails(client: AsyncClient, db_session: AsyncSession):
    """
    Security Test: Ensure that the hardcoded plaintext bypass for admin@astra.local
    (Admin123! or Password123!) is completely disabled and rejected with 401 Unauthorized
    when the user has a different real password.
    """
    real_password = "RealCustomSecurePassword987!"
    admin = User(
        email="admin@astra.local",
        hashed_password=get_password_hash(real_password),
        full_name="System Administrator",
        role=UserRole.ADMIN,
        is_active=True,
        is_approved=True,
    )
    db_session.add(admin)
    await db_session.commit()

    # 1. Attempt login with backdoor candidate 'Admin123!' -> MUST BE 401
    resp1 = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@astra.local", "password": "Admin123!"}
    )
    assert resp1.status_code == 401, f"Expected 401 Unauthorized for Admin123!, got {resp1.status_code}"

    # 2. Attempt login with backdoor candidate 'Password123!' -> MUST BE 401
    resp2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@astra.local", "password": "Password123!"}
    )
    assert resp2.status_code == 401, f"Expected 401 Unauthorized for Password123!, got {resp2.status_code}"

    # 3. Legitimate login with real password -> MUST BE 200
    resp3 = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@astra.local", "password": real_password}
    )
    assert resp3.status_code == 200, f"Expected 200 OK for valid password, got {resp3.status_code}"
    data = resp3.json()
    assert "access_token" in data
