"""Security tests for Phase 1 Task P1-3: JWT, Refresh Tokens, and Revocation."""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.security import create_access_token, decode_token, get_password_hash
from app.models.domain import User, UserRole


def test_jwt_secret_validation_rules():
    """Require JWT secret length >= 32 chars and reject known insecure defaults."""
    # 1. Reject secrets shorter than 32 characters
    with pytest.raises(ValidationError) as exc1:
        Settings(JWT_SECRET="too_short_key_123")
    assert "at least 32 characters" in str(exc1.value)

    # 2. Reject known insecure patterns
    with pytest.raises(ValidationError) as exc2:
        Settings(JWT_SECRET="12345678901234567890123456789012")
    assert "cannot use a known insecure default" in str(exc2.value)

    # 3. Accept strong >= 32 char secret
    valid_settings = Settings(JWT_SECRET="a_very_strong_cryptographic_jwt_secret_key_32bytes_min")
    assert valid_settings.JWT_SECRET == "a_very_strong_cryptographic_jwt_secret_key_32bytes_min"


def test_access_token_strict_ttl_and_claims(monkeypatch):
    """Access tokens must carry jti, token_version, type='access', and expire in ~15 minutes."""
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id, token_version=2)
    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["token_version"] == 2
    assert payload["type"] == "access"
    assert "jti" in payload
    assert len(payload["jti"]) >= 16

    # Verify TTL is ~15 minutes (900 seconds)
    exp = payload["exp"]
    iat = payload["iat"]
    ttl_seconds = exp - iat
    assert 890 <= ttl_seconds <= 910


@pytest.mark.asyncio
async def test_unapproved_and_inactive_users_rejected_by_auth(
    client: AsyncClient,
    db_session: AsyncSession
):
    """Users that are unapproved or inactive must be denied access."""
    # 1. Unapproved user
    unapproved = User(
        email="pending_user@example.com",
        hashed_password=get_password_hash("ValidPass123!"),
        full_name="Pending User",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=False
    )
    db_session.add(unapproved)
    await db_session.commit()
    await db_session.refresh(unapproved)

    token_unapproved = create_access_token(subject=unapproved.id, token_version=unapproved.token_version)
    res1 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_unapproved}"})
    assert res1.status_code == 403
    assert "pending administrator approval" in res1.json()["detail"]

    # 2. Inactive user
    inactive = User(
        email="inactive_user@example.com",
        hashed_password=get_password_hash("ValidPass123!"),
        full_name="Inactive User",
        role=UserRole.DEVELOPER,
        is_active=False,
        is_approved=True
    )
    db_session.add(inactive)
    await db_session.commit()
    await db_session.refresh(inactive)

    token_inactive = create_access_token(subject=inactive.id, token_version=inactive.token_version)
    res2 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_inactive}"})
    assert res2.status_code == 401
    assert "inactive" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_token_version_invalidation_on_credential_change(
    client: AsyncClient,
    db_session: AsyncSession
):
    """Incrementing user.token_version must immediately invalidate all previous access tokens."""
    user = User(
        email="active_user@example.com",
        hashed_password=get_password_hash("ValidPass123!"),
        full_name="Active User",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True,
        token_version=1
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Token with version 1
    token_v1 = create_access_token(subject=user.id, token_version=1)
    res_ok = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_v1}"})
    assert res_ok.status_code == 200

    # User increments token_version (e.g. password changed or admin revoke)
    user.token_version = 2
    await db_session.commit()

    # Old token with version 1 is now rejected
    res_invalid = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_v1}"})
    assert res_invalid.status_code == 401
    assert "Session expired" in res_invalid.json()["detail"]


@pytest.mark.asyncio
async def test_login_and_refresh_token_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession
):
    """Login issues access token and httpOnly refresh token; /auth/refresh rotates it."""
    user = User(
        email="cycle_user@example.com",
        hashed_password=get_password_hash("ValidPass123!"),
        full_name="Lifecycle User",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True,
        token_version=1
    )
    db_session.add(user)
    await db_session.commit()

    # 1. Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "cycle_user@example.com",
        "password": "ValidPass123!"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    refresh_token = login_data["refresh_token"]

    # Verify Set-Cookie header contains refresh token
    set_cookie = login_res.headers.get("set-cookie", "")
    assert settings.REFRESH_TOKEN_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie

    # 2. Refresh tokens using refresh_token in payload or cookie
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert "access_token" in new_data
    assert new_data["refresh_token"] != refresh_token  # Must be rotated

    # 3. Old refresh token should now be rejected (single-use rotation)
    stale_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert stale_res.status_code == 401


@pytest.mark.asyncio
async def test_logout_denylists_jwt_and_clears_cookie(
    client: AsyncClient,
    db_session: AsyncSession
):
    """Logout invalidates active access token in Redis and removes refresh token cookie."""
    user = User(
        email="logout_user@example.com",
        hashed_password=get_password_hash("ValidPass123!"),
        full_name="Logout User",
        role=UserRole.DEVELOPER,
        is_active=True,
        is_approved=True,
        token_version=1
    )
    db_session.add(user)
    await db_session.commit()

    # Login
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "logout_user@example.com",
        "password": "ValidPass123!"
    })
    login_data = login_res.json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    # Verify token works
    me_before = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_before.status_code == 200

    # Logout
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        cookies={settings.REFRESH_TOKEN_COOKIE_NAME: refresh_token}
    )
    assert logout_res.status_code == 200

    # Verify cookie was deleted
    set_cookie = logout_res.headers.get("set-cookie", "")
    assert f'{settings.REFRESH_TOKEN_COOKIE_NAME}=""' in set_cookie or f"{settings.REFRESH_TOKEN_COOKIE_NAME}=;" in set_cookie or "Max-Age=0" in set_cookie

    # Accessing /auth/me with revoked access token must now return 401
    me_after = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_after.status_code == 401
    assert "revoked" in me_after.json()["detail"]
