import asyncio
from sqlalchemy import text
from app.db.session import engine, Base
import app.models # ensure all models are registered

async def run_migration():
    print("Running RBAC & Team Collaboration schema migration...")
    async with engine.begin() as conn:
        # 1. Add is_approved to users
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;"))
        # Ensure existing users are approved
        await conn.execute(text("UPDATE users SET is_approved = TRUE WHERE is_approved IS NULL OR email = 'admin@astra.local';"))
        
        # 2. Add status and assigned_to_id to failure_analyses
        await conn.execute(text("ALTER TABLE failure_analyses ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'OPEN';"))
        await conn.execute(text("ALTER TABLE failure_analyses ADD COLUMN IF NOT EXISTS assigned_to_id UUID REFERENCES users(id) ON DELETE SET NULL;"))

        # 3. Create missing tables (project_members, defect_comments)
        await conn.run_sync(Base.metadata.create_all)
        print("RBAC & Team Collaboration migration finished successfully!")

if __name__ == "__main__":
    asyncio.run(run_migration())
