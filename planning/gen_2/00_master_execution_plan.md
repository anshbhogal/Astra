# ASTRA Gen 2 — Master Execution Plan & Implementation Status

> **ASTRA Gen 2 — Enterprise Quality Engineering, Polyglot Intelligence & Autonomous Self-Healing Platform**  
> **Status**: In Active Execution (Phase 1 Canonical Platform Core Completed & Verified ✅)  
> **Last Updated**: 2026-10-11  

---

## 1. Executive Summary & Progress Dashboard

ASTRA Gen 2 elevates the platform from an API-testing intelligence engine into an **all-in-one autonomous quality engineering platform** covering manual test authoring, automated execution across heterogeneous runners (HTTP, Playwright, k6), requirement traceability, defect lifecycle, and multi-language microservice meshes.

### Overall Status Tracker

```
[=====================>-----------------------------] 42% Total Gen 2 Completion

✅ DONE:
  - Canonical Domain Architecture & Data Model Freeze v2.3.0
  - 34-Dimension Enterprise Testing Benchmark Gap Analysis
  - Full Backend Security Audit (22 vulnerabilities categorized in security_vulnerabilities.md)
  - Alembic Migration 0011: Gen 2 Canonical Schema DDL (21 tables created in PostgreSQL 15)
  - Alembic Migration 0012: Legacy Compatibility Layer (legacy_execution_map & SQL views)
  - Canonical SQLAlchemy ORM Domain Models (app/models/canonical.py)
  - Idempotent Migration Backfill Runner (app/db/backfill_gen2.py: Phases A through G)
  - Mathematical & Cryptographic Invariant Verification (I-1 through I-5: 100% PASS)
  - Alembic Migration 0013: Canonical Constraints (projects.workspace_id & current_version_id NOT NULL)
  - Zero-Regression Test Suite (129/129 tests passing across engine and backend)

🔄 IN PROGRESS (Phase 1 Next Milestones):
  - Milestone 1.2: Gen 2 Canonical REST API Routers & Domain Services
  - Milestone 1.3: Polyglot AST Parsers (Go Gin/Fiber, Node Express/NestJS, Spring Boot)
  - Milestone 1.4: Universal Execution Adapters (sandbox_http, playwright, k6, manual)
  - Milestone 1.5: Frontend UI Expansion (Workspaces, Requirements, Test Library, Defects)

⏳ NOT STARTED (Future Phased Roadmap):
  - Phase 2 (Phase 12): Automated Program Repair (APR) & Autonomous GitHub PRs
  - Phase 3 (Phase 13): OpenTelemetry Distributed Tracing & Dynamic Cross-Service PKG
  - Phase 4 (Phase 14): Production Shadow Traffic Replay & Semantic Diff
  - Phase 5 (Phase 15): Adversarial Red-Team Multi-Agent Security Fuzzing
  - Security Workstream: Remediation of 22 Audited Vulnerabilities
```

---

## 2. Detailed "What's Done" vs "What's Not Done" Matrix

### 2.1 Phase 1: Canonical Platform Core & Polyglot Engine

