# ASTRA: Complete System Architecture & Engineering Diagrams

**Project Title**: ASTRA — Autonomous Software Testing, Regression Analysis & Defect Attribution Platform  
**Academic Document**: Final Viva Technical Reference & System Architecture Specification  
**Version**: 1.0 (Phase 1–10 Complete)

---

## 1. System Overview & Technology Stack

ASTRA is an enterprise-grade, autonomous software quality engineering and empirical evaluation platform designed for modern microservice architectures. It integrates deterministic AST static analysis, Program Knowledge Graphs (PKG), synthetic invariant test generation, machine learning failure prediction, change-impact selective regression, CI/CD pipeline automation, and multi-mode benchmark evaluation.

### Core Technology Stack

| Layer | Technologies & Frameworks | Key Responsibilities |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Zustand | Real-time reactive dashboards, quality scorecards, ablation matrix, bug traceability drilldown. |
| **API Backend** | FastAPI, Python 3.11, Pydantic V2, SQLAlchemy 2.0 (Async), Uvicorn | REST APIs, authentication (Argon2 + JWT), transaction management, query aggregation. |
| **Execution Engine** | Celery 5.3, Redis 7, SQLite memory transport, ASGITransport, Docker SDK | Asynchronous task workers, isolated test runners, deterministic AST parsing. |
| **Data & Storage** | PostgreSQL 16 (asyncpg), Alembic, Redis 7 (broker & result backend) | Persistent domain storage, historical telemetry, flakiness tracking, report artifacts. |
| **Intelligence Layer**| NetworkX (PKG graph), XGBoost, Scikit-learn, ReportLab, Weasyprint fallback | Graph reachability, ML test prioritization, PDF/HTML executive report synthesis. |

---

## 2. End-to-End System Architecture

```mermaid
graph TD
    subgraph Client["Developer & CI/CD Clients"]
        DevBrowser["Developer Browser (React 18 SPA)"]
        GitHubAction["GitHub Actions / Webhook Events"]
    end

    subgraph Gateway["API & Ingestion Layer (FastAPI)"]
        APIRouter["FastAPI REST Router (/api/v1)"]
        AuthService["Auth & RBAC Service (Argon2 / JWT)"]
        WebhookHandler["HMAC-SHA256 Webhook Ingestion"]
    end

    subgraph DataPlane["Storage & Message Plane"]
        PostgresDB[(PostgreSQL 16 Multi-Phase Store)]
        RedisCache[(Redis 7 Task Broker & Cache)]
    end

    subgraph Workers["Distributed Asynchronous Workers (Celery)"]
        WorkerPool["Celery Execution Cluster"]
        ASTParser["Phase 2: Tree-Sitter AST & PKG Builder"]
        TestGenerator["Phase 3: Synthetic Invariant Generator"]
        ExecutionSandbox["Phase 4: Isolated Sandbox & SSRF Guard"]
        FailureAnalyzer["Phase 6: Root Cause Classifier & Clusterer"]
        MLPrioritizer["Phase 7: XGBoost Failure Predictor"]
        SelectiveEngine["Phase 8: Change-Impact Selective Regression"]
        CIPipelineWorker["Phase 9: CI Check & PR Notifier"]
        BenchmarkRunner["Phase 10: Multi-Mode Benchmark & Ablation Engine"]
    end

    subgraph Targets["Target Microservice Sandboxes"]
        AuthApp["Auth Service (:8001)"]
        EcomApp["Ecommerce Service (:8002)"]
        StudentApp["Student Service (:8003)"]
        BankingApp["Banking Service (:8004)"]
    end

    DevBrowser -->|HTTP/REST| APIRouter
    GitHubAction -->|Signed Webhook| WebhookHandler
    APIRouter --> AuthService
    APIRouter --> PostgresDB
    APIRouter -->|Enqueue Task| RedisCache
    WebhookHandler -->|Enqueue CI Run| RedisCache

    RedisCache --> WorkerPool
    WorkerPool --> ASTParser
    WorkerPool --> TestGenerator
    WorkerPool --> ExecutionSandbox
    WorkerPool --> FailureAnalyzer
    WorkerPool --> MLPrioritizer
    WorkerPool --> SelectiveEngine
    WorkerPool --> CIPipelineWorker
    WorkerPool --> BenchmarkRunner

    ExecutionSandbox -->|HTTP with SSRF Guard| Targets
    BenchmarkRunner -->|In-Process / HTTP| Targets
    WorkerPool -->|Store Telemetry & Artifacts| PostgresDB
    CIPipelineWorker -->|GitHub Checks API| GitHubAction
```

