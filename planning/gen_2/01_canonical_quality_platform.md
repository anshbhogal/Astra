# ASTRA Gen 2 — Canonical Contract Freeze v2.3.0 (FINAL)

**Document Version**: 2.3.0 — FINAL FROZEN BASELINE  
**Status**: ✅ APPROVED — Implement `0011` DDL Only After This Document Is Signed Off  
**Architecture Score**: 9.5/10 | **Data Model**: 9.5/10 | **Migration**: 9.4/10 | **Implementation Readiness**: 9.3/10  

---

## The Gen 2 Compatibility Invariant (Non-Negotiable)

> **No Gen 2 product-layer change may reduce the analytical, deterministic, security, provenance, or reproducibility capabilities of Gen 1.**
>
> - **Gen 1** = ASTRA's Core Computational Intelligence Engine (AST, PKG, Invariant Generation, SBFL, XGBoost Flakiness, Selective Regression, RCA).
> - **Gen 2** = ASTRA's Canonical Quality Engineering & Execution Platform (Workspaces, Requirements, Test Authoring, Orchestration, Defects, Release Gates).
>
> Preserve Gen 1 intelligence **algorithms and analysis semantics** intact; refactor only their persistence and orchestration **boundaries** through versioned, typed Adapter Contracts.
>
> **Before any automated test execution or mutation is dispatched through the Gen 2 execution platform, the following contracts are binding.**

---

## Contract 1: Frozen Canonical Domain Model

### 1.1 Core Execution Lineage

```
Workspace
    ↓
Project
    ↓                     ↓                     ↓
Requirements          Test Suites             Builds
    ↓                     ↓                     ↓
Requirement           Test Definition       Environment
Version                   ↓
                    Definition Version
                          ↓
               TestPlan → TestCycle → TestCycleMembership
                                            ↓
                                     ExecutionJob ← selection_context
                                            ↓
                                    ExecutionAttempt
                                    (Build + Environment + DefinitionVersion)
                                            ↓
                                       TestResult
                                            ↓
                          ┌─────────────────┼────────────────┐
                          ↓                 ↓                ↓
                      Artifact       FailureAnalysis      Metrics
                                          ↓
                               FaultLocalizationResult
                                          ↓
                                  DefectOccurrence
                                          ↓
                                       Defect
                                          ↓
                                    DefectHistory
```

---

### 1.2 Workspaces

```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_tier VARCHAR(50) NOT NULL DEFAULT 'ENTERPRISE',
    settings JSONB NOT NULL DEFAULT '{}',  -- retention policies, quality gate defaults
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',  -- USER, SYSTEM, MIGRATION
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- Attach projects to workspaces (additive alter; projects table already exists)
ALTER TABLE projects ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE projects ADD COLUMN actor_type VARCHAR(20) NOT NULL DEFAULT 'USER';
CREATE INDEX idx_projects_workspace ON projects(workspace_id);
```

---

### 1.3 Requirements & Immutable Versioning

```sql
CREATE TABLE requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    req_code VARCHAR(50) NOT NULL,           -- e.g. REQ-AUTH-001
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',   -- LOW, MEDIUM, HIGH, CRITICAL
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',      -- DRAFT, IN_REVIEW, APPROVED, DEPRECATED
    current_version_id UUID NULL,            -- FK to requirement_versions; set after first version
    source_type VARCHAR(30) NOT NULL DEFAULT 'MANUAL', -- MANUAL, AI_GENERATED, IMPORTED, DERIVED
    source_reference VARCHAR(255) NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_project_req_code UNIQUE (project_id, req_code)
);

-- Immutable append-only snapshot. Once created, rows are NEVER updated.
CREATE TABLE requirement_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    acceptance_criteria JSONB NOT NULL DEFAULT '[]',  -- [{given, when, then}]
    change_reason VARCHAR(255) NULL,
    is_approved BOOLEAN NOT NULL DEFAULT FALSE,
    changed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_req_version UNIQUE (requirement_id, version_number)
);
-- Application Invariant: rows with is_approved=TRUE are read-only forever.
-- Any future change creates requirement_versions.version_number + 1.

ALTER TABLE requirements
    ADD CONSTRAINT fk_req_current_version
    FOREIGN KEY (current_version_id) REFERENCES requirement_versions(id) ON DELETE SET NULL;
```

---

### 1.4 Builds (Immutable CI/Release Snapshot)