| Component / Deliverable | Status | Verification & Notes |
|---|:---:|---|
| **Contract Freeze v2.3.0** | **DONE ✅** | Frozen in [`01_canonical_quality_platform.md`](file:///d:/Astra/planning/gen_2/01_canonical_quality_platform.md); covers 21 canonical tables, adapter protocols, RBAC matrix. |
| **34-Dimension Gap Analysis** | **DONE ✅** | Complete audit in [`03_benchmark_gap_analysis.md`](file:///d:/Astra/planning/gen_2/03_benchmark_gap_analysis.md) comparing ASTRA against TestRail, Jira, Postman, Playwright, k6. |
| **Security Audit** | **DONE ✅** | Full codebase audit in [`security_vulnerabilities.md`](file:///d:/Astra/security_vulnerabilities.md) (7 Crit, 6 High, 5 Med, 4 Low). Deferred for security sprint. |
| **Migration 0011 (Canonical DDL)** | **DONE ✅** | 21 tables created in PostgreSQL 15 (`workspaces` + 20 `g2_*` tables). Pure DDL. |
| **Migration 0012 (Compatibility)** | **DONE ✅** | Created `legacy_execution_map` and `v_canonical_legacy_runs` view. |
| **SQLAlchemy ORM Models** | **DONE ✅** | Implemented in [`canonical.py`](file:///d:/Astra/backend/app/models/canonical.py) with dual-dialect SQLite/PostgreSQL support. |
| **Data Backfill Runner** | **DONE ✅** | [`backfill_gen2.py`](file:///d:/Astra/backend/app/db/backfill_gen2.py) migrated 4 projects, 1 suite, 30 test cases to canonical definitions with `http.v1` specs. |
| **Verification Invariants** | **DONE ✅** | [`verify_migration_invariants.py`](file:///d:/Astra/backend/app/db/verify_migration_invariants.py) validated I-1, I-2, I-3, I-4, and I-5 (SHA-256 digest match). |
| **Migration 0013 (Constraints)** | **DONE ✅** | Enforced `NOT NULL` on `projects.workspace_id` and `g2_test_definitions.current_version_id`. |
| **Test Suite Zero Regression** | **DONE ✅** | 129/129 tests passing (91 engine tests + 38 backend tests). |
| **Gen 2 REST APIs & Services** | **IN PROGRESS 🔄** | FastAPI routers for `/workspaces`, `/requirements`, `/test-definitions`, `/test-plans`, `/test-cycles`, `/defects`. |
| **Go AST Parser (Gin/Fiber)** | **NOT DONE ⏳** | Target: Route groups, struct tags (`json:"..." binding:"required"`), path params (`:id`). |
| **TypeScript AST Parser (Express/Nest)** | **NOT DONE ⏳** | Target: Upgrade `typescript.py` & `javascript.py` to parse Express routes & NestJS decorators. |
| **Java AST Parser (Spring Boot)** | **NOT DONE ⏳** | Target: `@RestController`, `@GetMapping`, `@PathVariable`, `@Valid @RequestBody DTO`. |
| **Polyglot PKG Call Graph** | **NOT DONE ⏳** | Target: Cross-language nodes connecting routes $\rightarrow$ handlers $\rightarrow$ models $\rightarrow$ DB. |
| **Execution Adapters** | **NOT DONE ⏳** | Target: Stateless adapter workers for `sandbox_http`, `playwright`, `k6`, and manual test sessions. |
| **Frontend Canonical UI** | **NOT DONE ⏳** | Target: Workspaces switcher, Requirements Tree, Test Plan/Cycle board, Defect tracker. |

---

### 2.2 [Phase 2 (Phase 12): Automated Program Repair (APR) & Autonomous PRs](file:///d:/Astra/planning/gen_2/04_phase_02_automated_program_repair.md)

| Component / Deliverable | Status | Key Scope |
|---|:---:|---|
| **Fault Localization to AST Node** | **NOT DONE ⏳** | Map Tarantula/Ochiai SBFL suspiciousness score directly to precise AST statement node. |
| **AST Patch Synthesis Engine** | **NOT DONE ⏳** | Generate candidate AST replacement nodes for boundary bugs, off-by-one, missing null checks, and auth guards. |
| **Zero-Regression Verification Gate** | **NOT DONE ⏳** | Sandbox execution of synthesized patch against Tier 1 selective regression suite; fail if any passing test breaks. |
| **Autonomous GitHub PR Generator** | **NOT DONE ⏳** | Git branch creation, git commit, GitHub Pull Request creation with automated RCA explanation and diff preview. |

---

### 2.3 Phase 3: OpenTelemetry Distributed Tracing & Dynamic Cross-Service PKG

| Component / Deliverable | Status | Key Scope |
|---|:---:|---|
| **OTel Trace Ingestion Receiver** | **NOT DONE ⏳** | OTLP HTTP/gRPC receiver endpoint collecting spans and traces from Jaeger/Zipkin/OTel collectors. |
| **Dynamic Service Dependency Graph** | **NOT DONE ⏳** | Synthesize cross-microservice call edges (HTTP client $\rightarrow$ downstream route) from runtime traces. |
| **Distributed Impact Propagation** | **NOT DONE ⏳** | When Service A changes, evaluate reachability to Service B and automatically select downstream contract tests. |

---

### 2.4 Phase 4: Production Shadow Traffic Replay & Semantic Diff

| Component / Deliverable | Status | Key Scope |
|---|:---:|---|
| **Gateway Log / Mirror Ingestion** | **NOT DONE ⏳** | Ingestion of sanitized HTTP access logs or mirrored network traffic from Envoy/Nginx/Kong. |
| **PII & Credential Redaction Guard** | **NOT DONE ⏳** | Mandatory real-time scrubbing of authorization tokens, cookies, passwords, and PII before persistence. |
| **Staging Environment Replay Runner** | **NOT DONE ⏳** | Time-controlled replay of captured traffic against staging release candidates with mock time-travel. |
| **Semantic JSON Deep Diff Engine** | **NOT DONE ⏳** | Compare production baseline responses against staging replay responses; flag semantic contract regressions. |

---

### 2.5 Phase 5: Adversarial Red-Team Multi-Agent Security Fuzzing

| Component / Deliverable | Status | Key Scope |
|---|:---:|---|
| **OWASP API Top 10 Attack Engine** | **NOT DONE ⏳** | Autonomous red-team agents targeting BOLA/IDOR, Broken Authentication, Mass Assignment, and SSRF. |
| **Blue-Team Defense Evaluator** | **NOT DONE ⏳** | Invariant monitor evaluating whether server responses leak unauthorized tenant data or return 500 crashes. |
| **Vulnerability Scoring & Auto-Triage** | **NOT DONE ⏳** | CVSS severity scoring, automated PoC reproduction curl scripts, and defect generation in Gen 2 defect lifecycle. |

---

## 3. Immediate Implementation Order (Next Steps)

```
Step 1: REST API Routers for Gen 2 Canonical Modules (Phase 1.2)
  ├── Workspaces API (/api/v1/workspaces)
  ├── Requirements API (/api/v1/projects/{id}/requirements)
  ├── Test Plans & Cycles API (/api/v1/projects/{id}/test-plans, /test-cycles)
  └── Defect Lifecycle API (/api/v1/projects/{id}/defects)

Step 2: Polyglot AST Engine (Phase 1.3)
  ├── Go AST Parser (Gin/Fiber route group & struct tag extractor)
  ├── TypeScript/Node AST Parser (Express router & NestJS controller extractor)
  └── Java Spring Boot AST Parser (RestController & DTO extractor)

Step 3: Frontend Gen 2 Experience (Phase 1.4)
  ├── Workspace selector & navigation
  ├── Requirements traceability view
  ├── Hierarchical Test Suite & Definition library
  └── Defect triage Kanban board

Step 4: Security Remediation Sprint (from security_vulnerabilities.md)
  ├── CRIT-1: Remove hardcoded auth bypass
  ├── CRIT-2: Enforce strong JWT secret & short expiry
  ├── CRIT-3: Implement AES/Fernet encryption for notification URLs
  ├── CRIT-4: Fix DNS rebinding SSRF protection
  └── CRIT-7: Add tenant IDOR checks to failure analysis endpoints
```
