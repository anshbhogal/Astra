# ASTRA — Intelligent Automated Software Testing & Defect Remediation Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.x-61dafb.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178c6.svg)](https://www.typescriptlang.org/)
[![Monaco Editor](https://img.shields.io/badge/Monaco_Editor-VS_Code_Core-007acc.svg)](https://microsoft.github.io/monaco-editor/)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-Multi--Container-2496ed.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **ASTRA** is an enterprise-grade automated software quality, static analysis, and defect remediation platform built upon a **hybrid deterministic-ML-AI architecture**. It features strict **Role-Based Access Governance (RBAC)**, scoped repository isolation, QA-Developer defect triage collaboration, and an embedded **VS Code-grade Developer IDE (Code Studio)**.

---

## 📑 Table of Contents
- [Architectural Philosophy](#-architectural-philosophy)
- [System Architecture](#-system-architecture)
- [Core Platform Capabilities](#-core-platform-capabilities)
  - [1. Admin Governance & Repository Team Scoping](#1--admin-governance--repository-team-scoping)
  - [2. Code Studio — Embedded VS Code-Grade IDE](#2--code-studio--embedded-vs-code-grade-ide)
  - [3. QA Testing & Synthetic Suite Generation](#3--qa-testing--synthetic-suite-generation)
  - [4. Defect Collaboration & Triage Lifecycle](#4--defect-collaboration--triage-lifecycle)
  - [5. Interactive Code Knowledge Graph](#5--interactive-code-knowledge-graph)
- [Role-Based Access Control (RBAC) Matrix](#-role-based-access-control-rbac-matrix)
- [End-to-End Collaboration Workflow](#-end-to-end-collaboration-workflow)
- [Technology Stack](#️-technology-stack)
- [Quick Start & Deployment](#-quick-start--deployment)
  - [Prerequisites](#1-prerequisites)
  - [Environment Setup](#2-environment-setup)
  - [Launch with Docker Compose](#3-launch-services-with-docker-compose)
  - [Database Initialization & Default Credentials](#4-database-initialization--default-credentials)
- [API Reference](#-api-reference)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Directory Structure](#-repository-directory-structure)
- [License](#-license)

---

## 🌟 Architectural Philosophy

ASTRA operates across three complementary intelligence layers with **Zero-LLM Resilience**:

1. **Deterministic Layer (Core Engine):** Abstract Syntax Tree (AST) analysis, call graph generation, OpenAPI/REST route extraction, Boundary Value Analysis (BVA), Equivalence Partitioning (EP), and deterministic pytest/HTTPX test execution.
2. **Machine Learning Layer (Statistical Intelligence):** XGBoost test prioritization, failure frequency analytics, DBSCAN failure clustering, and flaky test detection.
3. **Generative AI Layer (NLP Intelligence):** Natural language requirement extraction (SRS/User Stories), zero-shot/few-shot edge case synthesis, LLM root-cause attribution, and automated defect reports.

> **Zero-LLM Resilience:** ASTRA has zero hard dependencies on external cloud AI providers. If external LLM APIs are unreachable, disabled, or rate-limited, ASTRA seamlessly falls back to its deterministic rule engine and static AST analysis without service interruption.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Presentation Layer (Vite + React 18)"]
        UI_Admin["Admin Governance Console"]
        UI_Studio["Code Studio (Monaco Editor / VS Code Web)"]
        UI_Tester["Test Execution & Defect Triage Center"]
        UI_Viewer["Audit Reports & Knowledge Graph"]
    end

    subgraph Gateway ["API Gateway & Core REST Engine (FastAPI)"]
        AUTH["Auth & JWT Gatekeeper<br/>(Password Complexity & 1st-Login Policy)"]
        RBAC["RBAC & Repo Scoping Engine"]
        API_ADMIN["/api/v1/admin (Approvals & Provisioning)"]
        API_CODE["/api/v1/projects/{id}/code (File I/O & IDE Runner)"]
        API_TEST["/api/v1/unit-tests & test-suites"]
        API_DEFECT["/api/v1/defects (Comments & State Lifecycle)"]
    end

    subgraph ExecutionLayer ["Distributed Processing & Engine Sandbox"]
        CELERY["Celery Task Workers"]
        REDIS[("Redis 7<br/>Broker & Cache")]
        AST_ENGINE["Deterministic AST Parser & Call Graph Builder"]
        TEST_RUNNER["Pytest Sandbox Runtime"]
    end

    subgraph DataLayer ["Persistence Layer"]
        PG[("PostgreSQL 16<br/>Projects, Users, Memberships, Defects")]
    end

    UI_Admin -->|JWT Bearer| AUTH
    UI_Studio -->|JWT Bearer| AUTH
    UI_Tester -->|JWT Bearer| AUTH
    UI_Viewer -->|JWT Bearer| AUTH

    AUTH --> RBAC
    RBAC --> API_ADMIN
    RBAC --> API_CODE
    RBAC --> API_TEST
    RBAC --> API_DEFECT

    API_ADMIN --> PG
    API_DEFECT --> PG
    API_CODE --> TEST_RUNNER
    API_TEST --> CELERY
    CELERY --> REDIS
    CELERY --> AST_ENGINE
    AST_ENGINE --> PG
```

---

## 🚀 Core Platform Capabilities

### 1. 🛡️ Admin Governance & Repository Team Scoping
- **Exclusive Repository Provisioning:** Only System Administrators can register and configure repositories (`POST /api/v1/projects`).
- **User Provisioning & Approval Gate:**
  - Administrators can directly provision **Tester**, **Developer**, and **Viewer** user IDs.
  - Self-registered users cannot access any platform features until an Administrator reviews and approves their account from the **Admin Governance Cockpit**.
  - Public registration for the `ADMIN` role is strictly forbidden at both schema and service layers.
- **Strict Repository Visibility Isolation:**
  - Non-admin engineers only see and access repositories assigned to them by the Admin.
  - For each repository, the Admin provisions a collaboration group of assigned **Developer(s)**, **Tester(s)**, and **Viewer(s)**.
  - The Admin maintains global visibility and orchestration across all repositories.
- **First-Time Login Security Policy:**
  - Provisioned users are flagged with `must_change_password: true`.
  - Upon first login, a non-dismissible modal forces the user to choose a secure password meeting strict enterprise complexity criteria (minimum 8 characters, mix of uppercase, lowercase, number, and special character).

### 2. 💻 Code Studio — Embedded VS Code-Grade IDE
- **Powered by Monaco Editor:** The exact open-source code editor powering Visual Studio Code.
- **Multi-Tab File Management:** Syntax highlighting for Python, TypeScript, JavaScript, JSON, YAML, Markdown, and CSS; dirty-file indicators, minimap, line numbers, code folding, and multi-cursor support.
- **Hierarchical File Tree:** Dynamic repository file explorer with directory traversal, file creation, file deletion, and instant file loading.
- **Tester Defect Navigator:** Integrated sidebar displaying active bugs logged by QA Testers. Clicking any defect instantly navigates the editor to the exact failing file and line (`failing_file:failing_line`).
- **Integrated Test Runner:** Developers can execute unit test runs against modified code directly from the IDE to verify bug fixes before committing.
- **High-Contrast Full-Screen View:** Dedicated full-screen toggle (`F11` / `Esc`) with high-contrast accessibility controls for distraction-free coding.

### 3. 🧪 QA Testing & Synthetic Suite Generation
- **Static AST Extraction:** Automated discovery of callable endpoints, function contracts, input types, and schemas across FastAPI, Flask, Django, etc.
- **Boundary & Type Fuzzing:** Automatic edge-case input payload generation (boundary integers, malformed strings, null bytes, unicode payloads).
- **Synthetic Test Suites:** Configurable test suite generation based on extracted contracts and natural language specifications.
- **Local Sandbox Execution:** Automated execution environment with real-time progress tracking, assertion validation, and detailed execution logs.

### 4. 🔍 Defect Collaboration & Triage Lifecycle
- **Automated Failure Attribution:** Classifies errors (AssertionError, HTTP 500, TypeMismatch, Timeout) and identifies candidate fault locations.
- **Tester ↔ Developer Triage Thread:** Testers log defects; Developers review traces, post remediation notes, and transition defect lifecycle states:
  $$\text{OPEN} \longrightarrow \text{UNDER\_INVESTIGATION} \longrightarrow \text{IN\_REPAIR} \longrightarrow \text{FIXED} \longrightarrow \text{CLOSED}$$
- **Executive Audit Export:** One-click generation of comprehensive PDF and JSON quality audit reports with unit test breakdowns.

### 5. 🕸️ Interactive Code Knowledge Graph
- **Dynamic Visual Architecture:** Visualizes modules, functions, classes, and inter-dependencies using an interactive force-directed graph.
- **Fullscreen Exploration Mode:** Expands the knowledge graph across the full screen with collapsible side panels for in-depth architectural inspections.

---

## 🔐 Role-Based Access Control (RBAC) Matrix

| Platform Capability | Administrator | Developer | QA Tester | Viewer |
| :--- | :---: | :---: | :---: | :---: |
| **Admin Console & User Approvals** | ✅ | ❌ | ❌ | ❌ |
| **Add / Register Repositories** | ✅ | ❌ | ❌ | ❌ |
| **Assign Teams & Groups to Repos** | ✅ | ❌ | ❌ | ❌ |
| **Repository Visibility** | **Global (All)** | **Assigned Only** | **Assigned Only** | **Assigned Only** |
| **Code Studio (VS Code) & File Edits** | ✅ | ✅ (Assigned) | ❌ | ❌ |
| **Run Automated & Synthetic Tests** | ✅ | ❌ | ✅ (Assigned) | ❌ |
| **Defect Triage & Collaboration** | ✅ | ✅ (Fix / Patch) | ✅ (Log / Verify) | ❌ (Read-Only) |
| **Quality Reports & Analytics** | ✅ | ✅ (Assigned) | ✅ (Assigned) | ✅ (Read-Only) |

---

## 🔄 End-to-End Collaboration Workflow

```text
[1. Administrator]
 ├── Registers new repository (e.g., "Payment Gateway")
 ├── Provisions or approves Developer & Tester accounts
 └── Assigns Developer and Tester to "Payment Gateway"
         │
         ▼
[2. QA Tester]
 ├── Logs into Astra and accesses assigned "Payment Gateway" repo
 ├── Runs automated static AST analysis & synthetic test suite
 ├── Discovers failing test case (e.g., NullPointerException at api/routes.py:84)
 └── Logs Defect with stack trace and assigns severity
         │
         ▼
[3. Developer]
 ├── Opens "Payment Gateway" in Code Studio (VS Code Web IDE)
 ├── Clicks the logged defect to automatically jump to api/routes.py:84
 ├── Edits the code and adds necessary guards
 ├── Hits "Run Tests" in the IDE bottom drawer to verify the fix passes
 └── Comments on the defect thread and marks status as "FIXED"
         │
         ▼
[4. QA Tester & Viewer]
 ├── Tester re-runs test suite, confirms resolution, and marks "CLOSED"
 └── Viewer reviews final executive audit reports and health dashboards
```

---

## 🛠️ Technology Stack

| Component | Technologies |
| :--- | :--- |
| **Backend API** | Python 3.11+, FastAPI 0.110+, Uvicorn, Pydantic v2, HTTPX |
| **Database & ORM** | PostgreSQL 16 Alpine, Async SQLAlchemy 2.0 (`asyncpg`), Alembic migrations |
| **Authentication** | JWT tokens (`pyjwt`), Argon2 / PBKDF2 password hashing, RBAC middleware |
| **Task Queue & Broker** | Redis 7 Alpine, Celery 5.3+ async worker pool |
| **Frontend UI** | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Zustand, Axios |
| **Code Editor** | Monaco Editor (`@monaco-editor/react`), VS Code Theme Engine |
| **Testing Engine** | Pytest 8.0+, pytest-asyncio, HTTPX ASGI Transport |
| **Containerization** | Docker, Docker Compose, Multi-stage builds |

---

## 💻 Quick Start & Deployment

### 1. Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/) installed.
- Python 3.11+ (optional, for local testing outside Docker).
- Node.js 20+ (optional, for local frontend development outside Docker).

### 2. Environment Setup
Copy the environment template:
```bash
cp .env.example .env
```

Key environment configurations in `.env`:
```ini
POSTGRES_USER=astra_user
POSTGRES_PASSWORD=astra_secret_password
POSTGRES_DB=astra_db
DATABASE_URL=postgresql+asyncpg://astra_user:astra_secret_password@postgres:5432/astra_db
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
JWT_SECRET=super_secure_astra_jwt_secret_key_change_in_production_2026
```

### 3. Launch Services with Docker Compose
Start all microservices in detached mode:
```bash
docker compose up --build -d
```

#### Service Endpoints:
- **Frontend Dashboard & Code Studio:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend REST API:** [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL Database:** `localhost:5432`
- **Redis Broker:** `localhost:6379`

### 4. Database Initialization & Default Credentials
Apply database migrations and seed default platform accounts:
```bash
# Run database migrations
docker compose exec backend alembic upgrade head

# Seed initial admin and demo user accounts
docker compose exec backend python -m app.db.seed
```

#### 🔑 Pre-Configured Test Accounts:
| Account | Email | Password | Role | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | `admin@astra.local` | `Password123!` | `ADMIN` | Global governance, user provisioning & approvals |
| **Lead Developer** | `dev@astra.local` | `Password123!` | `DEVELOPER` | Code Studio, bug remediation, test verification |
| **QA Specialist** | `tester@astra.local` | `Password123!` | `TESTER` | Test suite execution, defect logging |
| **Guest Observer** | `viewer@astra.local` | `Password123!` | `VIEWER` | Read-only metrics & audit inspection |

> **Note on First Login:** New accounts provisioned by the Administrator will be prompted to reset their password upon initial login to satisfy the password security policy.

---

## 📡 API Reference

A brief overview of the primary REST endpoints available on the FastAPI backend:

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register new account (Self-registration) | Public |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT access token | Public |
| `POST` | `/api/v1/auth/change-password`| Update user password (enforces complexity) | Authenticated |
| `GET` | `/api/v1/admin/users` | List all users across the platform | `ADMIN` |
| `GET` | `/api/v1/admin/users/pending`| Retrieve self-registered accounts awaiting approval | `ADMIN` |
| `POST` | `/api/v1/admin/users` | Directly provision a new user ID | `ADMIN` |
| `POST` | `/api/v1/admin/users/{id}/approve` | Approve a self-registered user and assign role | `ADMIN` |
| `POST` | `/api/v1/projects` | Register a new code repository | `ADMIN` |
| `GET` | `/api/v1/projects` | List projects (scoped to assigned memberships) | Authenticated |
| `GET` | `/api/v1/projects/{id}/code/tree` | Fetch repository directory file hierarchy | `ADMIN`, `DEVELOPER` |
| `GET` | `/api/v1/projects/{id}/code/file` | Read file contents into Code Studio editor | `ADMIN`, `DEVELOPER` |
| `PUT` | `/api/v1/projects/{id}/code/file` | Save modified code from Code Studio | `ADMIN`, `DEVELOPER` |
| `POST` | `/api/v1/projects/{id}/code/run-tests`| Execute unit tests against current code | `ADMIN`, `DEVELOPER` |
| `POST` | `/api/v1/unit-tests/run` | Execute automated test suite against repo | `ADMIN`, `TESTER` |
| `POST` | `/api/v1/defects/{id}/comments` | Post collaboration comment on defect thread | `ADMIN`, `DEVELOPER`, `TESTER` |
| `PUT` | `/api/v1/defects/{id}/status` | Update defect lifecycle state | `ADMIN`, `DEVELOPER`, `TESTER` |

Full interactive schemas and live testing are accessible at **`http://localhost:8000/docs`**.

---

## 🧪 Testing & Quality Assurance

### Run Complete Backend Integration Test Suite:
```bash
# Run RBAC governance, password policy, and admin approval tests
docker exec -e PYTHONPATH=/app astra_backend pytest tests/test_rbac_admin_flow.py -v

# Run Code Studio (Monaco IDE) backend integration tests
docker exec -e PYTHONPATH=/app astra_backend pytest tests/test_code_editor.py -v

# Run all backend unit & integration tests
docker exec -e PYTHONPATH=/app astra_backend pytest tests/ -v
```

### Verify Frontend Production Build:
```bash
docker exec astra_frontend npm run build
```

---

## 📂 Repository Directory Structure

```text
astra/
├── backend/                              # FastAPI Async REST Service
│   ├── app/
│   │   ├── api/v1/                       # Routers (auth, admin, projects, code_editor, analyzer, etc.)
│   │   ├── core/                         # Security (JWT/Argon2), RBAC middleware, Settings
│   │   ├── db/                           # Async Session, Alembic Migrations, Seeds
│   │   ├── models/                       # SQLAlchemy 2.0 ORM Models (User, Project, Defect, Member)
│   │   ├── schemas/                      # Pydantic v2 Request/Response Models
│   │   ├── services/                     # Business Services (Auth, Projects, Analyzer, Code)
│   │   └── main.py                       # Application Entrypoint & Middleware Configuration
│   ├── tests/                            # Pytest Integration & Unit Test Suites
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                             # React 18 + Vite + Tailwind CSS Client
│   ├── src/
│   │   ├── components/                   # FirstTimePasswordModal, KnowledgeGraph, Common UI
│   │   ├── pages/                        # AdminDashboard, CodeStudio, ProjectDetail, ProjectsList
│   │   ├── services/                     # Axios API Client with JWT Interceptors
│   │   ├── store/                        # Zustand Auth & State Stores
│   │   ├── App.tsx                       # Protected Route Guards & Layout Wiring
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
│
├── engine/                               # Autonomous Testing Engine
│   ├── analyzer/                         # AST Extraction, Function Contracts, Repo Cloner
│   └── execution/                        # Unit Test Executor, Sandbox Runtime
│
├── ai/                                   # LLM & Natural Language Intelligence Layer
├── ml/                                   # Statistical ML Models & Defect Classification
├── docker-compose.yml                    # Multi-container Microservice Orchestration
├── .env.example                          # Environment Template
├── Makefile                              # Dev shortcuts (make up, make test-backend, etc.)
└── README.md
```

---

## 📜 License
Released under the [MIT License](LICENSE). &copy; 2026 ASTRA Automated Software Quality Platform.
