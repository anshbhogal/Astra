# Phase 7 — ML Intelligence, Flakiness Engine & Human-in-the-Loop Test Healing Implementation Plan

> **Module Focus:** ML Classification Test Prioritization (XGBoost/RandomForest), Temporal Leakage Guards, APFD Metric Evaluation, State-Machine Flakiness Detection & Non-Blocking Quarantine, Normalized TF-IDF + Cosine DBSCAN Semantic Clustering, Safety-Validated Test Specification Healing, Versioning & Rollback, Async Celery Jobs, and REST/React Dashboards.

---

## 1. Executive Summary & Core Architectural Axioms

Phase 7 transforms ASTRA from automated execution and failure diagnosis into an enterprise-grade **self-optimizing quality platform**. Building on Phase 2 AST/PKG code churn, Phase 3 execution metrics, and Phase 6 root-cause failure diagnostics, Phase 7 introduces statistical machine learning, flakiness quarantine state-machines, and safety-validated test specification healing.

```text
                    ┌──────────────────────┐
                    │ Phase 2 PKG / Git    │
                    │ commit + code churn  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Phase 3 Test History │
                    │ runs/results/latency │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Phase 6 Diagnostics  │
                    │ category/RCA/evidence│
                    └──────────┬───────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │ Phase 7 Feature Store /   │
                 │ Dataset Builder           │
                 │ + Temporal Leakage Guard  │
                 └────────────┬──────────────┘
                              │
          ┌───────────────────┼────────────────────┐
          ▼                   ▼                    ▼
 ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐
 │ Prioritization │  │ Flakiness Engine│  │ Failure Clustering│
 │ XGBClassifier  │  │ State Machine   │  │ TF-IDF + DBSCAN  │
 └───────┬────────┘  └────────┬────────┘  └─────────┬────────┘
         │                    │                     │
         └────────────────────┼─────────────────────┘
                              ▼
                   ┌─────────────────────┐
                   │ Healing Candidate   │
                   │ Generator           │
                   └──────────┬──────────┘
                              ▼
                   ┌─────────────────────┐
                   │ Safety Validator    │
                   │ (Whitelist/Blacklist│
                   └──────────┬──────────┘
                              ▼
                    HUMAN REVIEW GATE
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
               APPROVE                 REJECT
                  │
                  ▼
             TestCase v2 (With Rollback)
```

### Core Architectural Axioms

1. **Zero-LLM ML Core & Baseline Fallbacks**: All ML pipelines (`XGBClassifier`, `RandomForestClassifier`, `TF-IDF`, `DBSCAN`, state-machines) run 100% locally and deterministically. If sample counts are insufficient ($N < 50$ runs), ASTRA automatically falls back to deterministic heuristic ranking (`PriorityScore = Risk * Impact / Cost`).
2. **Temporal Validation & Leakage Protection**: Data splitting strictly follows temporal ordering ($\text{Train} = \text{Older Runs}, \text{Validation} = \text{Subsequent Runs}, \text{Test} = \text{Latest Runs}$). Features for run $N$ are computed strictly using data available *before* run $N$.
3. **Binary Classification Formulation**: Prioritization is formulated as binary classification ($P(\text{FAIL} | \text{features}) = \text{predict\_proba}()[:, 1]$), combined with execution cost and failure severity into configurable ranking strategies (*Risk-First*, *Fast-Feedback*, *Severity-First*, *Balanced*). Evaluated empirically using **APFD (Average Percentage of Faults Detected)** and **NDCG@K**.
4. **Deterministic Flakiness & Non-Blocking Quarantine**: Flakiness detection uses a state machine tracking multi-outcome transitions (`PASS`, `FAIL`, `ERROR`, `TIMEOUT`, `ENVIRONMENT_ERROR`) over a minimum observation window ($N \ge 8$ runs, $T \ge 2$ transitions). Quarantined tests are executed in non-blocking mode (do not fail CI build gates) and require explicit human approval to quarantine.
5. **Normalized TF-IDF + DBSCAN Semantic Clustering**: Text normalizer strips dynamic values (UUIDs, timestamps, IPs, ports, dynamic paths) prior to TF-IDF vectorization. Post-clustering mapper assigns confidence metrics (`EXACT_MATCH` from Phase 6, `LIKELY_SAME`, `POSSIBLY_SAME`, `UNRELATED`).
6. **Human-in-the-Loop Test Healing & Safety Gate**: Healing generates proposed `TestCase.specification` patch candidates with strict operation whitelisting and blacklisting. Patches create immutable `TestCase v2` versions with 1-click rollback, optimistic locking, and audit trail (`MLActionAuditLog`). Automated spec mutation without human review is strictly prohibited.

