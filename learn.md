# ASTRA: Complete Technical Architecture & System Guide

Welcome to **ASTRA** (*Automated Software Testing, Analysis & Intelligence Platform*). This document provides an exhaustive, end-to-end breakdown of the entire repository structure, detailing every directory, file, API interaction, and engine component.

---

## 🏗️ 1. High-Level Architecture Overview

ASTRA is an enterprise-grade, rule-based and AI-assisted automated software testing platform. It scans source code repositories, parses Abstract Syntax Trees (AST), constructs dependency Knowledge Graphs, infers endpoint parameter schemas, synthesizes combinatorial test cases (EP, BVA, Pairwise, Security Probes), and executes test suites asynchronously.

```
                  ┌─────────────────────────────────────────┐
                  │          React Single-Page App          │
                  │   (Vite + TypeScript + Zustand UI)      │
                  └────────────────────┬────────────────────┘
                                       │ HTTP / REST APIs
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │           FastAPI Web Server            │
                  │      (Authentication, Router, DB)       │
                  └───────────┬─────────────────┬───────────┘
                              │                 │
              SQLAlchemy ORM  │                 │ Async Task Queue
                              ▼                 ▼
                   ┌──────────────────┐  ┌──────────────────┐
                   │ PostgreSQL Database│ │   Redis Broker   │
                   └──────────────────┘  └────────┬─────────┘
                                                  │
                                                  ▼
                                         ┌──────────────────┐
                                         │  Celery Worker   │
                                         │  (AST & Engine)  │
                                         └────────┬─────────┘
                                                  │
                                                  ▼
                                         ┌──────────────────┐
                                         │  Analysis & Test │
                                         │ Generation Engine│
                                         └──────────────────┘
```

---

## 📁 2. Complete Folder & File Directory Map

Below is a catalog explaining the purpose of **every folder** and **every file** in the project.

