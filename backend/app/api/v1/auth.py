from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import UserRegister, UserLogin, UserResponse, Token
from app.services import auth_service
from app.core.security import get_current_user, create_access_token
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
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate credentials and issue JWT access token."""
    user = await auth_service.authenticate_user(db, payload)
    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Retrieve authenticated user profile."""
    return current_user
