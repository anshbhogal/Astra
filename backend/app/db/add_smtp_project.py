import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.domain import User, Project, LanguageFramework


async def add_smtp_project():
    async with AsyncSessionLocal() as session:
        # Find admin user
        stmt = select(User).where(User.email == "admin@astra.local")
        res = await session.execute(stmt)
        admin_user = res.scalar_one_or_none()

        if not admin_user:
            print("❌ Admin user not found! Seed database first.")
            return

        # Check if project already exists
        repo_url = "https://github.com/anshbhogal/email_smtp"
        stmt_proj = select(Project).where(Project.repository_url == repo_url)
        res_proj = await session.execute(stmt_proj)
        existing_proj = res_proj.scalar_one_or_none()

        if existing_proj:
            print(f"ℹ️ Project 'email_smtp' already exists with ID: {existing_proj.id}")
            return existing_proj

        new_project = Project(
            name="Email SMTP Microservice",
            description="Email SMTP microservice target repository for ASTRA automated testing.",
            repository_url=repo_url,
            default_branch="main",
            language_framework=LanguageFramework.PYTHON_FASTAPI,
            owner_id=admin_user.id
        )
        session.add(new_project)
        await session.commit()
        await session.refresh(new_project)
        print(f"✅ Created Project 'Email SMTP Microservice' (ID: {new_project.id}) owned by Admin ({admin_user.email})!")
        return new_project


if __name__ == "__main__":
    asyncio.run(add_smtp_project())
