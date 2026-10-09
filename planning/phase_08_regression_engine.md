# Phase 8 — Selective Regression Engine, AST Impact Analysis & Selective Execution Implementation Plan

> **Module Focus:** Multi-Commit & PR Git Diff Parser with Rename Detection, Symbol Identity AST Change Analyzer, PKG Weighted Edge Reachability Core, TestCase-to-Endpoint Impact Mapper, Conservative Safety Gate & Explainability Subsystem, Tier 1 (Targeted Regression) vs Tier 2 (Deferred Full Suite) Dynamic Selector, Regression Metrics & Oracle Evaluator, Celery Async Runner, and React Regression Telemetry Dashboard.

---

## 1. Executive Summary & Core Architectural Axioms

Phase 8 equips ASTRA with an enterprise-grade, **explainable, conservative selective regression testing platform**. Running an entire test suite of thousands of tests on every minor code commit is inefficient and wasteful. Phase 8 dynamically analyzes source code modifications, maps AST symbol mutations onto the Phase 2 Program Knowledge Graph (PKG), computes reachability vectors to API endpoints, bridges endpoints to test case specifications, and selectively executes only impacted tests in Tier 1 while deferring full-suite execution to Tier 2.

```text
Git Commit / PR Push (base_sha -> target_sha)
                 │
                 ▼
┌─────────────────────────────────┐
│     Git Diff Parser Engine      │ Detects modified, added, deleted, renamed files
└────────────────┬────────────────┘ (old_path -> new_path with similarity matching)
                 ▼
┌─────────────────────────────────┐
│     AST Change Analyzer         │ Extracts qualified symbol mutations
└────────────────┬────────────────┘ (FUNCTIONS, CLASSES, SIGNATURES, DECORATORS, IMPORTS)
                 ▼
┌─────────────────────────────────┐
│ PKG Reachability Impact Core    │ Traverses weighted edges (CALLS=1.0, ROUTE=1.0, IMPORTS=0.5)
└────────────────┬────────────────┘ (mutated symbol -> caller chain -> impacted endpoint)
                 ▼
┌─────────────────────────────────┐
│ Test Impact Mapper              │ Maps impacted endpoints -> TestCase.specification
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ Conservative Safety Gate        │ Triggers Tier 1 safety expansion for UNKNOWN impact,
└────────────────┬────────────────┘ global dependencies, or parser warnings
                 ▼
┌─────────────────────────────────┐
│ Phase 7 Risk-Aware Selector     │ Filters tests into Tier 1 (Immediate Targeted)
└────────────────┬────────────────┘ and Tier 2 (Deferred Full Regression)
                 ▼
┌─────────────────────────────────┐
│ Celery Execution & Telemetry    │ Executes Tier 1 tests with commit snapshot binding
└─────────────────────────────────┘ (Evaluates Recall, Precision, False Negative Rate, Speedup)
```

### Core Architectural Axioms

1. **Selective Regression Safety Axiom (ZERO False Negatives Priority)**: ASTRA optimizes to **minimize false negatives** while maximizing test reduction. Over-selection is strictly preferred over under-selection whenever impact confidence is low or incomplete.
2. **Deterministic-First AST/PKG Impact Core (Zero-LLM Axiom)**: Code change detection, symbol mutation extraction, and PKG dependency reachability execute 100% locally and deterministically using `ast`, Tree-Sitter, `GitPython`, and `networkx`.
3. **Phase Separation Principle**: **Phase 8 determines test eligibility** (which tests are impacted or required for safety); **Phase 7 determines test execution priority** (which eligible tests run first).
4. **Symbol Identity Matching (Line-Number Resilient)**: AST symbol mutations are tracked using qualified identities (`language:module.Class.method`) rather than line ranges alone, correctly categorizing `FUNCTION_ADDED`, `FUNCTION_MODIFIED`, `SIGNATURE_CHANGED`, `DECORATOR_CHANGED`, and `RENAME_DETECTED`.
5. **Weighted Edge Reachability & Impact Bands**: PKG traversal accounts for edge types (`CALLS` = 1.0, `ROUTE` = 1.0, `INHERITS` = 0.7, `IMPORTS` = 0.5) to compute multi-factor Impact Scores rather than relying on rigid distance thresholds.
6. **Conservative Unknown Impact Handling**: Dynamic imports, reflection, shared global dependencies, or parser warnings automatically emit `UNKNOWN_IMPACT` and trigger safety expansion in Tier 1.
7. **Explainable Selection & Snapshot Consistency**: Every selected or deferred test case carries machine-readable `selection_reason`, `exclusion_reason`, `impact_path_trace`, and `confidence_score`. Selective execution strictly verifies that the execution environment commit matches the `target_commit`.
8. **Deferred $\neq$ Skipped**: Tier 1 provides immediate targeted regression feedback; Tier 2 represents deferred full regression (async background / nightly CI).

