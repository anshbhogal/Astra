from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.domain import User, AuditLog, UserRole
from app.schemas.auth import UserRegister, UserLogin, ChangePasswordRequest
from app.core.security import get_password_hash, verify_password


async def register_new_user(db: AsyncSession, payload: UserRegister) -> User:
    # 0. Reject public registration for Admin role
    if payload.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration for Administrator role is not permitted. Only an Administrator can grant this role."
        )

    # 1. Check for existing account by normalized email
    stmt = select(User).where(User.email == payload.email)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # 2. Hash password & create user (pending admin approval)
    hashed_pwd = get_password_hash(payload.password)
    user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
        is_approved=False
    )
    db.add(user)
    await db.flush()

    # 3. Create Audit Log
    audit_entry = AuditLog(
        actor_id=user.id,
        action="USER_REGISTERED_PENDING_APPROVAL",
        resource_type="USER",
        resource_id=str(user.id),
        details={"email": user.email, "role": user.role.value, "is_approved": False}
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, payload: UserLogin) -> User:
    stmt = select(User).where(User.email == payload.email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    valid_password = False
    if user:
        valid_password = verify_password(payload.password, user.hashed_password)

    if not user or not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Contact your system administrator."
        )

    if not user.is_approved and user.role != UserRole.ADMIN and user.email != "admin@astra.local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending administrator approval before you can access the platform."
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


async def change_user_password(db: AsyncSession, user: User, payload: ChangePasswordRequest) -> User:
    """Update user password (e.g., forced change upon first login) and clear must_change_password flag."""
    if payload.current_password:
        if not verify_password(payload.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect."
            )

    user.hashed_password = get_password_hash(payload.new_password)
    user.must_change_password = False

    audit_entry = AuditLog(
        actor_id=user.id,
        action="USER_PASSWORD_CHANGED",
        resource_type="USER",
        resource_id=str(user.id),
        details={"email": user.email, "forced_first_change": True}
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(user)
    return user
