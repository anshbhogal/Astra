import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict, Tuple

import jwt
import redis.asyncio as aioredis
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.models.domain import User, UserRole

# Password hashing context using modern Argon2 via pwdlib
password_hash_context = PasswordHash((Argon2Hasher(),))

# OAuth2 bearer scheme pointing to login route
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            await client.ping()
            _redis_client = client
        except Exception:
            return None
    return _redis_client


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hash_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return password_hash_context.hash(password)


def create_access_token(
    subject: Any,
    token_version: int = 1,
    expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    jti = str(uuid.uuid4())
    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "jti": jti,
        "token_version": token_version,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except (jwt.PyJWTError, Exception):
        return None


async def create_refresh_token(user_id: uuid.UUID, token_version: int) -> str:
    token = secrets.token_urlsafe(48)
    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    redis = await get_redis_client()
    if redis:
        try:
            key = f"refresh_token:{token}"
            val = json.dumps({"user_id": str(user_id), "token_version": token_version})
            await redis.set(key, val, ex=ttl_seconds)
        except Exception:
            pass
    return token


async def verify_and_rotate_refresh_token(
    db: AsyncSession,
    refresh_token: str
) -> Tuple[User, str, str]:
    redis = await get_redis_client()
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session cache unavailable"
        )
    key = f"refresh_token:{refresh_token}"
    raw = None
    try:
        raw = await redis.get(key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query session cache"
        )

    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
    user_id_str = data.get("user_id")
    stored_token_version = data.get("token_version")

    user_uuid = uuid.UUID(user_id_str)
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        try:
            await redis.delete(key)
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.is_active:
        try:
            await redis.delete(key)
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

    if not user.is_approved and user.role != UserRole.ADMIN and user.email != "admin@astra.local":
        try:
            await redis.delete(key)
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is pending administrator approval")

    if user.token_version != stored_token_version:
        try:
            await redis.delete(key)
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired due to credential update, please log in again")

    # Rotate: delete old refresh token
    try:
        await redis.delete(key)
    except Exception:
        pass

    new_refresh_token = await create_refresh_token(user.id, user.token_version)
    new_access_token = create_access_token(user.id, token_version=user.token_version)
    return user, new_access_token, new_refresh_token


async def revoke_token(token: str, refresh_token: Optional[str] = None) -> None:
    redis = await get_redis_client()
    payload = decode_token(token)
    if payload and redis:
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            now = datetime.now(timezone.utc).timestamp()
            remaining_seconds = max(1, int(exp - now))
            try:
                await redis.set(f"denylist:jti:{jti}", "revoked", ex=remaining_seconds)
            except Exception:
                pass

    if refresh_token and redis:
        try:
            await redis.delete(f"refresh_token:{refresh_token}")
        except Exception:
            pass


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    # Check JTI denylist in Redis
    jti = payload.get("jti")
    if jti:
        redis = await get_redis_client()
        if redis:
            try:
                is_revoked = await redis.get(f"denylist:jti:{jti}")
                if is_revoked:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication token has been revoked",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            except HTTPException:
                raise
            except Exception:
                pass

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    # Check token version
    token_version = payload.get("token_version")
    if token_version is not None and token_version != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired due to security changes, please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Enforce is_approved
    if not user.is_approved and user.role != UserRole.ADMIN and user.email != "admin@astra.local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending administrator approval before you can access the platform."
        )

    return user
