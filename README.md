# ASTRA — Intelligent Automated Software Testing & Defect Detection Platform

> **ASTRA** is a next-generation automated software quality and defect detection platform built upon a **hybrid deterministic-ML-AI architecture**.

---

## 🌟 Architectural Philosophy

ASTRA operates across three complementary intelligence layers:
1. **Deterministic Layer (Core Engine):** AST analysis, rule engines, OpenAPI parsing, Boundary Value Analysis (BVA), Equivalence Partitioning (EP), and deterministic pytest/HTTPX test execution.
2. **Machine Learning Layer (Statistical Intelligence):** XGBoost test prioritization, historical failure frequency analysis, DBSCAN failure clustering, and flaky test detection.
3. **Generative AI Layer (Optional NLP Intelligence):** Natural language requirement extraction (SRS), zero-shot/few-shot edge case scenario synthesis, LLM root-cause explanation, and automated Markdown bug reports.

> **Zero-LLM Resilience:** ASTRA does not depend on an LLM to function. If external AI API services are unreachable or rate-limited, ASTRA seamlessly falls back to its deterministic rule engine.

---

## 🚀 Phase 1 Implementation Status

Phase 1 establishes the production-grade foundation of ASTRA:
- ✅ **Monorepo Directory Layout:** Standardized structure for `backend/`, `frontend/`, `engine/`, `ai/`, `ml/`, `workers/`, `benchmark_apps/`, and `docker/`.
- ✅ **FastAPI Async Backend:** Versioned REST API (`/api/v1`) running Python 3.11+, Uvicorn, Pydantic v2, and Async SQLAlchemy 2.0 (`asyncpg`).
- ✅ **PostgreSQL 16 Relational Storage:** ORM declarative models for `User` (RBAC), `Project`, and `AuditLog` with Alembic migration versioning (`alembic upgrade head`).
- ✅ **JWT Authentication & RBAC:** Access token security supporting 4 roles: `ADMIN`, `DEVELOPER`, `TESTER`, and `VIEWER`.
- ✅ **Async Background Worker Queue:** Redis 7 broker & Celery 5.3 worker pool for asynchronous background task execution.
- ✅ **React 18 + Vite + Tailwind CSS Dashboard:** Dark-theme glassmorphism web UI with Zustand state management, Axios interceptors, Login/Register pages, Dashboard Overview, and Project CRUD views.
- ✅ **Multi-Container Docker Environment:** `docker-compose.yml` orchestrating PostgreSQL, Redis, FastAPI backend, Celery worker, and Vite frontend.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend API** | Python 3.11+, FastAPI 0.110+, Uvicorn, Pydantic v2, HTTPX |
| **Database & ORM** | PostgreSQL 16 Alpine, Async SQLAlchemy 2.0, `asyncpg`, Alembic migrations |
| **Authentication** | JWT tokens (`pyjwt`), `pwdlib[argon2]` password hashing, RBAC middleware guards |
| **Task Queue** | Redis 7 Alpine, Celery 5.3+ |
| **Frontend UI** | React 18, TypeScript, Vite, Tailwind CSS, Lucide-React Icons, Zustand, Axios |
| **Containerization** | Docker, Docker Compose, Dockerfiles |
| **Test Engine** | Pytest 8.0+, pytest-asyncio, aiosqlite |

---

## 💻 Local Development Setup

### 1. Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/) installed on your machine.
- Python 3.11+ (for local test runner execution).
- Node.js 20+ (for local frontend development).

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Start with Docker Compose
To build and launch all 5 microservices in detached mode:
```bash
docker compose up --build -d
```

### Expected Service URLs:
- **Frontend Dashboard:** `http://localhost:3000`
- **FastAPI Backend API:** `http://localhost:8000`
- **Interactive Swagger OpenAPI Docs:** `http://localhost:8000/docs`
- **PostgreSQL Database:** `localhost:5432`
- **Redis Server:** `localhost:6379`

### 4. Apply Database Migrations
To initialize the database schema in PostgreSQL:
```bash
docker compose exec backend alembic upgrade head
```

---

## 🧪 Running Unit & Integration Tests

To run the backend Pytest test suite (17 passed unit/integration tests):
```bash
cd backend
python -m pytest -v
```

---

## 📂 Repository Structure

```text
astra/
├── planning/                             # Implementation Roadmap (Phases 1-10)
│   ├── 00_master_execution_plan.md
│   └── phase_01_core_foundation.md
│
├── backend/                              # FastAPI Core Service
│   ├── app/
│   │   ├── api/v1/                       # Versioned REST Routers (auth, projects, tasks)
│   │   ├── core/                         # Config, Security (JWT/Argon2), Celery, RBAC
│   │   ├── db/                           # Async Session & Alembic Migrations
│   │   ├── models/                       # SQLAlchemy 2.0 ORM Models (User, Project, AuditLog)
│   │   ├── schemas/                      # Pydantic v2 Request/Response Schemas
│   │   ├── services/                     # Business Logic Services
│   │   └── main.py                       # FastAPI Application Entrypoint
│   ├── tests/                            # Pytest Test Suite (Health, Auth, RBAC, Projects, DB)
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                             # React 18 + Vite + Tailwind CSS App
│   ├── src/
│   │   ├── components/                   # Sidebar, Navbar, Layout, Button, Input, Modal, StatusBadge
│   │   ├── pages/                        # Login, DashboardOverview, ProjectsList, ProjectDetail
│   │   ├── services/                     # Axios API Client with Bearer token interceptor
│   │   ├── store/                        # Zustand Auth Store
│   │   ├── App.tsx                       # Protected Routes & Router Configuration
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
│
├── engine/                               # Testing Engine Core (Phase 2-4 Placeholder)
├── ai/                                   # LLM Provider Layer (Phase 5 Placeholder)
├── ml/                                   # Statistical ML Models (Phase 7 Placeholder)
├── workers/                              # Worker Sandboxes (Placeholder)
├── benchmark_apps/                       # Benchmark Microservices (Phase 10 Placeholder)
├── docker/                               # Custom Docker Specs
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

---

## 🔐 Role-Based Access Control (RBAC) Matrix

| Action | Admin | Developer | Tester | Viewer |
| :--- | :---: | :---: | :---: | :---: |
| **Manage Users & System Settings** | ✅ | ❌ | ❌ | ❌ |
| **Create & Edit Projects** | ✅ | ✅ | ✅ | ❌ |
| **Delete Projects** | ✅ | ✅ (Owner) | ✅ (Owner) | ❌ |
| **Dispatch Background Tasks** | ✅ | ✅ | ✅ | ❌ |
| **View Projects & Task Status** | ✅ | ✅ | ✅ | ✅ |

---

## 📜 License
MIT License &copy; 2026 ASTRA Automated Software Testing Team.