---

## 2. Monorepo Directory Architecture

```text
d:\Astra\
├── ml/
│   ├── __init__.py
│   ├── common/
│   │   ├── schemas.py                     # Data Contracts & Feature Schemas
│   │   ├── versions.py                    # Model & Dataset Versioning
│   │   └── metrics.py                     # APFD, APFDc, NDCG@K Metric Calculators
│   ├── dataset/
│   │   ├── __init__.py
│   │   ├── builder.py                     # Historical Feature Extractor & Store
│   │   ├── schema.py                      # Dataset Column Schemas
│   │   ├── temporal_split.py              # Temporal Train/Val/Test Splitter
│   │   └── validator.py                   # Data Leakage Guard & Sanity Checks
│   ├── features/
│   │   ├── feature_extractor.py           # Feature Engineering Core
│   │   ├── failure_features.py            # Failure Category & Entropy Features
│   │   ├── performance_features.py        # Latency Mean & Std Dev Features
│   │   └── code_churn.py                  # Git/AST Churn Features from Phase 2
│   ├── prioritization/
│   │   ├── baseline.py                    # Deterministic Heuristic Risk Baselines
│   │   ├── prioritizer.py                 # XGBClassifier / RandomForest Classifier
│   │   ├── evaluator.py                   # APFD & Ranking Strategy Evaluator
│   │   └── ranking.py                     # Configurable Scoring (Risk/Fast/Balanced)
│   ├── flakiness/
│   │   ├── state_machine.py               # Outcome Sequence State Machine
│   │   ├── flakiness_detector.py          # Entropy & Latency Flakiness Score Calculator
│   │   └── quarantine.py                  # Quarantine Recommendation Engine
│   ├── clustering/
│   │   ├── normalizer.py                  # Dynamic Value Text Normalizer
│   │   ├── vectorizer.py                  # TF-IDF N-gram Vectorizer
│   │   ├── semantic_clusterer.py          # Cosine DBSCAN & Post-Clustering Mapper
│   │   └── evaluator.py                   # Cluster Silhouette & Purity Metrics
│   ├── healing/
│   │   ├── candidate_generator.py         # Structural Patch Candidate Generator
│   │   ├── patch_operations.py            # Whitelist/Blacklist Operation Enforcer
│   │   ├── safety_validator.py            # Security & Contract Safety Gate
│   │   ├── versioning.py                  # TestCase Spec Versioning & Rollback
│   │   └── healing_engine.py              # Orchestrator for Specification Healing
│   └── models/                            # Serialized ML Artifacts (.joblib)
│       └── .gitkeep
├── backend/app/
│   ├── api/v1/
│   │   └── ml.py                          # REST Router for ML, Flakiness & Healing
│   ├── tasks/
│   │   └── ml_tasks.py                    # Celery Async Processing Tasks
│   ├── services/
│   │   └── ml_service.py                  # Service Layer Orchestrating ML & DB
│   └── models/
│       └── domain.py                      # Phase 7 DB Models & Alembic Migration 0007
├── engine/tests/
│   ├── test_dataset_builder.py            # Dataset & Temporal Split Verification
│   ├── test_prioritization_ml.py          # XGBoost Training, APFD & Baseline Tests
│   ├── test_flakiness_state_machine.py    # State Machine & Quarantine Tests
│   ├── test_semantic_clustering.py        # Dynamic Normalization & DBSCAN Tests
│   └── test_healing_safety_gate.py        # Whitelist/Blacklist & Versioning Tests
├── backend/tests/
│   └── test_phase7_e2e_integration.py     # Complete Pipeline Integration Test
└── frontend/src/
    ├── components/
    │   ├── FlakyTestsDrawer.tsx           # Flaky Tests Quarantine Inspector
    │   ├── PriorityHeatmapCard.tsx        # Prioritized Execution Plan Inspector
    │   └── HealingInspectorModal.tsx      # Human Approval Diff Inspector & Rollback UI
    └── pages/
        └── MLAnalyticsTab.tsx             # Unified ML Dashboard
```

---

## 3. Database Domain Schemas (Alembic Migration `0007_ml_intelligence_schema.py`)