### 📍 Root Directory (`/`)
- [`.env`](file:///d:/Astra/.env) / [`.env.example`](file:///d:/Astra/.env.example): Environment variables for database credentials, JWT secret keys, Redis connection URLs, and API ports.
- [`.gitignore`](file:///d:/Astra/.gitignore): Specifies file patterns ignored by Git (e.g. `__pycache__`, `.env`, node_modules, temp scratch files).
- [`docker-compose.yml`](file:///d:/Astra/docker-compose.yml): Orchestrates multi-container orchestration for `backend`, `celery_worker`, `frontend`, `postgres`, and `redis`.
- [`Makefile`](file:///d:/Astra/Makefile): Command shortcuts for starting services, running database migrations, linting, and running unit tests.
- [`README.md`](file:///d:/Astra/README.md): High-level overview, quickstart instructions, and architecture diagrams.
- [`history.md`](file:///d:/Astra/history.md): Technical roadmap, implementation log, and Phase 1–4 completion records.
- [`learn.md`](file:///d:/Astra/learn.md): Comprehensive project architecture, API guide, and folder map (this document).

---

### 🖥️ Backend Application (`/backend/`)
The FastAPI web server and database layer.

- [`backend/Dockerfile`](file:///d:/Astra/backend/Dockerfile): Builds the Python 3.11 container environment with `git` and system dependencies.
- [`backend/requirements.txt`](file:///d:/Astra/backend/requirements.txt): Python dependencies (FastAPI, SQLAlchemy, asyncpg, Celery, httpx, PyYAML, Pydantic).
- [`backend/alembic.ini`](file:///d:/Astra/backend/alembic.ini): Database migration configuration for Alembic.

#### 📂 `backend/app/`
- [`backend/app/main.py`](file:///d:/Astra/backend/app/main.py): Entry point for FastAPI app. Configures CORS, mounts API routers, and initializes lifespan events.

##### 📂 `backend/app/api/v1/` (API Routers)
- [`auth.py`](file:///d:/Astra/backend/app/api/v1/auth.py): User registration, authentication (`/login`), and JWT token generation.
- [`projects.py`](file:///d:/Astra/backend/app/api/v1/projects.py): Project CRUD endpoints (create, list, fetch details, update, delete).
- [`analyzer.py`](file:///d:/Astra/backend/app/api/v1/analyzer.py): Triggers repository cloning & static analysis (`/projects/{id}/analyze`), polls progress, and returns Knowledge Graph data.
- [`generator.py`](file:///d:/Astra/backend/app/api/v1/generator.py): Dispatches Phase 4 Advanced Test Suite generation (`/projects/{id}/test-suites/generate-advanced`) and retrieves job status.
- [`execution.py`](file:///d:/Astra/backend/app/api/v1/execution.py): Triggers synthetic test suite execution (`/projects/{id}/test-suites/{id}/execute`) and returns test execution logs.
- [`tasks.py`](file:///d:/Astra/backend/app/api/v1/tasks.py): General task monitoring endpoints for background workers.

##### 📂 `backend/app/core/`
- [`config.py`](file:///d:/Astra/backend/app/core/config.py): Pydantic settings loading configuration parameters from `.env`.
- [`security.py`](file:///d:/Astra/backend/app/core/security.py): Password hashing (Passlib / bcrypt) and JWT encoding/decoding functions.
- [`celery_app.py`](file:///d:/Astra/backend/app/core/celery_app.py): Configures Celery worker instance, Redis broker queues, and task module imports.

##### 📂 `backend/app/db/`
- [`session.py`](file:///d:/Astra/backend/app/db/session.py): Initializes SQLAlchemy AsyncEngine, `AsyncSessionLocal` session factory, and dependency injection `get_db()`.

##### 📂 `backend/app/models/`
- [`domain.py`](file:///d:/Astra/backend/app/models/domain.py): SQLAlchemy database models (`User`, `Project`, `ProjectAnalysis`, `DiscoveredEndpoint`, `EndpointParameter`, `TestSuite`, `TestCase`, `TestExecution`, `GenerationJob`).

##### 📂 `backend/app/schemas/`
- [`project.py`](file:///d:/Astra/backend/app/schemas/project.py): Pydantic validation schemas for project creation and responses.
- [`analyzer.py`](file:///d:/Astra/backend/app/schemas/analyzer.py): Schemas for analysis status, endpoint parameters, and Knowledge Graph representations.
- [`generator.py`](file:///d:/Astra/backend/app/schemas/generator.py): Schemas for strategy configuration, preset options, and generation job status.
- [`execution.py`](file:///d:/Astra/backend/app/schemas/execution.py): Schemas for test run requests, case results, and execution reports.

##### 📂 `backend/app/tasks/` (Celery Tasks)
- [`analyzer_tasks.py`](file:///d:/Astra/backend/app/tasks/analyzer_tasks.py): Background worker task (`run_project_analysis_task`) for cloning, scanning, AST parsing, and graph construction.
- [`generation_tasks.py`](file:///d:/Astra/backend/app/tasks/generation_tasks.py): Background worker task (`run_advanced_suite_generation_task`) executing Phase 4 test generation pipeline.
- [`execution_tasks.py`](file:///d:/Astra/backend/app/tasks/execution_tasks.py): Background worker task (`run_test_suite_execution_task`) executing generated test suites against target APIs.

---

### 🧠 Core Analysis & Generation Engine (`/engine/`)
The standalone, framework-agnostic intelligence engine.

#### 📂 `engine/analyzer/` (Phase 2 Static Analysis)
- [`repo_cloner.py`](file:///d:/Astra/engine/analyzer/repo_cloner.py): Handles local directory resolution or Git repository cloning with authentication.
- [`file_scanner.py`](file:///d:/Astra/engine/analyzer/file_scanner.py): Scans project directory, ignores binary/build assets, and collects source files.
- [`language_detector.py`](file:///d:/Astra/engine/analyzer/language_detector.py): Detects primary language (Python, JavaScript, TypeScript, Go, Java) based on file extensions.
- [`framework_detector.py`](file:///d:/Astra/engine/analyzer/framework_detector.py): Identifies frameworks (FastAPI, Flask, Django, Express, NestJS) by scanning imports and config files.
- [`endpoint_extractor.py`](file:///d:/Astra/engine/analyzer/endpoint_extractor.py): Extracts HTTP endpoints, routes, methods, and parameters from parsed AST nodes.
- [`knowledge_graph.py`](file:///d:/Astra/engine/analyzer/knowledge_graph.py): Constructs `ProjectKnowledgeGraph` tracking code nodes (functions, classes, endpoints) and caller/callee edge relationships.

##### 📂 `engine/analyzer/parsers/`
- [`python_parser.py`](file:///d:/Astra/engine/analyzer/parsers/python_parser.py): Python AST parser extracting function signatures, arguments, docstrings, and HTTP decorator routes.

#### 📂 `engine/schema/` (Constraint & Type Inference)
- [`models.py`](file:///d:/Astra/engine/schema/models.py): Normalized schema IR (`NormalizedFieldSchema`, `FieldConstraint`, `ConstraintSource`, `InferredType`).
- [`type_inferencer.py`](file:///d:/Astra/engine/schema/type_inferencer.py): Infers data types, nullability, min/max bounds, regex patterns, and confidence scores from AST and docstrings.

#### 📂 `engine/generator/` (Phase 4 Advanced Synthetic Generator)
- [`strategy.py`](file:///d:/Astra/engine/generator/strategy.py): Defines `TestGenerationStrategy` configuration and presets (`MINIMAL`, `STANDARD`, `THOROUGH`, `SECURITY`, `MAXIMUM`).
- [`models.py`](file:///d:/Astra/engine/generator/models.py): `TestScenario` IR representing test intent, field mutations, and expected behavior.
- [`combinatorial.py`](file:///d:/Astra/engine/generator/combinatorial.py): N-wise combinatorial engine producing valid pairwise combinations.
- [`deduplicator.py`](file:///d:/Astra/engine/generator/deduplicator.py): Hashes test payload signatures to eliminate redundant test scenarios.
- [`prioritizer.py`](file:///d:/Astra/engine/generator/prioritizer.py): Deterministically sorts test cases based on criticality (Happy Path > Boundary > Missing Required > Invalid Types > Security Probes).
- [`advanced_suite_generator.py`](file:///d:/Astra/engine/generator/advanced_suite_generator.py): Orchestrates constraint inference, scenario generation, mutation, deduplication, and test spec output.

##### 📂 `engine/generator/data_generators/`
- [`boundary_generator.py`](file:///d:/Astra/engine/generator/data_generators/boundary_generator.py): Generates equivalence partition and boundary value mutation inputs (min-1, min, max, max+1, empty, string length limits).
- [`invalid_type_generator.py`](file:///d:/Astra/engine/generator/data_generators/invalid_type_generator.py): Generates type violation inputs (e.g. passing strings for integer fields, null for non-nullable).
- [`security_generator.py`](file:///d:/Astra/engine/generator/data_generators/security_generator.py): Generates opt-in security probe inputs (SQL injection, XSS payloads, path traversal).

#### 📂 `engine/compiler/` (Test Specification Compiler)
- [`test_compiler.py`](file:///d:/Astra/engine/compiler/test_compiler.py): Converts high-level `TestSpecification` objects into executable `TestCase` database records.

#### 📂 `engine/executor/` (Phase 3 Execution Engine)
- [`httpx_runner.py`](file:///d:/Astra/engine/executor/httpx_runner.py): Asynchronous HTTP test runner making actual network calls to target API endpoints and validating response status codes.
- [`health_checker.py`](file:///d:/Astra/engine/executor/health_checker.py): Verifies endpoint availability prior to executing test runs.

---

### 🎨 Frontend Application (`/frontend/`)
The modern React single-page dashboard built with Vite, TypeScript, and Tailwind CSS.

- [`frontend/vite.config.ts`](file:///d:/Astra/frontend/vite.config.ts): Vite build configuration with API reverse proxy `/api/v1` pointing to `localhost:8000`.
- [`frontend/package.json`](file:///d:/Astra/frontend/package.json): NPM dependencies (React, React Router, Zustand, Lucide React, Tailwind CSS).

#### 📂 `frontend/src/`
- [`App.tsx`](file:///d:/Astra/frontend/src/App.tsx): Main application router and layout container.
- [`main.tsx`](file:///d:/Astra/frontend/src/main.tsx): React root mounting entry point.

##### 📂 `engine/analysis/` (Phase 6 Failure & Root-Cause Analysis Engine)
- [`models.py`](file:///d:/Astra/engine/analysis/models.py): Phase 6 domain models (`FailureEvidence`, `ParsedException`, `JsonDiffItem`, `FaultLocation`, `RootCauseCandidate`, `FailureAnalysis`, `DefectCluster`).
- [`redactor.py`](file:///d:/Astra/engine/analysis/redactor.py): `EvidenceRedactor` sanitizing credentials, secrets, tokens, cookies, and enforcing payload size limits.
- [`parsers/`](file:///d:/Astra/engine/analysis/parsers/): Language parsers for Python tracebacks, Node.js/V8 stacks, Java JVM stacks, and SQLSTATE error codes (`sql_parser.py`).
- [`diff/json_diff_isolator.py`](file:///d:/Astra/engine/analysis/diff/json_diff_isolator.py): `JsonDiffIsolator` calculating exact JSONPath-level response deltas (`$.body...`), status mismatches, header diffs, and SLA latency breaches.
- [`rules/classification_rules.py`](file:///d:/Astra/engine/analysis/rules/classification_rules.py): Priority Rule Engine (R001–R030) evaluating expected vs actual status semantically.
- [`classifier.py`](file:///d:/Astra/engine/analysis/classifier.py): `FailureClassifier` determining taxonomic failure categories (`SERVER_CRASH`, `BUSINESS_LOGIC_DEFECT`, `CONTRACT_VIOLATION`, `DATABASE_ERROR`, etc.).
- [`localization.py`](file:///d:/Astra/engine/analysis/localization.py): `FaultLocalizer` ranking source fault locations with individual attribution confidence and commit SHA validation against PKG nodes.
- [`candidate_engine.py`](file:///d:/Astra/engine/analysis/candidate_engine.py): `RootCauseCandidateEngine` generating prioritized candidate hypotheses with false-positive restraint (`UNKNOWN` with `0.0` confidence on ambiguous data).
- [`fingerprint.py`](file:///d:/Astra/engine/analysis/fingerprint.py): `FingerprintEngine` computing canonical JSON SHA256 hashes and clustering `DefectCluster` records.
- [`evaluator.py`](file:///d:/Astra/engine/analysis/evaluator.py): `DiagnosticEvaluator` benchmarking classification accuracy ($\ge 98\%$), attribution accuracy, diff precision, and false-positive restraint.
- [`root_cause_analyzer.py`](file:///d:/Astra/engine/analysis/root_cause_analyzer.py): Master Orchestrator coordinating full failure analysis pipeline.

##### 📂 `frontend/src/pages/`
- [`Login.tsx`](file:///d:/Astra/frontend/src/pages/Login.tsx): Authentication screen for login and admin registration.
- [`DashboardOverview.tsx`](file:///d:/Astra/frontend/src/pages/DashboardOverview.tsx): System metrics, total projects, test execution history, and active jobs.
- [`ProjectsList.tsx`](file:///d:/Astra/frontend/src/pages/ProjectsList.tsx): Displays all scanned repositories, registration modal, and search filtering.
- [`ProjectDetail.tsx`](file:///d:/Astra/frontend/src/pages/ProjectDetail.tsx): Comprehensive project view containing Knowledge Graph, Endpoint Catalog, and Test Suite Generator trigger.
- [`RequirementIntelligence.tsx`](file:///d:/Astra/frontend/src/pages/RequirementIntelligence.tsx): Phase 5 requirement intelligence matrix and AI payload dashboard.
- [`DefectDashboard.tsx`](file:///d:/Astra/frontend/src/pages/DefectDashboard.tsx): Phase 6 Failure Analysis & Defect Dashboard.
- [`TestRunDetail.tsx`](file:///d:/Astra/frontend/src/pages/TestRunDetail.tsx): Detailed test execution results, pass/fail status breakdown, and response payloads.

##### 📂 `frontend/src/components/`
- [`RootCauseInspectorModal.tsx`](file:///d:/Astra/frontend/src/components/RootCauseInspectorModal.tsx): Interactive root-cause diagnostic inspector modal displaying confidence meters, fault locations, candidates, and structural diffs.
- [`JsonDiffViewer.tsx`](file:///d:/Astra/frontend/src/components/JsonDiffViewer.tsx): Side-by-side expected vs actual JSONPath response delta viewer.

##### 📂 `frontend/src/store/`
- [`authStore.ts`](file:///d:/Astra/frontend/src/store/authStore.ts): Zustand state store handling JWT token persistence, login state, and 401 unauthenticated response handling.

##### 📂 `frontend/src/services/`
- [`api.ts`](file:///d:/Astra/frontend/src/services/api.ts): Axios/HTTP client with authorization interceptors for backend REST endpoints.

---

## 🔄 3. End-to-End API Interaction & Data Flow

Here is how data flows through ASTRA during a complete testing cycle:

```
 1. AUTHENTICATION
    [User] ──(POST /api/v1/auth/login)──► [FastAPI] ──(Verify JWT)──► [Zustand Store]

 2. PROJECT CREATION
    [User] ──(POST /api/v1/projects/)──► [FastAPI] ──(Save in DB)──► [PostgreSQL]

 3. STATIC CODE ANALYSIS (PHASE 2)
    [User] ──(POST /projects/{id}/analyze)──► [FastAPI] ──(Dispatch Task)──► [Redis]
                                                                                │
                                                                                ▼
                                                                        [Celery Worker]
                                                                                │
    [PostgreSQL] ◄──(Save Knowledge Graph & Endpoints)─── [Python AST Parser] ◄─┤

 4. ADVANCED TEST GENERATION (PHASE 4)
    [User] ──(POST /projects/{id}/test-suites/generate-advanced)──► [FastAPI]
                                                                          │
    [PostgreSQL] ◄──(Save Test Cases & Specs)─── [Generator Engine] ◄────┴─► [Celery]
                                                     │ (EP, BVA, Pairwise)

 5. TEST SUITE EXECUTION (PHASE 3)
    [User] ──(POST /test-suites/{id}/execute)──► [Celery Worker] ──► [Target API]
                                                      │
                                                      ▼
                                       [Save Results to PostgreSQL]
```

---

## 🚀 4. How to Run and Test ASTRA Locally

### Option A: Running with Docker Compose (Recommended)
Launch all 5 microservices (`backend`, `celery_worker`, `frontend`, `postgres`, `redis`) with a single command:

```bash
docker compose up --build -d
```

- **Frontend Dashboard**: `http://localhost:3000` (or `http://localhost:5173`)
- **Backend API Docs (Swagger UI)**: `http://localhost:8000/docs`
- **PostgreSQL Database**: `localhost:5432` (User: `postgres`, Pass: `postgres`, DB: `astra_db`)
- **Redis Broker**: `localhost:6379`

### Default Login Credentials
- **Email**: `admin@astra.com`
- **Password**: `AdminPass123!`

---

## 🛡️ Summary of Engineering Highlights
- **Decoupled Architecture**: Clear boundary separation between DB API models, normalized schema intermediate representations (IR), generator scenarios, and executable test cases.
- **Async Execution**: Non-blocking Celery background workers prevent thread locking during heavy AST scanning and test execution.
- **Deterministic & Reproducible**: All random mutations use configurable integer seed values (`seed=42`) and configuration hashing to guarantee 100% reproducible test suites.
