from typing import Optional
from fastapi import APIRouter, Depends, status, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    Token,
    RefreshTokenRequest,
    ChangePasswordRequest
)
from app.services import auth_service
from app.core.security import (
    get_current_user,
    create_access_token,
    create_refresh_token,
    verify_and_rotate_refresh_token,
    revoke_token,
    oauth2_scheme
)
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.domain import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account."""
    user = await auth_service.register_new_user(db, payload)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate credentials and issue JWT access token and opaque httpOnly refresh token."""
    user = await auth_service.authenticate_user(db, payload)
    access_token = create_access_token(subject=user.id, token_version=user.token_version)
    refresh_token = await create_refresh_token(user_id=user.id, token_version=user.token_version)

    # Set httpOnly cookie for refresh token
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth"
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=Token)
async def refresh_tokens(
    request: Request,
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """Rotate refresh token and issue new 15-minute access token."""
    refresh_token = None
    if payload and payload.refresh_token:
        refresh_token = payload.refresh_token
    else:
        refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token"
        )

    user, new_access_token, new_refresh_token = await verify_and_rotate_refresh_token(db, refresh_token)

    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=new_refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth"
    )

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user)
):
    """Denylist active access token and delete refresh token."""
    refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    await revoke_token(token, refresh_token)
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path="/api/v1/auth"
    )
    return {"message": "Successfully logged out"}


@router.post("/change-password", response_model=UserResponse)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Change current authenticated user's password (e.g. required first login)."""
    user = await auth_service.change_user_password(db, current_user, payload)
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Retrieve authenticated user profile."""
    return current_user