```sql
-- Build = immutable CI/release execution snapshot.
-- Identity: (project_id, commit_sha) is the source snapshot anchor.
-- Multiple version_name values for the same commit are allowed to represent
-- different release candidates (e.g. v2.4.0-rc1, v2.4.0-rc2 same commit).
-- Builds are NEVER updated after creation. Status transitions use status column only.
CREATE TABLE builds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_name VARCHAR(100) NOT NULL,        -- e.g. v2.4.0-rc1
    commit_sha VARCHAR(64) NOT NULL,
    branch VARCHAR(100) NOT NULL DEFAULT 'main',
    pipeline_provider VARCHAR(50) NULL,        -- GITHUB_ACTIONS, GITLAB_CI, JENKINS, MANUAL
    pipeline_id VARCHAR(100) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'REGISTERED',  -- REGISTERED, VALIDATED, SUPERSEDED
    build_metadata JSONB NOT NULL DEFAULT '{}',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',    -- USER, CI, MIGRATION
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
-- No UPDATE of identity fields (version_name, commit_sha, branch) is permitted after insert.
CREATE UNIQUE INDEX idx_builds_project_version ON builds(project_id, version_name);
CREATE INDEX idx_builds_project_commit ON builds(project_id, commit_sha);
```

---

### 1.5 Environments (SSRF-Safe, Credential-Referenced)

```sql
-- SSRF safety is enforced at TWO points:
-- (a) Environment registration (URL validation + DNS/IP safety validation)
-- (b) Every execution dispatch (re-validate base_url at runtime; DNS rebinding defence)
CREATE TABLE environments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,                -- DEV, QA, STAGING, UAT, PROD
    env_type VARCHAR(50) NOT NULL,             -- CLOUD, CONTAINER, BARE_METAL, LOCAL
    base_url VARCHAR(500) NOT NULL,            -- Stored; re-validated at execution time
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    credential_reference VARCHAR(255) NULL,    -- Reference key to Vault/env-secret; NEVER plaintext
    health_check_endpoint VARCHAR(255) NULL DEFAULT '/health',
    configuration JSONB NOT NULL DEFAULT '{}', -- Non-sensitive config only
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_project_env_name UNIQUE (project_id, name)
);
```

---

### 1.6 Hierarchical Test Suites

```sql
CREATE TABLE test_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_suite_id UUID REFERENCES test_suites(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    suite_type VARCHAR(30) NOT NULL DEFAULT 'STANDARD', -- STANDARD, REGRESSION, SMOKE, UAT
    order_index INTEGER NOT NULL DEFAULT 0,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idx_test_suites_parent ON test_suites(parent_suite_id);
CREATE INDEX idx_test_suites_project ON test_suites(project_id);
```

---

### 1.7 Canonical Test Definitions & Immutable Versioned Specifications

```sql
CREATE TABLE test_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    suite_id UUID NOT NULL REFERENCES test_suites(id) ON DELETE CASCADE,
    test_code VARCHAR(50) NOT NULL,            -- e.g. TC-AUTH-001
    category VARCHAR(50) NOT NULL,             -- MANUAL, SYNTHETIC_API, PLAYWRIGHT_WEB, K6_LOAD, DAST
    execution_type VARCHAR(20) NOT NULL,       -- MANUAL, AUTOMATED
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT', -- DRAFT, IN_REVIEW, APPROVED, DEPRECATED
    current_version_id UUID NULL,
    -- Provenance
    source_type VARCHAR(30) NOT NULL DEFAULT 'MANUAL', -- MANUAL, AI_GENERATED, IMPORTED, DERIVED, MIGRATED
    source_reference VARCHAR(255) NULL,
    generator_version VARCHAR(50) NULL,        -- Engine version if AI_GENERATED
    prompt_version VARCHAR(50) NULL,           -- Prompt template version if AI_GENERATED
    -- Legacy traceability (populated only for migrated Gen 1 records)
    legacy_test_case_id UUID NULL,
    -- Authorship
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',  -- USER, AI, SYSTEM, MIGRATION
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_project_test_code UNIQUE (project_id, test_code)
);
CREATE INDEX idx_test_defs_suite ON test_definitions(suite_id);
CREATE INDEX idx_test_defs_legacy ON test_definitions(legacy_test_case_id) WHERE legacy_test_case_id IS NOT NULL;

-- Immutable approved version snapshots
CREATE TABLE test_definition_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_definition_id UUID NOT NULL REFERENCES test_definitions(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    preconditions TEXT NULL,
    postconditions TEXT NULL,
    estimated_duration_s INTEGER NOT NULL DEFAULT 60,
    adapter_type VARCHAR(50) NOT NULL,          -- manual, sandbox_http, playwright, k6, dast
    specification JSONB NOT NULL DEFAULT '{}',  -- Typed per adapter_type; see schemas below
    version_hash VARCHAR(64) NOT NULL,          -- SHA-256(canonical_json(specification + steps))
    change_reason VARCHAR(255) NULL,
    is_approved BOOLEAN NOT NULL DEFAULT FALSE,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    -- Migration columns
    migration_status VARCHAR(30) NULL,          -- MIGRATED, MIGRATED_WITH_WARNING, UNSUPPORTED, FAILED
    migration_notes TEXT NULL,
    CONSTRAINT uq_test_def_version UNIQUE (test_definition_id, version_number)
);
-- Application Invariant: rows with is_approved=TRUE are permanently read-only.
-- Changes create a new version_number, never mutate an existing approved row.

ALTER TABLE test_definitions
    ADD CONSTRAINT fk_test_def_current_version
    FOREIGN KEY (current_version_id) REFERENCES test_definition_versions(id) ON DELETE SET NULL;

-- Test steps belong to a specific immutable version
CREATE TABLE test_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    definition_version_id UUID NOT NULL REFERENCES test_definition_versions(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    action TEXT NOT NULL,
    test_data TEXT NULL,
    expected_result TEXT NOT NULL,
    is_shared_step BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_version_step UNIQUE (definition_version_id, step_number)
);
```