Five ORM models registered in [`backend/app/models/domain.py`](file:///d:/Astra/backend/app/models/domain.py):

```python
class MLJobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class FlakyTestStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RECOMMENDED_QUARANTINE = "RECOMMENDED_QUARANTINE"
    QUARANTINED = "QUARANTINED"
    RESOLVED = "RESOLVED"

class HealingCandidateStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"

class MLModelArtifactModel(Base):
    __tablename__ = "ml_model_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(50), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)  # XGBClassifier / RandomForest
    hyperparameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)  # APFD, NDCG, Precision@K
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    training_commit_sha: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class FlakyTestRecordModel(Base):
    __tablename__ = "flaky_test_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    test_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"))
    flakiness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    observation_window: Mapped[int] = mapped_column(Integer, default=10)
    transition_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pass_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_mean_ms: Mapped[float] = mapped_column(Float, default=0.0)
    latency_std_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[FlakyTestStatus] = mapped_column(String(30), default=FlakyTestStatus.ACTIVE)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class TestPriorityRankingModel(Base):
    __tablename__ = "test_priority_rankings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    test_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"))
    test_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"))
    failure_probability: Mapped[float] = mapped_column(Float, nullable=False)
    execution_cost_ms: Mapped[float] = mapped_column(Float, nullable=False)
    severity_weight: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank_order: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy: Mapped[str] = mapped_column(String(50), default="BALANCED")
    rationale: Mapped[str] = mapped_column(String(500), nullable=True)

class HealingCandidateModel(Base):
    __tablename__ = "healing_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    test_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"))
    failure_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("failure_analyses.id", ondelete="CASCADE"))
    source_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"))
    original_specification: Mapped[dict] = mapped_column(JSON, nullable=False)
    proposed_specification: Mapped[dict] = mapped_column(JSON, nullable=False)
    patch_operations: Mapped[list] = mapped_column(JSON, nullable=False)  # Allowed diff ops list
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    status: Mapped[HealingCandidateStatus] = mapped_column(String(20), default=HealingCandidateStatus.PENDING)
    approved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    resulting_spec_version: Mapped[int] = mapped_column(Integer, default=1)
    rollback_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class MLActionAuditLogModel(Base):
    __tablename__ = "ml_action_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # QUARANTINE_APPROVE, HEALING_APPROVE, HEALING_ROLLBACK
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

---

## 4. Subsystem Technical Specifications

### Milestone 7.1: Dataset Builder & Temporal Leakage Guard (`ml/dataset/`)
- Builds reproducible Pandas DataFrames from PostgreSQL tables.
- Enforces **Temporal Split**: `Train` (Runs $1 \dots T_1$), `Validation` (Runs $T_1+1 \dots T_2$), `Test` (Runs $T_2+1 \dots T_N$).
- **Leakage Guard**: Feature values for run $N$ are calculated strictly using data up to run $N-1$.
- Columns: `sample_id`, `project_id`, `test_case_id`, `test_run_id`, `commit_sha`, `historical_failure_rate_prev`, `recent_failure_rate_5runs`, `transition_entropy_prev`, `avg_latency_prev`, `latency_std_prev`, `code_churn_score`, `target_failed`.

### Milestone 7.2: Binary Classification Prioritization Engine (`ml/prioritization/`)
- Trains `XGBClassifier` and `RandomForestClassifier` to output $P(\text{FAIL} | \text{features}) = \text{predict\_proba}()[:, 1]$.
- Calculates Priority Score:
  $$\text{PriorityScore} = \frac{P(\text{FAIL}) \cdot \text{SeverityWeight}}{\text{NormalizedCost}_{\text{ms}} + 0.1}$$
- Evaluates against deterministic baselines (*Random*, *Historical Rate*, *Recent Rate*, *Heuristic Risk*) using **APFD (Average Percentage of Faults Detected)**:
  $$\text{APFD} = 1 - \frac{\sum_{i=1}^{m} TF_i}{n \cdot m} + \frac{1}{2n}$$
- Model serialization via `joblib` with versioning in `MLModelArtifactModel`.

### Milestone 7.3: State Machine Flakiness Engine & Non-Blocking Quarantine (`ml/flakiness/`)
- Tracks outcome sequences across $W = 10$ runs per test case.
- Requires minimum observation ($N \ge 8$ runs, $T \ge 2$ transitions) before triggering flakiness evaluation.
- Calculates Flakiness Index ($FI$):
  $$FI = 0.5 \cdot \text{TransitionRate} + 0.3 \cdot \left(\frac{\sigma_{\text{latency}}}{\mu_{\text{latency}} + 1}\right) + 0.2 \cdot \text{EnvFlakeRatio}$$
- Quarantined tests execute in **non-blocking mode** (do not fail CI build gate) after explicit human approval via the React UI.

### Milestone 7.4: Normalized TF-IDF + Cosine DBSCAN Failure Clusterer (`ml/clustering/`)
- **Text Normalizer**: Strips UUIDs (`[0-9a-f-]{36}`), timestamps, IP addresses, ports, and dynamic paths.
- **Vectorizer**: `TfidfVectorizer(ngram_range=(1,2), max_features=1000)`.
- **Clustering**: `DBSCAN(metric='cosine', eps=0.35, min_samples=2)`.
- Assigns macro-cluster confidence labels (`EXACT_MATCH` from Phase 6, `LIKELY_SAME`, `POSSIBLY_SAME`, `UNRELATED`).

### Milestone 7.5: Human-in-the-Loop Test Healing & Safety Gate (`ml/healing/`)
- Structural repair generator analyzing Phase 6 `FailureAnalysis` output and `TestCase.specification`.
- **Whitelist Operations**:
  - `REPLACE_EXPECTED_STATUS` (e.g., 200 $\rightarrow$ 201)
  - `ADD_EXPECTED_HEADER`
  - `REMOVE_EXPECTED_HEADER`
  - `RENAME_JSON_PATH` (e.g., `$.user_id` $\rightarrow$ `$.account_id`)
  - `UPDATE_JSON_VALUE_CONSTRAINT`
  - `UPDATE_LATENCY_THRESHOLD` (requires human confirmation)
- **Forbidden Blacklist Operations**:
  - `REMOVE_AUTH_ASSERTION`
  - `REMOVE_SECURITY_TEST`
  - `DISABLE_ASSERTION`
  - `CHANGE_HTTP_METHOD`
  - `CHANGE_TARGET_HOST`
  - `DISABLE_SSL_VALIDATION`
- **Versioning**: Approval creates `TestCase v2` with complete audit trail (`MLActionAuditLogModel`) and 1-click rollback capability. Optimistic locking prevents race conditions.

---

## 5. REST APIs & Celery Infrastructure

### Celery Async Tasks (`backend/app/tasks/ml_tasks.py`)
- `train_prioritization_model_task(project_id: str)`
- `evaluate_flakiness_task(project_id: str)`
- `cluster_semantic_defects_task(project_id: str, run_id: str)`

### REST Router (`backend/app/api/v1/ml.py`)
- `POST /api/v1/projects/{project_id}/ml/train` (Triggers Celery training job)
- `GET /api/v1/projects/{project_id}/ml/prioritize` (Returns ranked test execution plan)
- `GET /api/v1/projects/{project_id}/ml/flaky-tests` (Lists flaky test records)
- `POST /api/v1/projects/{project_id}/ml/flaky-tests/{id}/quarantine` (Approve/Reject quarantine)
- `GET /api/v1/projects/{project_id}/ml/healing-candidates` (Lists pending spec repair candidates)
- `POST /api/v1/projects/{project_id}/ml/healing-candidates/{id}/apply` (Human approval endpoint with optimistic locking)
- `POST /api/v1/projects/{project_id}/ml/healing-candidates/{id}/rollback` (Rollback to previous spec version)

All endpoints enforce JWT authentication (`get_current_user`), project RBAC access verification, and administrative role enforcement for state mutation.

---

## 6. Comprehensive Multi-Phase Execution Roadmap

```text
PHASE 7.0: Pre-ML Dataset Validation & Integration Contract Check
PHASE 7.1: Monorepo Setup & Database Migration 0007
PHASE 7.2: Dataset Builder & Temporal Leakage Guard (`ml/dataset/`)
PHASE 7.3: Deterministic Heuristic Prioritization Baseline (`ml/prioritization/baseline.py`)
PHASE 7.4: XGBoost / RandomForest Binary Classifier (`ml/prioritization/prioritizer.py`)
PHASE 7.5: APFD Ranking Metric Evaluator (`ml/prioritization/evaluator.py`)
PHASE 7.6: Outcome Sequence State Machine & Flakiness Engine (`ml/flakiness/`)
PHASE 7.7: Quarantine Approval Subsystem & Non-Blocking Execution Gate
PHASE 7.8: Dynamic Value Text Normalizer (`ml/clustering/normalizer.py`)
PHASE 7.9: TF-IDF + Cosine DBSCAN Semantic Failure Clusterer (`ml/clustering/`)
PHASE 7.10: Structural Test Specification Healing Candidate Generator (`ml/healing/`)
PHASE 7.11: Whitelist/Blacklist Safety Gate & Optimistic Locking Engine
PHASE 7.12: TestCase Spec Versioning, Rollback & Audit Logging
PHASE 7.13: Celery Background Tasks & REST API Router (`v1/ml.py`)
PHASE 7.14: React Dashboard Components (`FlakyTestsDrawer`, `PriorityHeatmap`, `HealingInspector`)
PHASE 7.15: Containerized Pytest Verification Suite (100% Pass Rate Target)
PHASE 7.16: Repository Documentation Update (`history.md`) & Git Commit
```
