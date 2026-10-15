import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    payload = {
        "email": "newuser@example.com",
        "password": "Password123!",
        "full_name": "New Developer",
        "role": "DEVELOPER"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New Developer"
    assert data["role"] == "DEVELOPER"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_admin_role_security_downgrade(client: AsyncClient):
    # Public registration must not allow choosing ADMIN role
    payload = {
        "email": "hacker@example.com",
        "password": "Password123!",
        "full_name": "Fake Admin",
        "role": "ADMIN"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in [400, 422]
    assert "Administrator role is not permitted" in str(response.json())


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient):
    payload = {
        "email": "dup@example.com",
        "password": "Password123!",
        "full_name": "Original User"
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    from sqlalchemy import select
    from app.models.domain import User

    # Register first
    reg_payload = {
        "email": "loginuser@example.com",
        "password": "Password123!",
        "full_name": "Login Tester"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # Administrator approves the registered user
    stmt = select(User).where(User.email == "loginuser@example.com")
    user = (await db_session.execute(stmt)).scalar_one()
    user.is_approved = True
    await db_session.commit()

    # Login
    login_payload = {
        "email": "loginuser@example.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "loginuser@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password_fails(client: AsyncClient):
    reg_payload = {
        "email": "wrongpwd@example.com",
        "password": "Password123!",
        "full_name": "Wrong Pwd User"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrongpwd@example.com",
        "password": "WrongPassword!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authorized(client: AsyncClient, dev_headers: dict):
    response = await client.get("/api/v1/auth/me", headers=dev_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "developer@astra.local"
    assert data["role"] == "DEVELOPER"