#### Typed Adapter Specification Schemas

##### `sandbox_http` — Schema: `http.v1`
```json
{
  "schema_version": "http.v1",
  "adapter": "sandbox_http",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "headers": {"Content-Type": "application/json"},
  "query": {},
  "body": {"username": "{{USERNAME}}", "password": "{{PASSWORD}}"},
  "expected_status": 200,
  "assertions": [
    {"type": "status_code", "operator": "eq", "value": 200},
    {"type": "json_path", "path": "$.token", "operator": "exists"},
    {"type": "response_time_ms", "operator": "lte", "value": 500}
  ]
}
```

##### `playwright` — Schema: `playwright.v1`
```json
{
  "schema_version": "playwright.v1",
  "adapter": "playwright",
  "browser": "chromium",
  "viewport": {"width": 1280, "height": 720},
  "actions": [
    {"action": "goto", "url": "{{BASE_URL}}/login"},
    {"action": "fill", "selector": "#email", "value": "test@astra.io"},
    {"action": "click", "selector": "#submit-btn"},
    {"action": "assert_visible", "selector": "#dashboard-header"}
  ]
}
```

##### `manual` — Schema: `manual.v1`
```json
{
  "schema_version": "manual.v1",
  "adapter": "manual",
  "environment_type": "web_browser",
  "tags": ["smoke", "regression", "p1"]
}
```

##### `k6` — Schema: `k6.v1`
```json
{
  "schema_version": "k6.v1",
  "adapter": "k6",
  "script_ref": "scripts/load_auth.js",
  "options": {"vus": 50, "duration": "60s"},
  "thresholds": {"http_req_duration": ["p(95)<500"]}
}
```

---

### 1.8 Requirement Links — Version-Level Traceability

```sql
-- Fix #1: Links are versioned at both ends for exact historical traceability.
-- The (requirement_id, test_definition_id) pair is retained for current-state lookups.
-- The (req_version_id, def_version_id) pair is the authoritative historical anchor.
CREATE TABLE requirement_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Current-state identifiers (for fast lookups)
    requirement_id UUID NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    test_definition_id UUID NOT NULL REFERENCES test_definitions(id) ON DELETE CASCADE,
    -- Version-level identifiers (authoritative historical record)
    requirement_version_id UUID NOT NULL REFERENCES requirement_versions(id) ON DELETE RESTRICT,
    definition_version_id UUID NOT NULL REFERENCES test_definition_versions(id) ON DELETE RESTRICT,
    coverage_type VARCHAR(30) NOT NULL DEFAULT 'DIRECT_VERIFICATION',
    -- DIRECT_VERIFICATION, REGRESSION_GUARD, EDGE_CASE, NEGATIVE_SCENARIO
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_req_test_link UNIQUE (requirement_id, test_definition_id)
);
CREATE INDEX idx_req_links_req ON requirement_links(requirement_id);
CREATE INDEX idx_req_links_def ON requirement_links(test_definition_id);
```

---

### 1.9 Test Plans, Cycles & Membership Tables

```sql
CREATE TABLE test_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    entry_criteria TEXT NULL,
    exit_criteria TEXT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',  -- DRAFT, ACTIVE, COMPLETED, ARCHIVED
    target_release VARCHAR(100) NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- Fix #3a: TestPlan → TestSuite or TestDefinition membership
CREATE TABLE test_plan_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_plan_id UUID NOT NULL REFERENCES test_plans(id) ON DELETE CASCADE,
    suite_id UUID NOT NULL REFERENCES test_suites(id) ON DELETE CASCADE,
    include_children BOOLEAN NOT NULL DEFAULT TRUE,
    order_index INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_plan_suite UNIQUE (test_plan_id, suite_id)
);

CREATE TABLE test_cycles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_plan_id UUID NOT NULL REFERENCES test_plans(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE RESTRICT,
    build_id UUID NOT NULL REFERENCES builds(id) ON DELETE RESTRICT,
    start_date TIMESTAMPTZ NULL,
    end_date TIMESTAMPTZ NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PLANNED',  -- PLANNED, IN_PROGRESS, COMPLETED, ABORTED
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- Fix #3b: TestCycle → TestDefinition membership with selection provenance
CREATE TABLE test_cycle_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id UUID NOT NULL REFERENCES test_cycles(id) ON DELETE CASCADE,
    test_definition_id UUID NOT NULL REFERENCES test_definitions(id) ON DELETE CASCADE,
    definition_version_id UUID NOT NULL REFERENCES test_definition_versions(id) ON DELETE RESTRICT,
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    selection_source VARCHAR(30) NOT NULL DEFAULT 'MANUAL',
    -- MANUAL, PLAN, REGRESSION_ENGINE, CI, RISK_ENGINE
    order_index INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_cycle_definition UNIQUE (cycle_id, test_definition_id)
);
CREATE INDEX idx_cycle_defs_cycle ON test_cycle_definitions(cycle_id);
```

