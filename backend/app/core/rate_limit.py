"""Rate Limiting infrastructure for ASTRA API using slowapi and Redis."""

from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings


def get_rate_limit_key(request: Request) -> str:
    """Rate limit key function: uses authenticated user ID if present, otherwise client IP."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        from app.core.security import decode_token
        payload = decode_token(token)
        if payload and "sub" in payload:
            return f"user:{payload['sub']}"
    return get_remote_address(request) or "127.0.0.1"


storage_uri = settings.REDIS_URL if settings.REDIS_URL else "memory://"

limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=storage_uri,
    strategy="fixed-window",
    enabled=settings.ENVIRONMENT != "test"
)
