import asyncio
import sys
from sqlalchemy import select
from app.db.session import AsyncSessionLocal, engine, Base
from app.models.domain import User, UserRole, Project, LanguageFramework
from app.core.security import get_password_hash

TEST_USERS = [
    {
        "email": "admin@astra.local",
        "full_name": "System Administrator",
        "role": UserRole.ADMIN,
        "password": "Password123!",
    },
    {
        "email": "dev@astra.local",
        "full_name": "Lead Developer",
        "role": UserRole.DEVELOPER,
        "password": "Password123!",
    },
    {
        "email": "tester@astra.local",
        "full_name": "QA Specialist",
        "role": UserRole.TESTER,
        "password": "Password123!",
    },
    {
        "email": "viewer@astra.local",
        "full_name": "Guest Observer",
        "role": UserRole.VIEWER,
        "password": "Password123!",
    },
]

TEST_PROJECTS = [
    {
        "name": "ASTRA Core Backend",
        "description": "Intelligent automated software testing platform core FastAPI microservice.",
        "repository_url": "https://github.com/astra-testing/astra-backend",
        "default_branch": "main",
        "language_framework": LanguageFramework.PYTHON_FASTAPI,
        "owner_email": "admin@astra.local",
    },
    {
        "name": "Payment Gateway API",
        "description": "High-throughput financial transaction processing microservice.",
        "repository_url": "https://github.com/astra-testing/payment-gateway",
        "default_branch": "main",
        "language_framework": LanguageFramework.NODE_EXPRESS,
        "owner_email": "dev@astra.local",
    },
    {
        "name": "E-Commerce Inventory Service",
        "description": "Spring Boot microservice managing catalog inventory and order events.",
        "repository_url": "https://github.com/astra-testing/ecommerce-inventory",
        "default_branch": "master",
        "language_framework": LanguageFramework.JAVA_SPRING,
        "owner_email": "tester@astra.local",
    },
]


async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print("🌱 Seeding ASTRA Database with Testing Credentials...")

        created_users = {}
        for user_data in TEST_USERS:
            stmt = select(User).where(User.email == user_data["email"])
            res = await session.execute(stmt)
            existing_user = res.scalar_one_or_none()

            if not existing_user:
                hashed_pw = get_password_hash(user_data["password"])
                user = User(
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    hashed_password=hashed_pw,
                    is_active=True,
                )
                session.add(user)
                await session.flush()
                print(f"  ✅ Created User: {user.email} [{user.role.value}]")
                created_users[user.email] = user
            else:
                print(f"  ℹ️ User already exists: {existing_user.email}")
                created_users[existing_user.email] = existing_user

        for proj_data in TEST_PROJECTS:
            stmt = select(Project).where(Project.name == proj_data["name"])
            res = await session.execute(stmt)
            existing_proj = res.scalar_one_or_none()

            if not existing_proj:
                owner = created_users.get(proj_data["owner_email"])
                if owner:
                    project = Project(
                        name=proj_data["name"],
                        description=proj_data["description"],
                        repository_url=proj_data["repository_url"],
                        default_branch=proj_data["default_branch"],
                        language_framework=proj_data["language_framework"],
                        owner_id=owner.id,
                    )
                    session.add(project)
                    print(f"  ✅ Created Sample Project: '{project.name}'")
            else:
                print(f"  ℹ️ Project already exists: '{existing_proj.name}'")

        await session.commit()
        print("🎉 Database Seeding Complete!")


if __name__ == "__main__":
    asyncio.run(seed_data())
