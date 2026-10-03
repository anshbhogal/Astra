import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.domain import User, UserRole, Project, LanguageFramework

# In-memory SQLite for fast, isolated async testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@astra.local",
        hashed_password=get_password_hash("AdminSecret123!"),
        full_name="System Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def dev_user(db_session: AsyncSession) -> User:
    user = User(
        email="developer@astra.local",
        hashed_password=get_password_hash("DevSecret123!"),
        full_name="Lead Developer",
        role=UserRole.DEVELOPER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def tester_user(db_session: AsyncSession) -> User:
    user = User(
        email="tester@astra.local",
        hashed_password=get_password_hash("TesterSecret123!"),
        full_name="QA Tester",
        role=UserRole.TESTER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    user = User(
        email="viewer@astra.local",
        hashed_password=get_password_hash("ViewerSecret123!"),
        full_name="Guest Viewer",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    token = create_access_token(subject=admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def dev_headers(dev_user: User) -> dict:
    token = create_access_token(subject=dev_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(viewer_user: User) -> dict:
    token = create_access_token(subject=viewer_user.id)
    return {"Authorization": f"Bearer {token}"}
