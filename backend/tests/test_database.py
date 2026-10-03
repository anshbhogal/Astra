import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.domain import User, UserRole, Project, LanguageFramework, AuditLog
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_user_project_relationship_persistence(db_session: AsyncSession):
    # Create User
    user = User(
        email="dbuser@example.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="DB Test User",
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create Project owned by User
    project = Project(
        name="DB Service",
        repository_url="https://github.com/example/dbservice",
        language_framework=LanguageFramework.PYTHON_FLASK,
        owner_id=user.id
    )
    db_session.add(project)

    # Create Audit Log
    log = AuditLog(
        actor_id=user.id,
        action="TEST_ACTION",
        resource_type="PROJECT",
        resource_id=str(project.id)
    )
    db_session.add(log)
    await db_session.commit()

    # Query back
    stmt = select(User).where(User.id == user.id)
    retrieved_user = (await db_session.execute(stmt)).scalar_one()
    assert retrieved_user.email == "dbuser@example.com"