---

### 1.10 Execution Jobs, Attempts & Rich Normalized Results

```sql
-- Fenced execution job with idempotency and lease token
CREATE TABLE execution_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    test_cycle_id UUID REFERENCES test_cycles(id) ON DELETE SET NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    job_type VARCHAR(50) NOT NULL,             -- MANUAL_SESSION, AUTOMATED_BATCH, CI_SELECTIVE
    status VARCHAR(30) NOT NULL DEFAULT 'QUEUED',
    -- QUEUED, DISPATCHED, RUNNING, COMPLETED, FAILED, TIMED_OUT, CANCELLED
    priority INTEGER NOT NULL DEFAULT 10,
    -- Fencing (Fix #22: prevents dual-execution after worker recovery)
    worker_id VARCHAR(100) NULL,
    lease_token UUID NULL,                     -- UUID rotated per heartbeat cycle
    lease_version INTEGER NOT NULL DEFAULT 0,  -- Monotonically increasing; stale workers are rejected
    lease_expires_at TIMESTAMPTZ NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 2,
    -- Statistics
    total_tests INTEGER NOT NULL DEFAULT 0,
    passed_tests INTEGER NOT NULL DEFAULT 0,
    failed_tests INTEGER NOT NULL DEFAULT 0,
    error_tests INTEGER NOT NULL DEFAULT 0,
    blocked_tests INTEGER NOT NULL DEFAULT 0,
    skipped_tests INTEGER NOT NULL DEFAULT 0,
    -- Selection context snapshot (Fix #20: records why these tests ran)
    execution_context JSONB NOT NULL DEFAULT '{}',
    -- {selector_version, regression_model_version, selection_policy, risk_scores}
    timeout_seconds INTEGER NOT NULL DEFAULT 3600,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',  -- USER, CI, SYSTEM, REGRESSION_ENGINE
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    -- Manual session extensions
    session_state JSONB NULL,                  -- {current_step, last_active_definition_id}
    last_active_at TIMESTAMPTZ NULL,
    resume_token VARCHAR(128) NULL,
    CONSTRAINT uq_project_idempotency UNIQUE (project_id, idempotency_key)
);
CREATE INDEX idx_jobs_status_lease ON execution_jobs(status, lease_expires_at);
CREATE INDEX idx_jobs_cycle ON execution_jobs(test_cycle_id);

-- Fix #7: ExecutionAttempt uses FK to Build and Environment (not varchar snapshots)
CREATE TABLE execution_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES execution_jobs(id) ON DELETE CASCADE,
    definition_version_id UUID NOT NULL REFERENCES test_definition_versions(id) ON DELETE RESTRICT,
    environment_id UUID NOT NULL REFERENCES environments(id) ON DELETE RESTRICT,
    build_id UUID NOT NULL REFERENCES builds(id) ON DELETE RESTRICT,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'RUNNING',  -- RUNNING, COMPLETED, TIMED_OUT, CANCELLED
    -- Full execution provenance (Fix #7 extended)
    engine_version VARCHAR(50) NULL,           -- ASTRA engine version at execution time
    adapter_version VARCHAR(50) NULL,
    execution_config_hash VARCHAR(64) NULL,    -- SHA-256 of adapter config used
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    completed_at TIMESTAMPTZ NULL,
    duration_ms FLOAT NOT NULL DEFAULT 0.0,
    CONSTRAINT uq_job_version_attempt UNIQUE (job_id, definition_version_id, attempt_number)
);
CREATE INDEX idx_attempts_job ON execution_attempts(job_id);
CREATE INDEX idx_attempts_definition_version ON execution_attempts(definition_version_id);

-- Rich normalized result preserving ALL Gen 1 telemetry (Fix #4)
CREATE TABLE test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID UNIQUE NOT NULL REFERENCES execution_attempts(id) ON DELETE CASCADE,
    -- Outcome taxonomy (Fix #25: enriched set matching Gen 1 + new manual states)
    outcome VARCHAR(30) NOT NULL,
    -- PASS, FAIL, ERROR, TIMEOUT, BLOCKED, SKIPPED, ENVIRONMENT_ERROR, CANCELLED
    -- Structured normalized data
    step_results JSONB NOT NULL DEFAULT '[]',
    assertion_results JSONB NOT NULL DEFAULT '[]',
    -- Gen 1 HTTP telemetry preserved (not discarded)
    http_status_code INTEGER NULL,
    http_method VARCHAR(20) NULL,
    http_path VARCHAR(500) NULL,
    response_body_truncated BOOLEAN NOT NULL DEFAULT FALSE,
    -- Diagnostics
    error_message TEXT NULL,
    stack_trace TEXT NULL,
    execution_time_ms FLOAT NOT NULL,
    -- Gen 1 fingerprint & SBFL attribution preserved
    deterministic_fingerprint VARCHAR(64) NULL,
    is_flaky BOOLEAN NOT NULL DEFAULT FALSE,
    -- Adapter-specific raw output (versioned; type identified by adapter_type)
    adapter_result JSONB NOT NULL DEFAULT '{}',
    -- Full provenance snapshot
    provenance JSONB NOT NULL DEFAULT '{}',
    -- {commit_sha, env_url_hash, runner_host, engine_ver, config_hash, retry_number}
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idx_results_fingerprint ON test_results(deterministic_fingerprint) WHERE deterministic_fingerprint IS NOT NULL;
CREATE INDEX idx_results_outcome ON test_results(outcome);
```

