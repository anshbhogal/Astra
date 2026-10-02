# Phase 1 — Core Foundation & Infrastructure Implementation Guide

> **Module Focus:** Project Management, Data Persistence, User Authentication (RBAC), API Gateway Framework, and Developer Environment Infrastructure.

---

## 1. Phase Overview & Objectives

Phase 1 establishes the production-grade foundation for the **ASTRA** platform. It delivers the core backend service (FastAPI + Async SQLAlchemy), relational data models (PostgreSQL), task queue framework (Celery + Redis), authentication/RBAC layer, responsive React dashboard shell, and containerized Docker setup.

### Key Deliverables
1. **Repository Structure & Monorepo Configuration:** Standardized directory layout for `backend`, `frontend`, `engine`, `ai`, `ml`, and `docker`.
2. **PostgreSQL Relational Schema & ORM:** Declarative async SQLAlchemy 2.0 models for users, projects, repositories, environments, and audit logs.
3. **Authentication & RBAC System:** JWT-based OAuth2 authentication supporting four user roles: `Admin`, `Developer`, `Tester`, and `Viewer`.
4. **Project Management REST APIs:** Full CRUD endpoints for creating, updating, listing, and configuring software testing projects.
5. **React Dashboard Skeleton:** UI shell featuring navigation, dark theme design system, auth flows, and project management views.
6. **Containerization Engine:** Multi-container `docker-compose.yml` orchestrating PostgreSQL, Redis, FastAPI, Celery Workers, and Vite frontend.

---

## 2. Technical Stack Specifications

- **Backend Framework:** FastAPI `0.110+` running on Python `3.11+` with `uvicorn` / `gunicorn`.
- **ORM & Database:** SQLAlchemy `2.0+` (async engine via `asyncpg`), PostgreSQL `16`, Alembic for schema migrations.
- **Queue & Async Worker:** Celery `5.3+` backed by Redis `7.2` key-value store.
- **Frontend Framework:** React `18+` compiled via Vite, styled with Tailwind CSS, `lucide-react` icons, `react-router-dom` v6.
- **Authentication:** `python-jose` for JWT decoding/signing, `passlib[bcrypt]` for password hashing.

---

## 3. Database Schema & Data Models

### Entity Relationship Architecture

```text
┌────────────────┐        1:N        ┌─────────────────┐
│     users      ├───────────────────►│    projects     │
└───────┬────────┘                   └────────┬────────┘
        │                                     │
        │ 1:N                                 │ 1:N
        ▼                                     ▼
┌────────────────┐                   ┌─────────────────┐
│   audit_logs   │                   │  project_configs│
└────────────────┘                   └─────────────────┘
```

### SQLAlchemy Model Declarations (`backend/app/models/domain.py`)

```python
from datetime import datetime
from enum import Enum
import uuid
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase):
    pass

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
    VIEWER = "VIEWER"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.DEVELOPER, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    projects: Mapped[list["Project"]] = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

class LanguageFramework(str, Enum):
    PYTHON_FASTAPI = "PYTHON_FASTAPI"
    PYTHON_FLASK = "PYTHON_FLASK"
    NODE_EXPRESS = "NODE_EXPRESS"
    JAVA_SPRING = "JAVA_SPRING"
    OTHER = "OTHER"

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    repository_url: Mapped[str] = mapped_column(String(500), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    language_framework: Mapped[LanguageFramework] = mapped_column(SQLEnum(LanguageFramework), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    environment_vars: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="projects")
```

---

## 4. API Endpoints & Controller Logic

### Authentication & Project Routers (`backend/app/api/v1/projects.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.domain import User, UserRole
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role Viewer is not permitted to create projects."
        )
    return await project_service.create_new_project(db, payload, current_user.id)

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await project_service.get_projects(db, skip=skip, limit=limit)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await project_service.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

---

## 5. Role-Based Access Control (RBAC) Matrix

| Action | Admin | Developer | Tester | Viewer |
| :--- | :---: | :---: | :---: | :---: |
| **Manage Users & System Settings** | ✅ | ❌ | ❌ | ❌ |
| **Create & Configure Projects** | ✅ | ✅ | ✅ | ❌ |
| **Trigger Test Generation / Execution** | ✅ | ✅ | ✅ | ❌ |
| **View Test Results & Analytics** | ✅ | ✅ | ✅ | ✅ |
| **Manage Bug Reports & Root Cause Logs** | ✅ | ✅ | ✅ | ❌ |

---

## 6. Frontend Dashboard Shell (`frontend/src/App.tsx`)

The React UI provides a modern, dark-themed responsive dashboard using Tailwind CSS:

```tsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import DashboardOverview from './pages/DashboardOverview';
import ProjectsList from './pages/ProjectsList';
import ProjectDetail from './pages/ProjectDetail';
import Login from './pages/Login';
import { useAuthStore } from './store/authStore';

export default function App() {
  const { token } = useAuthStore();

  if (!token) {
    return <Login />;
  }

  return (
    <BrowserRouter>
      <div className="flex h-screen bg-slate-950 text-slate-100 font-sans">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Navbar />
          <main className="flex-1 overflow-y-auto p-6 bg-slate-900/50">
            <Routes>
              <Route path="/" element={<DashboardOverview />} />
              <Route path="/projects" element={<ProjectsList />} />
              <Route path="/projects/:id" element={<ProjectDetail />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}
```

---

## 7. Infrastructure Setup (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: astra_postgres
    environment:
      POSTGRES_DB: astra_db
      POSTGRES_USER: astra_user
      POSTGRES_PASSWORD: astra_secret_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: astra_redis
    ports:
      - "6379:6379"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: astra_backend
    environment:
      DATABASE_URL: postgresql+asyncpg://astra_user:astra_secret_password@postgres:5432/astra_db
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET: super_secure_astra_jwt_secret_key_2026
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.core.celery_app worker --loglevel=info
    container_name: astra_celery
    environment:
      DATABASE_URL: postgresql+asyncpg://astra_user:astra_secret_password@postgres:5432/astra_db
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - backend

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: astra_frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

---

## 8. Verification & Test Plan

1. **Database Migration Verification:**
   - Execute `alembic upgrade head`. Verify table creation for `users` and `projects` in PostgreSQL.
2. **API Integration Test:**
   - Run `pytest backend/tests/test_auth.py` and `pytest backend/tests/test_projects.py`. Verify HTTP 201 on project creation and HTTP 403 when a `VIEWER` role attempts creation.
3. **Container Readiness:**
   - Run `docker-compose up -d`. Verify all 5 containers (`astra_postgres`, `astra_redis`, `astra_backend`, `astra_celery`, `astra_frontend`) reach healthy running status. Access `http://localhost:8000/docs` to inspect OpenAPI UI.
