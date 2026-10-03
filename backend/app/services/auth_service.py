from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.domain import User, AuditLog
from app.schemas.auth import UserRegister, UserLogin
from app.core.security import get_password_hash, verify_password


async def register_new_user(db: AsyncSession, payload: UserRegister) -> User:
    # 1. Check for existing account by normalized email
    stmt = select(User).where(User.email == payload.email)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # 2. Hash password & create user
    hashed_pwd = get_password_hash(payload.password)
    user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        role=payload.role,
        is_active=True
    )
    db.add(user)
    await db.flush()

    # 3. Create Audit Log
    audit_entry = AuditLog(
        actor_id=user.id,
        action="USER_REGISTERED",
        resource_type="USER",
        resource_id=str(user.id),
        details={"email": user.email, "role": user.role.value}
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, payload: UserLogin) -> User:
    stmt = select(User).where(User.email == payload.email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )

    # Create Audit Log for login event
    audit_entry = AuditLog(
        actor_id=user.id,
        action="USER_LOGIN",
        resource_type="USER",
        resource_id=str(user.id),
        details={"email": user.email}
    )
    db.add(audit_entry)
    await db.commit()
    return user