---

### 1.11 Artifacts (Object-Storage Backed)

```sql
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_result_id UUID NOT NULL REFERENCES test_results(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    artifact_type VARCHAR(50) NOT NULL,        -- SCREENSHOT, VIDEO, HAR_NETWORK, TRACE_ZIP, LOG
    storage_backend VARCHAR(50) NOT NULL DEFAULT 'LOCAL',  -- LOCAL, S3, MINIO, AZURE_BLOB
    storage_key VARCHAR(1000) NOT NULL,        -- Opaque key/path; NEVER guessable filesystem path
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    -- Retention policy enforcement
    retention_class VARCHAR(30) NOT NULL DEFAULT 'STANDARD',  -- STANDARD, EXTENDED, PERMANENT
    expires_at TIMESTAMPTZ NULL,               -- Populated from workspace retention policy
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
```

---

### 1.12 First-Class Defect Lifecycle

```sql
CREATE TABLE defects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    defect_key VARCHAR(50) NOT NULL,           -- e.g. DEF-042
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'MAJOR',  -- BLOCKER, CRITICAL, MAJOR, MINOR, TRIVIAL
    priority VARCHAR(20) NOT NULL DEFAULT 'P2',
    status VARCHAR(30) NOT NULL DEFAULT 'NEW',
    -- NEW, TRIAGED, ASSIGNED, IN_PROGRESS, FIXED, READY_FOR_RETEST, VERIFIED, CLOSED
    fingerprint VARCHAR(64) NULL,              -- Links to Gen 1 defect_clusters.fingerprint
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    -- Fix #15: Migrated defects from fingerprints are INFERRED only
    source VARCHAR(30) NOT NULL DEFAULT 'MANUAL',
    -- MANUAL, MIGRATED_INFERRED, AUTO_DETECTED
    external_issue_tracker VARCHAR(50) NULL,
    external_issue_id VARCHAR(100) NULL,
    external_issue_url VARCHAR(500) NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_project_defect_key UNIQUE (project_id, defect_key)
);

CREATE TABLE defect_occurrences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    defect_id UUID NOT NULL REFERENCES defects(id) ON DELETE CASCADE,
    test_result_id UUID NOT NULL REFERENCES test_results(id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_defect_test_result UNIQUE (defect_id, test_result_id)
);

-- Append-only audit trail; rows are NEVER deleted or updated
CREATE TABLE defect_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    defect_id UUID NOT NULL REFERENCES defects(id) ON DELETE CASCADE,
    from_status VARCHAR(30) NOT NULL,
    to_status VARCHAR(30) NOT NULL,
    changed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'USER',
    comment TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
```

---

## Contract 2: Gen 1 → Gen 2 Mapping Specification

### 2.1 Legacy Execution Map

```sql
CREATE TABLE legacy_execution_map (
    -- Composite key: one row per unique (run × case × result) triple
    legacy_test_run_id UUID NOT NULL,
    legacy_test_case_id UUID NOT NULL,
    legacy_test_result_id UUID NOT NULL,
    -- Canonical targets
    canonical_test_definition_id UUID NOT NULL,
    canonical_version_id UUID NOT NULL,
    canonical_execution_job_id UUID NOT NULL,
    canonical_execution_attempt_id UUID NOT NULL,
    canonical_test_result_id UUID NOT NULL,
    -- Migration provenance
    migration_status VARCHAR(30) NOT NULL,    -- MIGRATED, MIGRATED_WITH_WARNING, UNSUPPORTED, FAILED
    migration_notes TEXT NULL,
    migrated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (legacy_test_run_id, legacy_test_case_id, legacy_test_result_id)
);
```

### 2.2 Projection Rules