---

## 2. Monorepo Directory Architecture

```text
d:\Astra\
├── engine/regression/                     # Phase 8 Core Subsystem
│   ├── __init__.py
│   ├── git_diff_parser.py                 # Multi-Commit & PR Diff Analyzer with Rename Detection
│   ├── ast_change_analyzer.py              # Symbol Identity & Mutation Extractor
│   ├── impact_analyzer.py                 # PKG Weighted Edge Dependency Reachability Core
│   ├── test_impact_mapper.py              # TestCase -> Endpoint -> Code Reachability Mapper
│   ├── safety_gate.py                     # Conservative Safety Gate & Unknown Impact Expander
│   ├── selective_selector.py              # Tier 1 vs Tier 2 Test Suite Selector
│   ├── change_telemetry.py                # Telemetry, Recall & Speedup Calculator
│   └── evaluators.py                      # Regression Oracle & Precision/Recall Benchmark Engine
├── backend/app/
│   ├── api/v1/
│   │   └── regression.py                  # REST Router for Impact Analysis, Selection & History
│   ├── tasks/
│   │   └── regression_tasks.py            # Celery Async Processing Tasks
│   ├── services/
│   │   └── regression_service.py          # Service Layer Orchestrating Diff, PKG, ML & DB
│   └── models/
│       └── domain.py                      # Phase 8 DB Models & Alembic Migration 0008
├── engine/tests/
│   ├── test_git_diff_parser.py            # Rename & line delta unit tests
│   ├── test_ast_change_analyzer.py        # Symbol identity matching unit tests
│   ├── test_impact_analyzer.py            # PKG reachability unit tests
│   ├── test_test_impact_mapper.py         # TestCase mapping unit tests
│   ├── test_safety_gate.py                # Safety expansion unit tests
│   ├── test_selective_selector.py         # Tier 1 / Tier 2 selection unit tests
│   └── test_regression_oracle.py          # Recall, Precision & Oracle benchmark tests
├── backend/tests/
│   └── test_phase8_e2e_integration.py     # Complete Pipeline Integration Test
└── frontend/src/
    ├── components/
    │   ├── ChangeImpactGraph.tsx          # PKG Visual Impact Tree Inspector
    │   ├── SelectionReasonDrawer.tsx      # "Why was this test selected?" Drawer
    │   ├── SelectiveSuiteCard.tsx         # Tier 1 vs Tier 2 Selection Inspector
    │   └── RegressionTelemetryCard.tsx    # Recall, Speedup & Time Avoided Metrics
    └── pages/
        └── RegressionDashboardTab.tsx     # Unified Regression Analytics Dashboard
```

---

## 3. Database Domain Schemas (Alembic Migration `0008_regression_schema.py`)