---

## 3. Entity-Relationship Diagram (ERD)

The relational schema spans all 10 project milestones, enforcing strict cascading deletes, foreign key indices, and temporal auditing.

```mermaid
erDiagram
    USERS ||--o{ PROJECTS : "owns"
    USERS ||--o{ AUDIT_LOGS : "triggers"
    PROJECTS ||--o{ PROJECT_ANALYSES : "analyzed_in"
    PROJECTS ||--o{ TEST_SUITES : "contains"
    PROJECTS ||--o{ TEST_RUNS : "executes"
    PROJECTS ||--o{ FAILURE_ANALYSES : "records"
    PROJECTS ||--o{ FLAKY_TEST_RECORDS : "tracks"
    PROJECTS ||--o{ REGRESSION_ANALYSES : "analyzes"
    PROJECTS ||--o{ CI_PIPELINE_RUNS : "runs_ci"
    PROJECTS ||--o{ QUALITY_REPORTS : "generates"
    
    TEST_SUITES ||--o{ TEST_CASES : "contains"
    TEST_RUNS ||--o{ TEST_RESULTS : "yields"
    TEST_RUNS ||--o{ FAILURE_ANALYSES : "diagnoses"
    TEST_RUNS ||--o{ SELECTIVE_EXECUTION_RUNS : "selects"
    
    REGRESSION_ANALYSES ||--o{ SELECTIVE_EXECUTION_RUNS : "governs"
    REGRESSION_ANALYSES ||--o{ CI_PIPELINE_RUNS : "informs"
    
    BENCHMARK_RUNS ||--o{ BENCHMARK_BUG_RESULTS : "evaluates"

    USERS {
        uuid id PK
        string email UK
        string full_name
        string role
        boolean is_active
        datetime created_at
    }

    PROJECTS {
        uuid id PK
        string name
        string repository_url
        string default_branch
        string language_framework
        uuid owner_id FK
        datetime created_at
    }

    TEST_SUITES {
        uuid id PK
        uuid project_id FK
        string name
        int total_cases
        int version
        datetime created_at
    }

    TEST_CASES {
        uuid id PK
        uuid suite_id FK
        string endpoint
        string method
        json request_payload
        json assertions
        datetime created_at
    }

    TEST_RUNS {
        uuid id PK
        uuid project_id FK
        uuid suite_id FK
        string status
        int total_tests
        int passed_tests
        int failed_tests
        float duration_ms
        datetime created_at
    }

    TEST_RESULTS {
        uuid id PK
        uuid test_run_id FK
        uuid test_case_id FK
        string outcome
        int status_code
        float execution_time_ms
        json assertion_failures
    }

    FAILURE_ANALYSES {
        uuid id PK
        uuid project_id FK
        uuid run_id FK
        string test_result_id
        string category
        string summary
        string fingerprint
        float classification_confidence
        datetime created_at
    }

    FLAKY_TEST_RECORDS {
        uuid id PK
        uuid project_id FK
        uuid test_case_id FK
        float flakiness_score
        int transition_count
        string status
        datetime last_evaluated_at
    }

    REGRESSION_ANALYSES {
        uuid id PK
        uuid project_id FK
        string base_commit
        string target_commit
        int total_suite_tests
        int selected_tier1_count
        int deferred_tier2_count
        float test_reduction_percent
        float estimated_time_avoided_ms
        datetime created_at
    }

    CI_PIPELINE_RUNS {
        uuid id PK
        uuid project_id FK
        string git_provider
        string base_commit
        string target_commit
        string pipeline_status
        string quality_gate_status
        float duration_ms
        datetime created_at
    }

    BENCHMARK_RUNS {
        uuid id PK
        string mode
        string execution_profile
        int total_bugs
        int total_controls
        int tp
        int fp
        int tn
        int fn
        float recall
        float precision
        float f1_score
        float bootstrap_ci_lower
        float bootstrap_ci_upper
        datetime completed_at
    }

    BENCHMARK_BUG_RESULTS {
        uuid id PK
        uuid benchmark_run_id FK
        string bug_id
        string service
        string detection_state
        boolean is_control
        int trial_index
        float execution_latency_ms
    }

    QUALITY_REPORTS {
        uuid id PK
        uuid project_id FK
        string title
        float quality_score
        string sha256_hash
        json summary_metrics
        text html_content
        datetime created_at
    }
```

---

## 4. Sequence Diagrams

### 4.1 Selective Regression Pipeline (Phase 8 & 9)