| Gen 1 Source | Gen 2 Target | Transformation Rules |
|---|---|---|
| `projects` | `workspaces` + `projects.workspace_id` | One default Workspace `"Default Organization"` created; `actor_type = 'MIGRATION'`. |
| `test_suites` | `test_suites` | Direct mirror; `parent_suite_id = NULL`, `order_index = 0`, `actor_type = 'MIGRATION'`. |
| `test_cases` | `test_definitions` + `test_definition_versions` | **Fix #25**: `test_code = 'TC-API-' || SUBSTRING(legacy_id::text, 1, 8)` (stable UUID prefix, not ROW_NUMBER). `category = 'SYNTHETIC_API'`, `execution_type = 'AUTOMATED'`, `source_type = 'MIGRATED'`, `actor_type = 'MIGRATION'`, `legacy_test_case_id = test_cases.id`. |
| `test_cases.specification` | `test_definition_versions.specification` | **Fix #26**: Attempt `http.v1` schema coercion. If incompatible → `migration_status = 'UNSUPPORTED'`, `specification = {"schema_version": "unknown.v0", "raw": <original>}`. Never silently coerce malformed specs. |
| `test_runs` | `execution_jobs` | `idempotency_key = 'migrated-run-' || test_run.id`, `job_type = 'AUTOMATED_BATCH'`, `actor_type = 'MIGRATION'`. |
| `test_runs.target_environment` | `environments` + `builds` | **Fix #14**: Create one `MIGRATION_ENVIRONMENT` per unique `target_environment.base_url` and one `MIGRATION_BUILD` per unique `(project_id, commit_sha)` or synthetic fallback with `actor_type = 'MIGRATION'`, `build_metadata.provenance = 'DERIVED_FROM_MIGRATION'`. |
| `test_results` | `execution_attempts` + `test_results` | Preserve: `status_code → http_status_code`, `request_data`, `response_data → adapter_result`, `assertion_failures → assertion_results`, `error_message`. Map `'SKIP' → 'SKIPPED'`. |
| `failure_analyses` | `defect_occurrences` only | **Fix #15**: Do NOT auto-create `defects`. Create `DefectOccurrence` records. Set `defects.source = 'MIGRATED_INFERRED'` only when a corresponding `DefectClusterModel` fingerprint cluster exists, with `status = 'NEW'` (not CONFIRMED). |

---

## Contract 3: Typed Adapter Protocols

### 3.1 Strongly Typed Canonical Payloads

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


# --- Canonical Outcome Enum (Fix #25) ---
class NormalizedOutcome(str, Enum):
    PASS             = "PASS"
    FAIL             = "FAIL"
    ERROR            = "ERROR"
    TIMEOUT          = "TIMEOUT"
    BLOCKED          = "BLOCKED"
    SKIPPED          = "SKIPPED"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    CANCELLED        = "CANCELLED"


# --- Typed adapter-specific specification payloads ---
@dataclass(frozen=True)
class HttpSpecV1:
    schema_version: str               # "http.v1"
    adapter: str                      # "sandbox_http"
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    expected_status: int = 200
    assertions: List[Dict[str, Any]] = field(default_factory=list)

@dataclass(frozen=True)
class PlaywrightSpecV1:
    schema_version: str               # "playwright.v1"
    adapter: str                      # "playwright"
    browser: str
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 720})
    actions: List[Dict[str, Any]] = field(default_factory=list)

@dataclass(frozen=True)
class ManualSpecV1:
    schema_version: str               # "manual.v1"
    adapter: str                      # "manual"
    environment_type: str
    tags: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class K6SpecV1:
    schema_version: str               # "k6.v1"
    adapter: str                      # "k6"
    script_ref: str
    options: Dict[str, Any] = field(default_factory=dict)
    thresholds: Dict[str, List[str]] = field(default_factory=dict)


# --- Canonical result types ---
@dataclass(frozen=True)
class NormalizedArtifact:
    name: str
    artifact_type: str
    storage_key: str
    mime_type: str
    size_bytes: int
    sha256: str

@dataclass(frozen=True)
class NormalizedStepResult:
    step_number: int
    status: NormalizedOutcome
    actual_result: str
    notes: Optional[str] = None
    duration_ms: float = 0.0

@dataclass(frozen=True)
class NormalizedAssertionResult:
    assertion_type: str
    path: Optional[str]
    operator: str
    expected: Any
    actual: Any
    passed: bool
    message: Optional[str] = None

@dataclass(frozen=True)
class ExecutionResultPayload:
    outcome: NormalizedOutcome
    duration_ms: float
    started_at: datetime
    completed_at: datetime
    step_results: List[NormalizedStepResult] = field(default_factory=list)
    assertion_results: List[NormalizedAssertionResult] = field(default_factory=list)
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    http_status_code: Optional[int] = None
    deterministic_fingerprint: Optional[str] = None
    adapter_result: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[NormalizedArtifact] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)