Four ORM models registered in [`backend/app/models/domain.py`](file:///d:/Astra/backend/app/models/domain.py):

```python
class ExecutionTier(str, Enum):
    TIER1_TARGETED = "TIER1_TARGETED"
    TIER2_DEFERRED_FULL = "TIER2_DEFERRED_FULL"

class RegressionAnalysisStatus(str, Enum):
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class RegressionAnalysisModel(Base):
    __tablename__ = "regression_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    base_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    target_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    target_branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pkg_snapshot_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0")
    total_modified_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_modified_symbols: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_impacted_endpoints: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_suite_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selected_tier1_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deferred_tier2_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    test_reduction_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    estimated_time_avoided_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    impact_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    safety_expansion_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[RegressionAnalysisStatus] = mapped_column(SQLEnum(RegressionAnalysisStatus), default=RegressionAnalysisStatus.QUEUED, nullable=False)
    analysis_warnings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class CodeChangeManifestModel(Base):
    __tablename__ = "code_change_manifests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regression_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("regression_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    old_path: Optional[Mapped[str]] = mapped_column(String(500), nullable=True)
    new_path: Mapped[str] = mapped_column(String(500), nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # M, A, D, RENAMED, COPIED
    rename_similarity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    modified_lines: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    modified_symbols: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    change_category: Mapped[str] = mapped_column(String(50), default="FUNCTION_MODIFIED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class EndpointImpactRecordModel(Base):
    __tablename__ = "endpoint_impact_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regression_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("regression_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint_id: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    impact_distance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    impact_type: Mapped[str] = mapped_column(String(30), default="DIRECT", nullable=False)  # DIRECT, INDIRECT, UNKNOWN
    impact_path_trace: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    dependency_edge_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

class SelectiveExecutionRunModel(Base):
    __tablename__ = "selective_execution_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regression_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("regression_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    test_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_tier: Mapped[ExecutionTier] = mapped_column(SQLEnum(ExecutionTier), default=ExecutionTier.TIER1_TARGETED, nullable=False)
    selected_test_details: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # [{test_case_id, selection_reason, confidence, impact_path}]
    deferred_test_details: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # [{test_case_id, exclusion_reason}]
    selection_recall: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    selection_precision: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    tier1_actual_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tier2_actual_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Alembic Migration: `0008_regression_schema.py`.

---

## 4. Subsystem Technical Specifications

### Milestone 8.1: Git Diff Parser & Rename Detector (`engine/regression/git_diff_parser.py`)
- Inspects commits using `GitPython` across base SHA and target SHA.
- Identifies file changes including `MODIFIED`, `ADDED`, `DELETED`, `RENAMED` (`old_path` $\rightarrow$ `new_path`), and `COPIED`.
- Parses hunk headers to extract exact line ranges added (`+`) or deleted (`-`).

### Milestone 8.2: Symbol Identity AST Change Analyzer (`engine/regression/ast_change_analyzer.py`)
- Uses Python `ast` and Tree-Sitter parsers to extract qualified symbol identities (`language:module.Class.method`).
- Categorizes change semantics: `FUNCTION_ADDED`, `FUNCTION_REMOVED`, `FUNCTION_MODIFIED`, `SIGNATURE_CHANGED`, `DECORATOR_CHANGED`, `IMPORT_CHANGED`, `GLOBAL_CONFIG_CHANGED`.

### Milestone 8.3: PKG Weighted Edge Reachability Core (`engine/regression/impact_analyzer.py`)
- Traverses PKG graph (`nx.DiGraph`) with edge weights: `CALLS` (1.0), `ROUTE` (1.0), `USES` (0.8), `INHERITS` (0.7), `IMPORTS` (0.5).
- Performs backward call graph reachability from mutated symbols to caller functions to endpoint handler nodes.
- Emits structured impact records with call trace vectors and confidence scores.

### Milestone 8.4: TestCase-to-Endpoint Impact Mapper (`engine/regression/test_impact_mapper.py`)
- Maps impacted endpoints to `TestCase.specification` records in project test suite.
- Constructs `TestImpactRecord` detailing `test_case_id`, `endpoint_id`, `impact_score`, `selection_reason`, `impact_path_trace`.

### Milestone 8.5: Conservative Safety Gate (`engine/regression/safety_gate.py`)
- Evaluates risk triggers: global dependency modifications, auth/security code changes, parser warnings, PKG unresolved symbols, or low analysis confidence.
- Automatically triggers **Safety Expansion** in Tier 1 whenever confidence is insufficient, fulfilling the Zero False Negatives Axiom.

### Milestone 8.6: Tiered Selective Selector & Metrics Engine (`engine/regression/selective_selector.py`)
- Integrates impact mapper output with Phase 7 ML prioritization scores.
- Selects **Tier 1 (Immediate Targeted Regression)** and **Tier 2 (Deferred Full Regression)**.
- Computes **Test Reduction %**, **Estimated Execution Time Avoided (ms)**, **Selection Recall**, and **Selection Precision**.

### Milestone 8.7: Celery Tasks & Service Layer (`backend/app/services/regression_service.py`)
- Orchestrates snapshot verification, analysis fingerprinting, Celery task dispatching, and database persistence.
- Provides endpoints in [`backend/app/api/v1/regression.py`](file:///d:/Astra/backend/app/api/v1/regression.py).

### Milestone 8.8: React UI Dashboard (`frontend/src/pages/RegressionDashboardTab.tsx`)
- **`ChangeImpactGraph.tsx`**: Interactive tree showing mutated symbol $\rightarrow$ caller chain $\rightarrow$ endpoint $\rightarrow$ test case.
- **`SelectionReasonDrawer.tsx`**: Drawer showing explicit "Why was this test selected/deferred?" rationale.
- **`SelectiveSuiteCard.tsx`**: Interactive Tier 1 vs Tier 2 execution trigger.
- **`RegressionTelemetryCard.tsx`**: Metrics showing Recall, Precision, Test Reduction %, and Compute Time Avoided.

---

## 5. Verification & Pytest Test Matrix

1. **Git Rename & Hunk Line Delta Test** (`engine/tests/test_git_diff_parser.py`):
   - Rename file `order_service.py` to `order_manager.py` and modify line 20. Verify parser identifies `RENAMED` change type and isolates line 20 delta.
2. **Symbol Identity AST Mutation Test** (`engine/tests/test_ast_change_analyzer.py`):
   - Modify decorator `@router.post("/orders")`. Verify matcher emits `DECORATOR_CHANGED` with symbol `services.orders.create_order`.
3. **PKG Reachability & Edge Weight Test** (`engine/tests/test_impact_analyzer.py`):
   - Traverse synthetic PKG from helper function through `CALLS` edge to endpoint handler. Verify reachability trace and confidence score calculation.
4. **TestCase Impact Mapper Test** (`engine/tests/test_test_impact_mapper.py`):
   - Map endpoint `POST /orders` to `TestCase.specification`. Verify exact `selection_reason` and path trace generation.
5. **Safety Gate Expansion Test** (`engine/tests/test_safety_gate.py`):
   - Simulate unresolved symbol or global auth change. Verify safety gate expands Tier 1 selection to prevent false negatives.
6. **Regression Oracle & Metrics Test** (`engine/tests/test_regression_oracle.py`):
   - Compare actual post-change failures against selected tests. Assert Selection Recall $\ge 99\%$.
7. **Full E2E Containerized Integration Test** (`backend/tests/test_phase8_e2e_integration.py`):
   - Complete pipeline test: DB $\rightarrow$ Git Diff $\rightarrow$ AST Change $\rightarrow$ PKG Reachability $\rightarrow$ Safety Expansion $\rightarrow$ Selective Suite Filtering $\rightarrow$ Celery Execution $\rightarrow$ Telemetry REST API.

---

## 6. Comprehensive Multi-Phase Execution Roadmap

```text
PHASE 8.0: Integration & Pre-Regression Contract Check
PHASE 8.1: Monorepo Setup & Database Migration 0008
PHASE 8.2: Git Diff Parser with Rename & Hunk Delta Detection (`engine/regression/git_diff_parser.py`)
PHASE 8.3: Qualified Symbol Identity AST Change Analyzer (`engine/regression/ast_change_analyzer.py`)
PHASE 8.4: PKG Weighted Edge Reachability Impact Engine (`engine/regression/impact_analyzer.py`)
PHASE 8.5: TestCase-to-Endpoint Impact Mapper (`engine/regression/test_impact_mapper.py`)
PHASE 8.6: Conservative Safety Gate & Unknown Impact Expander (`engine/regression/safety_gate.py`)
PHASE 8.7: Tiered Selective Suite Selector & Metrics Engine (`engine/regression/selective_selector.py`)
PHASE 8.8: Regression Oracle Evaluator (Recall, Precision, Speedup Metrics)
PHASE 8.9: Celery Async Tasks & REST Router (`v1/regression.py`)
PHASE 8.10: React Dashboard Components (`ChangeImpactGraph`, `SelectionReasonDrawer`, `RegressionTelemetry`)
PHASE 8.11: Containerized Pytest Verification Suite (100% Pass Rate Target)
PHASE 8.12: Repository Documentation Update (`history.md`) & Git Commit
```