```mermaid
sequenceDiagram
    autonumber
    actor Developer
    participant GitHub as GitHub Webhook
    participant ASTRA_API as ASTRA API Server
    participant Celery as Celery Worker
    participant Engine as PKG & Impact Engine
    participant Runner as Isolated Test Sandbox
    participant DB as PostgreSQL DB

    Developer->>GitHub: Push Commit / Open PR (Base -> Target)
    GitHub->>ASTRA_API: POST /api/v1/integrations/github/webhook (HMAC signature)
    ASTRA_API->>ASTRA_API: Verify HMAC-SHA256 signature
    ASTRA_API->>DB: Store WebhookEvent & Create CIPipelineRun(QUEUED)
    ASTRA_API->>Celery: Enqueue Regression Task
    ASTRA_API-->>GitHub: 202 Accepted

    Celery->>Engine: Run Git Diff & AST Symbol Extraction
    Engine->>Engine: Traverse PKG Call-Graph (k-hop reachability)
    Engine->>Engine: Partition Tests into Tier 1 (Targeted) & Tier 2 (Deferred)
    Engine->>DB: Persist RegressionAnalysis & CodeChangeManifest

    Celery->>Runner: Execute Tier 1 Tests only (ASGITransport / HTTP)
    Runner-->>Celery: Test Results (Pass / Fail outcomes)
    
    Celery->>DB: Store TestRun & SelectiveExecutionRun
    Celery->>ASTRA_API: Evaluate Quality Gate (Pass Rate, Zero Critical Failures)
    ASTRA_API->>GitHub: POST /repos/.../check-runs (Status: Completed, Conclusion: Success)
    ASTRA_API->>GitHub: POST /issues/.../comments (PR Impact Summary Markdown)
```

### 4.2 Benchmark Empirical Ablation Study (Phase 10)

```mermaid
sequenceDiagram
    autonumber
    actor Researcher
    participant BenchAPI as Benchmark API (/runs)
    participant Runner as Benchmark Runner Engine
    participant Microservices as Benchmark Microservices (4 Apps)
    participant Matcher as 3-State Bug Matcher
    participant DB as PostgreSQL DB

    Researcher->>BenchAPI: POST /api/v1/benchmarks/runs (Mode: MODE_D, Profile, Trials: 3)
    BenchAPI->>Runner: Initialize Multi-Trial Evaluation

    loop For each Trial (1..N)
        Runner->>Microservices: Clean Reset & Seed DB State
        Runner->>Microservices: Activate Injected Bugs (1..50)
        
        loop For each Bug (1..50)
            Runner->>Microservices: Dispatch Bug Trigger Precondition Payload
            Microservices-->>Runner: HTTP Response (Status, Payload, Latency)
            Runner->>Matcher: Evaluate 3-State Matcher
            Note over Matcher: 1. TRIGGERED: Precondition matched<br/>2. DETECTED: Assertion failed<br/>3. ATTRIBUTED: Root cause mapped
            Matcher-->>Runner: Match State (TP or FN)
        end

        loop For each Negative Control (1..100)
            Runner->>Microservices: Dispatch Clean Invariant Payload
            Microservices-->>Runner: HTTP Response
            Runner->>Matcher: Evaluate Control Invariant
            Matcher-->>Runner: Match State (TN or FP)
        end
    end

    Runner->>Runner: Compute Confusion Matrix (TP, FP, TN, FN)
    Runner->>Runner: Calculate Empirical Metrics (Recall, Precision, Specificity, F1, FPR)
    Runner->>Runner: Execute 1,000 Bootstrap Resamples -> 95% Confidence Interval
    Runner->>DB: Persist BenchmarkRunModel & 150 BenchmarkBugResultModels
    Runner-->>BenchAPI: Complete BenchmarkRunReport
    BenchAPI-->>Researcher: Return JSON Report with Bootstrap Statistics
```

---

## 5. Security Architecture & SSRF Guard

ASTRA implements defense-in-depth isolation across all execution pathways:

1. **SSRF Guard**: All outbound synthetic HTTP test requests pass through an invariant IP address validator (`engine/execution/ssrf_guard.py`) that strictly prohibits private IPv4/IPv6 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16` AWS metadata) unless explicitly whitelisted for local container sandboxes.
2. **Secret Redaction**: Test payloads and server logs undergo regex masking for API tokens, Bearer tokens, private keys, and passwords before database persistence.
3. **HMAC Webhook Verification**: GitHub webhooks are validated using constant-time `hmac.compare_digest` with SHA-256 against secret tokens.
4. **Report Sanitization**: Executive audit HTML artifacts sanitize all user-supplied project names and titles, escaping `<script>`, `onerror`, and XSS injection vectors.