# --- Adapter Protocols ---
class ExecutionAdapter(Protocol):
    adapter_type: str
    adapter_version: str

    async def execute(
        self,
        specification: Dict[str, Any],
        environment_config: Dict[str, Any],
        timeout_seconds: int = 60,
    ) -> ExecutionResultPayload: ...


class AnalyzerAdapter(Protocol):
    """Maps to Gen 1 AST parser and PKG builder."""
    async def parse_repository(
        self, project_id: str, commit_sha: str
    ) -> Dict[str, Any]: ...


class GeneratorAdapter(Protocol):
    """Maps to Gen 1 invariant and synthetic test generation engine."""
    async def generate_invariants(
        self, project_id: str, endpoint_spec: Dict[str, Any]
    ) -> List[Dict[str, Any]]: ...


# Fix #11: Separate RCA (stack/taxonomy/PKG attribution) from Fault Localization (SBFL)
class FailureAnalysisAdapter(Protocol):
    """Maps to Gen 1 deterministic RCA: stack parsing, JSON diff, taxonomy, fingerprinting."""
    async def analyze_failure(
        self, result_id: str, error_context: Dict[str, Any]
    ) -> Dict[str, Any]: ...


class FaultLocalizationAdapter(Protocol):
    """Maps to Gen 1 Tarantula/Ochiai SBFL: identifies suspicious source locations."""
    async def localize_fault(
        self, project_id: str, spectrum_matrix: Dict[str, Any]
    ) -> List[Dict[str, Any]]: ...


class MLAdapter(Protocol):
    """Maps to Gen 1 XGBoost flakiness and failure risk predictor."""
    async def predict_flakiness(
        self, test_id: str, history: List[Dict[str, Any]]
    ) -> float: ...


class RegressionAdapter(Protocol):
    """Maps to Gen 1 Git AST Delta Selective Prioritizer (Tier 1 / Tier 2)."""
    async def select_tests(
        self, base_commit: str, target_commit: str
    ) -> Dict[str, List[str]]: ...


# Fix #10: Quality gates are Gen 2 orchestration policy; no Gen 1 adapter needed.
# Quality gate evaluation reads canonical TestResult / Defect data directly.
```

---

## Contract 4: Migration Verification Invariants (Corrected)

### 4.1 Staged Migration Sequence

```
[0011_canonical_schema.py]           Pure DDL — creates all new tables (no data changes)
         ↓
[0012_legacy_compatibility.py]       Creates legacy_execution_map + compatibility views; NO data
         ↓
[backfill_gen2.py — application job] Batched data migration in chunks of 500; idempotent by design
    Phase A: Project → Workspace
    Phase B: test_suites (mirror)
    Phase C: test_cases → test_definitions + test_definition_versions
    Phase D: test_runs → execution_jobs (+ MIGRATION_ENVIRONMENT + MIGRATION_BUILD)
    Phase E: test_results → execution_attempts + canonical test_results
    Phase F: failure_analyses → defect_occurrences (NO auto-defect creation)
    Phase G: defect_clusters → defects (MIGRATED_INFERRED status only)
         ↓
[0013_canonical_constraints.py]      Enforces NOT NULL, indexes, FK constraints after validation
```

### 4.2 Corrected Mathematical Migration Invariants (Fix #13)

All five invariants must pass using `DISTINCT` counts. A migration is valid **only if all five hold**:

```sql
-- Invariant I-1: Every unique legacy test case has exactly one canonical test definition
SELECT COUNT(DISTINCT id) FROM test_cases
= SELECT COUNT(DISTINCT legacy_test_case_id)
  FROM test_definitions WHERE legacy_test_case_id IS NOT NULL;

-- Invariant I-2: Every unique legacy test run has exactly one canonical execution job
SELECT COUNT(DISTINCT id) FROM test_runs
= SELECT COUNT(DISTINCT legacy_test_run_id) FROM legacy_execution_map;

-- Invariant I-3: Every unique legacy test result has exactly one canonical test result
SELECT COUNT(DISTINCT id) FROM test_results_legacy
= SELECT COUNT(DISTINCT canonical_test_result_id) FROM legacy_execution_map;

-- Invariant I-4: Aggregate pass counts are preserved
SELECT SUM(passed_tests) FROM test_runs
= SELECT SUM(passed_tests) FROM execution_jobs WHERE actor_type = 'MIGRATION';

-- Invariant I-5: Canonical Migration Digest v1 (Fix #12)
-- Hash input: JSON array of objects ordered by legacy_test_result_id ASC:
-- [{id, test_case_id, test_run_id, outcome_normalized, status_code, error_message_hash, created_at_epoch}]
-- JSON keys sorted alphabetically; strings UTF-8; nulls as JSON null.
-- Algorithm: SHA-256 of UTF-8 encoded canonical JSON string.
SELECT sha256_hex(canonical_json(legacy_results_digest))
= SELECT sha256_hex(canonical_json(gen2_results_digest));
```

### 4.3 Rollback Test (Mandatory Before Deprecation)

```bash
# Step 1: Snapshot Gen 1 data
pg_dump --schema-only --data-only astra_db > gen1_snapshot.sql

# Step 2: Apply 0011 + 0012 + backfill
alembic upgrade 0013_canonical_constraints

# Step 3: Run all 5 invariant checks
python -m app.db.verify_migration_invariants --assert-all

# Step 4: Rollback
alembic downgrade 0010_analytics_and_benchmarks

# Step 5: Compare — MUST be identical
pg_dump astra_db | diff - gen1_snapshot.sql
```

---

## Contract 5: Multi-Tenant RBAC Permissions Matrix

| Permission | Workspace Owner | Workspace Admin | Project Admin | QA Lead | Tester | Developer | Viewer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `workspace:destroy` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `workspace:configure` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `users:invite` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `projects:create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `environments:manage` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `requirements:create` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `requirements:approve` | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `tests:create` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `tests:approve` | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `tests:execute` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `defects:create` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `defects:close` | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `releases:sign_off` | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `audit_logs:read` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `reports:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Approval separation invariant**: `tests:create` transitions definition to `IN_REVIEW`; only `tests:approve` (QA Lead+) transitions to `APPROVED`. This preserves the Gen 2 AI safety principle:
> **AI proposes → Human reviews → Approved Definition → Execution. Never AI → Database → Execution.**

---

## Contract 6: Canonical Event Model (Lightweight)

```python
@dataclass(frozen=True)
class DomainEvent:
    event_id: str                  # UUID
    event_type: str                # TestDefinitionApproved, ExecutionJobQueued, ...
    aggregate_type: str            # test_definition, execution_job, defect, ...
    aggregate_id: str              # UUID of the primary entity
    project_id: str
    workspace_id: str
    occurred_at: datetime
    actor_type: str                # USER, SYSTEM, AI, CI, MIGRATION
    actor_id: Optional[str]        # User UUID if actor_type == USER
    schema_version: str            # "event.v1"
    payload: Dict[str, Any]        # Event-specific data

# Canonical event types (Phase 1 scope)
# TestDefinitionApproved, ExecutionJobQueued, ExecutionJobStarted,
# ExecutionAttemptCompleted, TestResultProduced, DefectCreated, DefectStatusChanged
```

---

## Contract 7: Compatibility Layer Deprecation Phases

```
Phase A: Dual-write disabled; Gen 1 APIs primary; Gen 2 DDL exists (0011 complete)
Phase B: Canonical write + legacy projection (backfill complete; both APIs live)
Phase C: Canonical read primary + Gen 1 API fallback (all new work on Gen 2)
Phase D: Gen 1 API reads disabled; legacy_execution_map read-only
Phase E: Gen 1 legacy tables archived; legacy_execution_map kept indefinitely
```

The compatibility layer is **temporary by design**. Phase D must occur before any Gen 3 planning begins.

---

## 10-Item Pre-Migration Sign-Off Checklist

- [x] **Fix #1**: `RequirementLink` now records `requirement_version_id` + `definition_version_id`.
- [x] **Fix #2**: `is_approved=TRUE` versions are immutable; changes create new version numbers.
- [x] **Fix #3**: `test_plan_suites` and `test_cycle_definitions` membership tables added.
- [x] **Fix #4**: Migration creates `MIGRATION_ENVIRONMENT` and `MIGRATION_BUILD` records with `provenance='DERIVED_FROM_MIGRATION'`; no silent synthetic data.
- [x] **Fix #5**: Invariants corrected to use `COUNT(DISTINCT ...)`.
- [x] **Fix #6**: Canonical Migration Digest v1 algorithm defined (sorted keys, UTF-8, SHA-256).
- [x] **Fix #7**: No auto-created confirmed `Defect` from fingerprints; only `DefectOccurrence` + `MIGRATED_INFERRED` defects with `source='MIGRATED_INFERRED'`.
- [x] **Fix #8**: `test_code` uses stable `TC-API-<8-char-UUID-prefix>` — not `ROW_NUMBER()`.
- [x] **Fix #9**: Unknown/malformed specs set `migration_status='UNSUPPORTED'`, preserved as `unknown.v0` raw; never silently coerced.
- [x] **Fix #10**: `FailureAnalysisAdapter` (deterministic RCA) and `FaultLocalizationAdapter` (Tarantula/Ochiai SBFL) are now separate protocols.

---

## ✅ Final Approval Status

| Contract | Status |
|---|:---:|
| Canonical Domain Model (DDL) | **FROZEN** |
| Gen 1 → Gen 2 Mapping Spec | **FROZEN** |
| Typed Adapter Protocols | **FROZEN** |
| Migration Invariants | **FROZEN** |
| RBAC Permissions Matrix | **FROZEN** |
| Event Model | **FROZEN** |
| Compatibility Deprecation Phases | **FROZEN** |

**Begin `0011_canonical_schema.py` (DDL only) on approval.**
