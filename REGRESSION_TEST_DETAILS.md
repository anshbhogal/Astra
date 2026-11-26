# ASTRA — Detailed Regression Test Documentation and Evidence Audit

**Document Version:** 2.1.0 (Final Reconciled Evidence Audit)  
**Audit Date:** November 23, 2026  
**Auditor:** ASTRA Engineering Assistant (Autonomous Verification Suite)  
**Target Environment:** Docker Container `astra_backend` (Linux x86_64, Python 3.11.17, pytest 9.1.1)  
**Suite Status:** **PASSED** (307 Passed, 3 Skipped, 0 Failed across 81 Distinct Test Files)  

---

## 1. Full Regression Suite Overview & Execution Records

This audit establishes the empirical evidence, exact numerical accounting, and concrete verification boundaries of the regression test suite executed following the Google Gemini single-provider consolidation and Automated Program Repair (APR) cleanup.

### 1.1 Execution Metadata & Reconciliation of Execution Records
Two separate test executions were conducted in the Docker container `astra_backend` to verify results and establish per-file statistics:

| Execution Metric | Run 1: Full Regression Run (Task 1898) | Run 2: Granular Per-File Audit Run (Task 1990) | Reconciled Status |
| :--- | :--- | :--- | :--- |
| **Exact Command** | `docker exec -e PYTHONPATH=/app astra_backend python -m pytest tests/ engine/tests/ -q` | `docker exec -e PYTHONPATH=/app astra_backend python /app/scratch/audit_test_suite.py` | Run 1 ran standard pytest CLI; Run 2 ran programmatic pytest with ResultCollector plugin. |
| **Execution Timestamp** | 2026-11-23 12:36:01 UTC (18:06:01 IST) | 2026-11-23 12:55:30 UTC (18:25:30 IST) | Run 1 established initial baseline; Run 2 captured per-file counts. |
| **Duration** | **264.82s (0:04:24)** | **260.19s (0:04:20)** | **Duration difference:** 4.63s (~1.7%). The underlying cause of this duration difference was not instrumented and remains **undetermined** (consistent with normal execution jitter). |
| **Docker Container** | `astra_backend` (`1d8cf5b02083`, image: `astra-backend`) | `astra_backend` (`1d8cf5b02083`, image: `astra-backend`) | Same running container instance. |
| **Python Version** | Python 3.11.17 (`/usr/local/bin/python`) | Python 3.11.17 (`/usr/local/bin/python`) | Identical interpreter. |
| **pytest Version** | pytest 9.1.1 (Plugins: `anyio-4.15.1`, `asyncio-1.4.1`, `pluggy-1.7.0`) | pytest 9.1.1 (Plugins: `anyio-4.15.1`, `asyncio-1.4.1`, `pluggy-1.7.0`, `ResultCollector`) | Identical test framework. |
| **Container Directory** | `/app` (Mounts host `./backend` to `/app`, `./engine` to `/app/engine`) | `/app` (Mounts host `./backend` to `/app`, `./engine` to `/app/engine`) | Identical mount topology. |
| **Total Collected Items** | **310** | **310** | Exactly reconciled. |
| **Passed Tests** | **307** | **307** | Exactly reconciled. |
| **Skipped Tests** | **3** | **3** | Exactly reconciled. |
| **Failed Tests** | **0** | **0** | Zero failures. |
| **Total Warnings** | **23** | **23** | Exactly reconciled. |

### 1.2 Path Discrepancy Resolution
* **Host Path:** `backend/tests/test_gemini_integration.py`
* **Container Path:** `/app/tests/test_gemini_integration.py` (pytest nodeid: `tests/test_gemini_integration.py`)
* **Resolution:** In `docker-compose.yml`, the host directory `./backend` is mounted directly to `/app` inside the `astra_backend` container. When pytest runs from `/app` with arguments `tests/ engine/tests/`, it discovers backend test files under relative path `tests/` and engine tests under `engine/tests/`. Therefore, `backend/tests/test_gemini_integration.py` on the host and `tests/test_gemini_integration.py` in the container refer to the **same single physical file**. It is counted exactly once in the inventory.

### 1.3 Test Inventory Summary
* **Distinct Test Files Collected:** **81 files** (39 files in `tests/`, 42 files in `engine/tests/`).
* **Total Collected Items:** **310 items** (307 passed, 3 skipped, 0 failed).

### 1.4 Verification of the Custom Audit Script (`scratch/audit_test_suite.py`)
Inspection of `scratch/audit_test_suite.py` confirms:
1. **Scope of Execution:** It executed all 310 collected items via `pytest.main(['tests/', 'engine/tests/', '-q', '--disable-warnings'], plugins=[collector])`.
2. **Environment & Configuration:** It executed in the same container (`astra_backend`), working directory (`/app`), and Python interpreter as Run 1.
3. **Parametrization Accounting:** It hooks into `pytest_runtest_logreport`, extracting the file path via `report.nodeid.split('::')[0]`. Every parametrized iteration reports its own `report.passed` or `report.skipped` event, meaning parametrized tests (such as the 81 items in `test_tenant_isolation.py`) are genuinely counted per item.
4. **Execution Status Accounting:** It increments `passed`, `failed`, and `skipped` directly from live pytest report objects (`when == 'call'` and `when in ('setup', 'teardown')`).
5. **Qualification:** Run 2 is qualified as a **separate audit execution** conducted at 18:25:30 IST to generate machine-readable per-file breakdowns, confirming identical aggregate statistics (307 passed, 3 skipped, 23 warnings) to Run 1.

---

## 2. Comprehensive Test File Inventory

The regression suite encompasses **81 distinct test files**. Below is the forensic accounting of every test file collected and executed, grouped across 16 subsystems. Every test file is categorized under exactly one subsystem.

### Subsystem Summary Table
| Subsystem Number & Name | File Count | Passed Items | Skipped Items | Failed Items | File-Associated Warnings |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 2.1 Authentication, Authorization & Security Hardening | 6 | 18 | 0 | 0 | 1 |
| 2.2 User Management, RBAC & Governance | 3 | 7 | 0 | 0 | 0 |
| 2.3 Projects, Database & Multi-Tenant Isolation | 4 | 87 | 0 | 0 | 0 |
| 2.4 Codebase Static Analysis & Knowledge Graphs | 4 | 4 | 0 | 0 | 0 |
| 2.5 AST Parsing, Diffing & Polyglot Capabilities | 4 | 10 | 0 | 0 | 0 |
| 2.6 Test Generation & Synthesis Engine | 6 | 12 | 0 | 0 | 0 |
| 2.7 Test Execution, Runner & Sandbox Isolation | 9 | 36 | 3 | 0 | 0 |
| 2.8 Defect Management & Failure Clustering | 3 | 5 | 0 | 0 | 0 |
| 2.9 Failure Analysis, Classification & Root Cause | 6 | 13 | 0 | 0 | 5 |
| 2.10 Automated Program Repair (APR) & Zero-Observed-Regression | 6 | 35 | 0 | 0 | 0 |
| 2.11 Google Gemini Single-Provider Integration | 1 | 9 | 0 | 0 | 0 |
| 2.12 Machine Learning & Test Prioritization (XGBoost) | 6 | 24 | 0 | 0 | 5 |
| 2.13 Selective Regression Engine | 5 | 6 | 0 | 0 | 2 |
| 2.14 CI/CD, GitHub Integration & Dispatching | 8 | 13 | 0 | 0 | 3 |
| 2.15 Code Studio & Developer Workbench | 4 | 7 | 0 | 0 | 2 |
| 2.16 Analytics, Reporting & System Health | 6 | 21 | 0 | 0 | 3 |
| **Total Subsystem Subtotals** | **81** | **307** | **3** | **0** | **21** |
| *Top-Level Framework Deprecation Warnings (Module-Level)* | — | — | — | — | **2** |
| **Reconciled Grand Total** | **81** | **307** | **3** | **0** | **23** |

---

### Detailed Per-Subsystem Inventories

#### 2.1 Authentication, Authorization & Security Hardening (6 files, 18 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_auth.py` | Registration, credential validation, login, profile retrieval, admin downgrade defense | 7 | 7 | 0 | 0 | 0 |
| `tests/security/test_auth_backdoor.py` | Verifies elimination of admin email bypass and unapproved registration backdoors | 2 | 2 | 0 | 0 | 0 |
| `tests/security/test_jwt_revocation.py` | JWT secret entropy (>=32 chars), 15-min TTL, token versioning, refresh cookie lifecycle | 6 | 6 | 0 | 0 | 1 |
| `tests/security/test_rate_limiting.py` | SlowAPI login rate limiting (blocks brute-force attempts after 5 failures) | 1 | 1 | 0 | 0 | 0 |
| `tests/security/test_port_exposure.py` | Docker compose inspection verifying database & internal ports are restricted to localhost | 1 | 1 | 0 | 0 | 0 |
| `tests/security/test_container_user.py` | Confirms container runs under dedicated non-root user (`appuser:1000`) | 1 | 1 | 0 | 0 | 0 |
| **Subtotal** | | **18** | **18** | **0** | **0** | **1** |

#### 2.2 User Management, RBAC & Governance (3 files, 7 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_rbac.py` | Role-Based Access Control matrix (Admin vs Developer vs Viewer permissions) | 4 | 4 | 0 | 0 | 0 |
| `tests/test_rbac_admin_flow.py` | Administrative user governance, approval lifecycle, and role assignment flows | 1 | 1 | 0 | 0 | 0 |
| `tests/test_soft_deletes.py` | Soft-deletion mechanics ensuring user/project deletion preserves audit history | 2 | 2 | 0 | 0 | 0 |
| **Subtotal** | | **7** | **7** | **0** | **0** | **0** |

#### 2.3 Projects, Database & Multi-Tenant Isolation (4 files, 87 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_projects.py` | Project CRUD lifecycle, repo URL validation, 404 handling | 3 | 3 | 0 | 0 | 0 |
| `tests/security/test_tenant_isolation.py` | Parameterized matrix (3 test functions $\times$ 27 endpoints) enforcing 401/403 isolation | 81 | 81 | 0 | 0 | 0 |
| `tests/test_database.py` | SQLAlchemy AsyncSession persistence and user-project relationship integrity | 1 | 1 | 0 | 0 | 0 |
| `tests/test_composite_indexes.py` | Verifies canonical PostgreSQL composite indexes declare and exist in database schema | 2 | 2 | 0 | 0 | 0 |
| **Subtotal** | | **87** | **87** | **0** | **0** | **0** |

#### 2.4 Codebase Static Analysis & Knowledge Graphs (4 files, 4 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_analyzer.py` | Background project static analysis dispatch and result aggregation | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_endpoint_extractor.py` | FastAPI/Flask/Django route decorators and HTTP method extractor | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_impact_analyzer.py` | Call graph reachability and package modification blast-radius calculation | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_knowledge_graph.py` | Code entity dependency graph construction (modules, classes, functions) | 1 | 1 | 0 | 0 | 0 |
| **Subtotal** | | **4** | **4** | **0** | **0** | **0** |

#### 2.5 AST Parsing, Diffing & Polyglot Capabilities (4 files, 10 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `engine/tests/test_python_ast_parser.py` | Python AST statement, symbol table, and import hierarchy extraction | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_polyglot_parsers.py` | JavaScript & TypeScript AST route and function parsing via Babel/tree-sitter fallback | 3 | 3 | 0 | 0 | 0 |
| `engine/tests/test_stack_parsers.py` | Multi-language runtime exception parsers (Python tracebacks, Node.js, Java, SQLState) | 4 | 4 | 0 | 0 | 0 |
| `engine/tests/test_ast_change_analyzer.py` | AST node-level diff mapping across Git commit snapshots | 2 | 2 | 0 | 0 | 0 |
| **Subtotal** | | **10** | **10** | **0** | **0** | **0** |

#### 2.6 Test Generation & Synthesis Engine (6 files, 12 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_advanced_generator.py` | End-to-end multi-endpoint synthetic test suite generation API | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_suite_generator.py` | Combinatorial test scenario builder and parameter permutation engine | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_boundary_generators.py` | Numeric edge cases, string overflow, unicode injection, and probe generators | 3 | 3 | 0 | 0 | 0 |
| `engine/tests/test_combinatorial.py` | All-pairs (pairwise) parameter reduction testing | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_schema_inferencer.py` | JSON Schema inference from observed request/response payloads | 2 | 2 | 0 | 0 | 0 |
| `engine/tests/test_unit_test_synthesizer.py` | AST-grounded pytest synthesizer with zero tautological assertions | 4 | 4 | 0 | 0 | 0 |
| **Subtotal** | | **12** | **12** | **0** | **0** | **0** |

#### 2.7 Test Execution, Runner & Sandbox Isolation (9 files, 39 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_execution.py` | Celery test execution task lifecycle, timeout handling, status tracking | 1 | 1 | 0 | 0 | 0 |
| `tests/test_phase3_hardening.py` | Real execution against live FastAPI fixtures, negative matrix, telemetry redaction | 6 | 6 | 0 | 0 | 0 |
| `tests/security/test_containerized_sandbox_lifecycle.py` | Ephemeral mock server container startup, health probe, RBAC, and auto-cleanup | 10 | 10 | 0 | 0 | 0 |
| `tests/security/test_sandbox_isolation.py` | SandboxClient isolation, timeout limits, live runner (3 raw docker SDK tests skipped) | 6 | 3 | 0 | 3 | 0 |
| `tests/security/test_sandbox_rce.py` | RCE prevention: command whitelist enforcement (422), path traversal blocks, shell=False | 4 | 4 | 0 | 0 | 0 |
| `engine/tests/test_httpx_runner.py` | HTTP execution runner error resilience for unreachable endpoints | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_assertion_evaluator.py` | Response assertion verification (status code, JSON schema, latency SLA) | 4 | 4 | 0 | 0 | 0 |
| `engine/tests/test_ssrf_protector.py` | SSRF defense: scheme validation, private IP/loopback blocking on external calls | 4 | 4 | 0 | 0 | 0 |
| `engine/tests/test_redactor.py` | Evidence redactor: Authorization headers, JWT tokens, connection strings, payloads | 3 | 3 | 0 | 0 | 0 |
| **Subtotal** | | **39** | **36** | **0** | **3** | **0** |

#### 2.8 Defect Management & Failure Clustering (3 files, 5 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `engine/tests/test_defect_clustering.py` | Failure fingerprinting and canonical SHA-256 cluster grouping | 2 | 2 | 0 | 0 | 0 |
| `engine/tests/test_semantic_clustering.py` | DBSCAN-based failure text normalization and semantic group isolation | 2 | 2 | 0 | 0 | 0 |
| `engine/tests/test_deduplicator.py` | Identical payload and duplicate test scenario pruning | 1 | 1 | 0 | 0 | 0 |
| **Subtotal** | | **5** | **5** | **0** | **0** | **0** |

#### 2.9 Failure Analysis, Classification & Root Cause (6 files, 13 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_failure_analysis_api.py` | Failure analysis REST endpoints, authorization, health probe | 2 | 2 | 0 | 0 | 0 |
| `tests/test_phase6_e2e_integration.py` | End-to-end failure localization, stacktrace parsing, and defect creation | 1 | 1 | 0 | 0 | 5 |
| `engine/tests/test_failure_classifier.py` | Rule-based failure classification (500 crash, database deadlock, auth 401, semantic) | 4 | 4 | 0 | 0 | 0 |
| `engine/tests/test_fault_localization.py` | Spectrum-based fault localization (origin statement vs caller context) | 2 | 2 | 0 | 0 | 0 |
| `engine/tests/test_root_cause_analyzer.py` | Deterministic root-cause extraction from tracebacks and local symbols | 2 | 2 | 0 | 0 | 0 |
| `engine/tests/test_json_diff_isolator.py` | Expected vs actual JSON response field-level difference isolation | 2 | 2 | 0 | 0 | 0 |
| **Subtotal** | | **13** | **13** | **0** | **0** | **5** |

#### 2.10 Automated Program Repair (APR) & Zero-Observed-Regression (6 files, 35 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `engine/tests/test_automated_program_repair.py` | AST pinpointing, 4 deterministic mutators, patch validator, regression gate, PR formatting | 18 | 18 | 0 | 0 | 0 |
| `tests/test_phase12_apr_api.py` | End-to-end APR job triggering via FastAPI router on synthetic defect | 1 | 1 | 0 | 0 | 0 |
| `tests/test_defect_apr_bridge.py` | FailureAnalysis-to-G2Defect bridge and PR authorization with honest 40-char commit SHA | 2 | 2 | 0 | 0 | 0 |
| `tests/security/test_repair_auth.py` | Formal RBAC and project authorization gate on APR trigger, candidates, and PR approval | 4 | 4 | 0 | 0 | 0 |
| `tests/security/test_repair_webhook.py` | GitHub PR merged webhook HMAC verification, idempotency, and defect auto-closure | 7 | 7 | 0 | 0 | 0 |
| `engine/tests/test_healing_safety_gate.py` | Operation allowlist/denylist enforcer, server crash rejection, status transition check | 3 | 3 | 0 | 0 | 0 |
| **Subtotal** | | **35** | **35** | **0** | **0** | **0** |

#### 2.11 Google Gemini Single-Provider Integration (1 file, 9 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_gemini_integration.py` | Provider config, secret masking, error handling, deterministic priority, offline honesty | 9 | 9 | 0 | 0 | 0 |
| **Subtotal** | | **9** | **9** | **0** | **0** | **0** |

#### 2.12 Machine Learning & Test Prioritization (XGBoost) (6 files, 24 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_phase7_e2e_integration.py` | End-to-end Phase 7 ML test prioritization pipeline | 1 | 1 | 0 | 0 | 5 |
| `engine/tests/test_prioritization_ml.py` | APFD calculation, heuristic baseline, XGBoost model train/predict, no lookahead leakage | 6 | 6 | 0 | 0 | 0 |
| `engine/tests/test_dataset_builder.py` | 7 historical features extraction, temporal splitting ($k < t$), data leakage validation | 4 | 4 | 0 | 0 | 0 |
| `engine/tests/test_flakiness_state_machine.py` | Flakiness Markov state machine (PASSING, FLAKY, QUARANTINED, HEALED) | 3 | 3 | 0 | 0 | 0 |
| `engine/tests/test_benchmark_apps.py` | 4 realistic benchmark microservices (Auth, Banking, Ecommerce, Student) & 50 injected faults | 7 | 7 | 0 | 0 | 0 |
| `engine/tests/test_benchmark_runner.py` | Benchmark runner ablation evaluation (Mode D vs Mode 0) and bug match states | 3 | 3 | 0 | 0 | 0 |
| **Subtotal** | | **24** | **24** | **0** | **0** | **5** |

#### 2.13 Selective Regression Engine (5 files, 6 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_phase8_e2e_integration.py` | End-to-end Phase 8 selective regression testing pipeline | 1 | 1 | 0 | 0 | 2 |
| `engine/tests/test_selective_selector.py` | Tier-1 / Tier-2 test selection partitioning based on modified endpoints | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_git_diff_parser.py` | Git unidiff parser extracting modified lines, hunks, renames, and deletions | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_safety_gate.py` | Full-suite trigger gate on database migration or shared utility changes | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_candidate_engine.py` | Regression candidate generator handling caller vs origin modifications | 2 | 2 | 0 | 0 | 0 |
| **Subtotal** | | **6** | **6** | **0** | **0** | **2** |

#### 2.14 CI/CD, GitHub Integration & Dispatching (8 files, 13 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_phase9_e2e_integration.py` | End-to-end Phase 9 CI/CD pull request webhook and comment pipeline | 1 | 1 | 0 | 0 | 2 |
| `tests/test_pr_dispatcher_honest.py` | AutonomousPRDispatcher verifying real Git commits and honest SHA generation | 4 | 4 | 0 | 0 | 0 |
| `tests/security/test_webhook_secret.py` | Rejection of insecure default webhook secrets and enforcement of custom HMAC keys | 2 | 2 | 0 | 0 | 0 |
| `engine/tests/test_hmac_validator.py` | Cryptographic HMAC-SHA256 signature verification utility | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_event_abstraction.py` | GitHub Webhook JSON event adapter for PR and push events | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_pr_commenter.py` | Markdown PR status comment formatter with regression report breakdown | 1 | 1 | 0 | 0 | 1 |
| `engine/tests/test_notification_dispatchers.py` | Slack & Email alert dispatchers with outbound SSRF defense | 2 | 2 | 0 | 0 | 0 |
| `engine/tests/test_quality_gate.py` | Pull request pass/block policy evaluator based on test pass thresholds | 1 | 1 | 0 | 0 | 0 |
| **Subtotal** | | **13** | **13** | **0** | **0** | **3** |

#### 2.15 Code Studio & Developer Workbench (4 files, 7 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_code_editor.py` | Code Studio file tree, file reading, and syntax-checked saving API | 1 | 1 | 0 | 0 | 0 |
| `tests/test_code_editor_async.py` | Asynchronous in-browser developer test execution with timeout containment | 2 | 2 | 0 | 0 | 0 |
| `tests/test_code_studio_git.py` | Code Studio branch switching, commit staging, and Git diff inspection | 2 | 2 | 0 | 0 | 2 |
| `tests/security/test_code_editor_security.py` | Path traversal prevention (`../`) and symlink escape defense in file editor | 2 | 2 | 0 | 0 | 0 |
| **Subtotal** | | **7** | **7** | **0** | **0** | **2** |

#### 2.16 Analytics, Reporting & System Health (6 files, 21 items)
| Test File Path | Subsystem / Module Purpose | Total | Passed | Failed | Skipped | Warnings |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_health.py` | System health (`/health`) and PostgreSQL/Redis readiness probes | 2 | 2 | 0 | 0 | 0 |
| `tests/test_existing_features.py` | SMTP email settings, Celery background worker dispatch, project CRUD | 5 | 5 | 0 | 0 | 0 |
| `tests/test_phase10_e2e_integration.py` | End-to-end analytics metrics aggregation, MTTR, and pass rate calculations | 1 | 1 | 0 | 0 | 2 |
| `engine/tests/test_report_generator.py` | PDF export, sanitized HTML reports, metrics aggregation, trend charts | 5 | 5 | 0 | 0 | 0 |
| `engine/tests/test_evaluation_matrix.py` | Comprehensive verification matrix covering 13 architectural categories | 1 | 1 | 0 | 0 | 0 |
| `engine/tests/test_phase5_intelligence.py` | Markdown/Gherkin SRS parsing, mapping scorer, prompt sanitizer, prompt injection guard | 7 | 7 | 0 | 0 | 1 |
| **Subtotal** | | **21** | **21** | **0** | **0** | **3** |

---

## 3. Security Test Suite Forensic Accounting

### 3.1 Correction of Claimed Test Counts
Previous documentation claimed *"over 150 dedicated security test cases across 13 test files"*. 
A forensic inspection of the actual test collection establishes that this was an unverified estimate. 

The actual count is **127 collected pytest test items**, generated from **49 distinct test function definitions** across the **13 security test files**:

| Security Test File Path | Test Function Definitions | Collected Pytest Items | Parameterization Mechanism |
| :--- | :---: | :---: | :--- |
| `tests/security/test_auth_backdoor.py` | 2 | 2 | Direct unit tests |
| `tests/security/test_code_editor_security.py` | 2 | 2 | Direct unit tests |
| `tests/security/test_container_user.py` | 1 | 1 | Direct unit test |
| `tests/security/test_containerized_sandbox_lifecycle.py` | 10 | 10 | Direct lifecycle integration tests |
| `tests/security/test_jwt_revocation.py` | 6 | 6 | Direct unit tests |
| `tests/security/test_port_exposure.py` | 1 | 1 | Direct compose inspection test |
| `tests/security/test_rate_limiting.py` | 1 | 1 | Direct integration test |
| `tests/security/test_repair_auth.py` | 4 | 4 | Direct RBAC authorization tests |
| `tests/security/test_repair_webhook.py` | 7 | 7 | Direct HMAC and replay tests |
| `tests/security/test_sandbox_isolation.py` | 6 | 6 | 3 direct passed tests, 3 direct skipped tests |
| `tests/security/test_sandbox_rce.py` | 4 | 4 | Direct AST and endpoint tests |
| `tests/security/test_tenant_isolation.py` | **3** | **81** | **Parameterized:** 3 test functions $\times$ 27 discovered project GET routes = 81 items |
| `tests/security/test_webhook_secret.py` | 2 | 2 | Direct secret validation tests |
| **Total Across 13 Files** | **49** | **127** | **124 passed, 3 skipped, 0 failed** |

### 3.2 Detail of Parameterized Tenant Isolation
In `tests/security/test_tenant_isolation.py`, the function `get_project_routes()` dynamically discovers all FastAPI routes with `{project_id}` in their path (27 endpoints total).
Three asynchronous test functions are parameterized over these 27 routes:
1. `test_tenant_isolation_unauthenticated` (27 items): Verifies HTTP 401 Unauthorized for requests without tokens.
2. `test_tenant_isolation_unassigned_user_blocked` (27 items): Verifies HTTP 403/404 for authenticated developers not assigned to the project.
3. `test_tenant_isolation_assigned_member_permitted` (27 items): Verifies assigned project members are permitted access.

$$3 \text{ test functions} \times 27 \text{ routes} = 81 \text{ collected test items}$$

---

## 4. Detailed Investigation of Skipped Sandbox Tests

All three skipped tests reside in `tests/security/test_sandbox_isolation.py`.

### 4.1 Exact Skip Condition in Source Code
In `tests/security/test_sandbox_isolation.py`, lines 5–22 define the helper `get_docker_client()`:

```python
try:
    import docker
    from docker.errors import DockerException
except ImportError:
    docker = None
    DockerException = Exception

def get_docker_client():
    if docker is None:
        pytest.skip("docker python library not installed")
    try:
        return docker.from_env()
    except DockerException:
        pytest.skip("Docker daemon not accessible from test runner environment")
```

### 4.2 Exact pytest Skip Report and Root Cause
When executed in `astra_backend` with `pytest -rs`, pytest records:
```text
SKIPPED [3] tests/security/test_sandbox_isolation.py:17: docker python library not installed
```
* **Triggered Condition:** Line 17 (`if docker is None: pytest.skip("docker python library not installed")`).
* **Actual Cause:** The `docker` Python library is **not installed** in the `astra_backend` container's Python environment (`ModuleNotFoundError: No module named 'docker'`).
* **Correction of Prior Claims:** Previous documentation attributed the skip to `/var/run/docker.sock` mount absence. The execution trace proves that execution never reached `docker.from_env()` or the Docker socket; it halted at the missing Python package check on line 17.

### 4.3 Analysis of Skipped Tests vs Other Executed Tests
| Skipped Test Function | Tested Invariant in Source Code | Other Tests in Suite Verifying Property | Status in Current Suite |
| :--- | :--- | :--- | :---: |
| `test_sandbox_network_isolation_blocks_egress` | Spawns container with `network_mode="none"`; attempts TCP socket connection to `8.8.8.8:53`; asserts failure. | **None.** No other test actively verifies network egress blockage. | **UNVERIFIED** |
| `test_sandbox_memory_bomb_contained_by_cgroups` | Spawns container with `mem_limit="512m"`; allocates 1GB in Python `bytearray`; asserts OOM termination or `MemoryError`. | **None.** No other test actively executes memory bomb allocation. | **UNVERIFIED** |
| `test_sandbox_fork_bomb_contained_by_pid_limits` | Spawns container with `pids_limit=128`; executes infinite `os.fork()`; asserts `BlockingIOError`/`OSError`. | **None.** No other test actively executes a fork bomb. | **UNVERIFIED** |

### 4.4 What IS Verified vs What Remains Unverified
* **Verified:** `test_sandbox_client_live_runner_execution` verified that `SandboxClient` successfully communicates with `http://sandbox_runner:8001/execute` over HTTP, and `test_containerized_sandbox_lifecycle.py` verified mock-server container startup and HTTP health checks.
* **Unverified:** Active kernel-level cgroup enforcement of 512MB memory quotas, PID limit termination under fork bombs, and physical network egress blockage (`network_mode="none"`) were **not executed** and remain **unverified** by direct test evidence.

---

## 5. Reconciled Warning Accounting and Asyncio Teardown Analysis

Pytest recorded exactly **23 warnings** during the regression run.

### 5.1 Exact Category Breakdown
The 23 warnings reconcile into three distinct technical categories:

1. **17 PytestCollectionWarnings:** Emitted during test discovery when pytest encounters domain model and dataclass classes prefixed with `Test` having `__init__` constructors:
   - `tests/test_phase10_e2e_integration.py` (1 warning): `TestRunStatus` (`app/models/domain.py:291`)
   - `tests/test_phase6_e2e_integration.py` (5 warnings): `TestSuite`, `TestCase`, `TestRunStatus`, `TestOutcome`, `TestType` (`app/models/domain.py`)
   - `tests/test_phase7_e2e_integration.py` (5 warnings): `TestSuite`, `TestCase`, `TestRunStatus`, `TestOutcome`, `TestType` (`app/models/domain.py`)
   - `tests/test_phase8_e2e_integration.py` (2 warnings): `TestSuite`, `TestCase` (`app/models/domain.py`)
   - `tests/test_phase9_e2e_integration.py` (2 warnings): `TestSuite`, `TestCase` (`app/models/domain.py`)
   - `engine/tests/test_phase5_intelligence.py` (1 warning): `TestGenerationStrategy` (`engine/generator/strategy.py:20`)
   - `engine/tests/test_pr_commenter.py` (1 warning): `TestSelectionDetail` (`engine/regression/selective_selector.py:12`)
   *Subtotal:* $1 + 5 + 5 + 2 + 2 + 1 + 1 = \mathbf{17 \text{ collection warnings}}$.

2. **3 Deprecation Warnings:**
   - `PendingDeprecationWarning` in `starlette/formparsers.py:12`: `Please use import python_multipart instead.` (Emitted during package import).
   - `PydanticDeprecatedSince20` in `app/schemas/intelligence.py:17`: `Support for class-based config is deprecated, use ConfigDict instead.` (Emitted during schema import).
   - `DeprecationWarning` in `httpx/_client.py:1859` during `tests/security/test_jwt_revocation.py::test_logout_denylists_jwt_and_clears_cookie`: `Setting per-request cookies=<...> is being deprecated`
   *Subtotal:* $1 + 1 + 1 = \mathbf{3 \text{ deprecation warnings}}$.

3. **3 Asyncio RuntimeWarnings:** Emitted during test session execution:
   - `RuntimeWarning` in `sqlalchemy/orm/context.py:2786` during `tests/test_code_studio_git.py::test_code_studio_git_lifecycle`: `coroutine 'AbstractConnection._send_packed_command' was never awaited`
   - `RuntimeWarning` in `sqlalchemy/orm/context.py:2786` during `tests/test_code_studio_git.py::test_code_studio_git_lifecycle`: `coroutine 'to_thread' was never awaited`
   - `RuntimeWarning` in `sqlalchemy/orm/loading.py:144` during `tests/test_phase10_e2e_integration.py::test_phase10_full_e2e_analytics_and_benchmarks`: `coroutine 'Connection._cancel' was never awaited`
   *Subtotal:* $2 + 1 = \mathbf{3 \text{ runtime warnings}}$.

$$\text{Total Reconciled Warnings} = 17 \text{ (Collection)} + 3 \text{ (Deprecation)} + 3 \text{ (Runtime)} = \mathbf{23}$$

### 5.2 Mapping Warnings to the Section 2 Subsystem Tables
In Section 2:
* **21 warnings** are associated directly with specific test files in the tables:
  - 17 PytestCollectionWarnings (across 7 test files).
  - 1 DeprecationWarning (in `test_jwt_revocation.py`).
  - 3 RuntimeWarnings (2 in `test_code_studio_git.py`, 1 in `test_phase10_e2e_integration.py`).
* **2 warnings** are top-level module/package import deprecations (`starlette/formparsers.py:12` and `app/schemas/intelligence.py:17`) that occur prior to test execution and are not attached to any single test file.

$$21 \text{ file-associated warnings} + 2 \text{ top-level import warnings} = \mathbf{23 \text{ total warnings}}$$

### 5.3 Qualified Asyncio Teardown Findings
Inspection of `tests/conftest.py` and the async fixture lifecycle establishes the following technical distinctions:
* **Observed RuntimeWarnings:** Three specific warnings captured by pytest: unawaited coroutines for `AbstractConnection._send_packed_command`, `to_thread`, and `Connection._cancel`.
* **Confirmed Warning Origin:** The stack traces confirm that these unawaited coroutine objects are created by `asyncpg` and SQLAlchemy's async engine driver (`sqlalchemy.ext.asyncio`).
* **Suspected Event-Loop Lifecycle Issue:** `tests/conftest.py` defines `event_loop` at session scope (`@pytest.fixture(scope="session")`), whereas pytest-asyncio strict mode uses function-scoped test loops by default (`asyncio_default_test_loop_scope=function`). It is suspected that function-scoped loops or sessions close while background connection cleanup tasks (such as socket cancellation commands during rollback/close) remain pending on another loop or are unawaited when the test coroutine exits.
* **Proven Fixture-Level Root Cause:** **Not proven.** The exact line in fixture teardown where connection draining fails has not been isolated with memory allocation profiling (`tracemalloc`). The issue remains a **suspected** lifecycle mismatch between session-scoped event loops and connection pool teardown.

---

## 6. Clarification of Google Gemini Verification (Mocked vs Live)

All dedicated Gemini integration tests reside in `tests/test_gemini_integration.py` (9 tests total).

### 6.1 Granular Test Classification
| Test Function Name | Test Modality | Real Components Executed | Mocked Components / Dependencies | Assertions Made |
| :--- | :--- | :--- | :--- | :--- |
| `test_gemini_configuration_defaults` | **In-Process Unit** | `settings` object | None | Asserts `GEMINI_MODEL` and `GEMINI_API_KEY` attributes exist and model is supported. |
| `test_gemini_provider_secret_redaction` | **In-Process Unit** | `GeminiProvider.__repr__()`, `__str__()` | None | Asserts raw key `AIzaSy...` is absent from string representations; `api_key=present`. |
| `test_factory_returns_gemini_provider` | **In-Process Unit** | `LLMProviderFactory` | None | Asserts factory exclusively instantiates `GeminiProvider`. |
| `test_gemini_missing_api_key_returns_graceful_envelope` | **In-Process Unit** | `GeminiProvider` | None | Asserts unconfigured provider returns structured envelope with diagnostic message. |
| `test_gemini_strips_markdown_code_fences` | **Mocked HTTP Unit** | `GeminiProvider.generate_structured()`, JSON parser | `httpx.AsyncClient.post` mocked with simulated Gemini JSON response wrapped in ` ```json ` | Asserts markdown fences are stripped and valid JSON is parsed into dictionary. |
| `test_gemini_rate_limit_http_429` | **Mocked HTTP Unit** | `GeminiProvider.generate_structured()` | `httpx.AsyncClient.post` mocked with HTTP 429 status code | Asserts rate limit error envelope returned; raw key not leaked in error text. |
| `test_gemini_network_timeout` | **Mocked HTTP Unit** | `GeminiProvider.generate_structured()` | `httpx.AsyncClient.post` mocked with `httpx.TimeoutException` | Asserts timeout error envelope returned cleanly. |
| `test_deterministic_first_repair_does_not_invoke_gemini` | **Engine Orchestration Unit** | `RepairJobService`, `NullSafetyGuardMutator`, `PatchValidator`, `SandboxExecutor` (local subprocess) | `GeminiProvider.generate_structured` mocked via `AsyncMock` | Asserts deterministic mutator generates patch; asserts `mock_gemini.generate_structured.assert_not_called()`. |
| `test_offline_failure_honesty_when_deterministic_fails` | **Engine Orchestration Unit** | `RepairJobService`, `PatchValidator` | `GeminiProvider` instantiated with empty key (`api_key=""`) | Asserts pipeline honestly returns `status="FAILED"`, 0 candidates. Zero mock fabrication. |

### 6.2 Header Authentication and URL Query Parameter Audit
* **Implementation Audit (`engine/intelligence/providers/gemini.py`):**
  Lines 80–84 set headers:
  ```python
  url = f"{self.base_url}/{self.model}:generateContent"
  headers = {
      "Content-Type": "application/json",
      "x-goog-api-key": self.api_key,
  }
  ```
  The implementation places the API key in the `x-goog-api-key` header and does not append it to the URL query string.
* **Test Suite Assertion Finding:**
  In `tests/test_gemini_integration.py`, the test `test_gemini_strips_markdown_code_fences` mocks `httpx.AsyncClient.post`, but **does NOT inspect `mock_post.call_args` to assert that `x-goog-api-key` was present in `headers` or that the URL was clean of key query parameters**. The test only verified that the parsed response matched expectations.
* **Live API Connectivity Finding:**
  **No live Gemini API request was executed during the test run.** All network requests were intercepted via `unittest.mock.patch` or evaluated in unconfigured/offline mode. Live network connectivity and live model inference against `generativelanguage.googleapis.com` remain **unverified** in this test suite.

---

## 7. Strengthened APR Evidence Descriptions and Modality Audit

### 7.1 Production APR Route Reconciliation
Inspection of the active FastAPI router in `backend/app/api/v1/repair.py` confirms that the production APR trigger endpoint is:
$$\mathbf{POST\ /api/v1/repair/defects/\{defect\_id\}/trigger}$$
(Defined on line 147 as `@router.post("/defects/{defect_id}/trigger", response_model=RepairJobResponse, status_code=status.HTTP_201_CREATED)` with prefix `/repair`). Any prior references to `/api/v1/repair/defects/{defect_id}/repair` were planning document discrepancies and are resolved to this verified route.

### 7.2 APR Test Suite Inventory and Execution Modality
| Test File Path | Tests | Real Components Executed | Mocked / Synthetic Elements | Database Used | Sandbox Modality |
| :--- | :---: | :--- | :--- | :--- | :--- |
| `engine/tests/test_automated_program_repair.py` | 18 | `ASTPinpointer`, `PatchValidator`, 4 mutators, `ZeroObservedRegressionGate`, `SandboxExecutor` | None (pure Python unit tests on hardcoded string snippets) | **None** (in-memory) | Ephemeral directory via local subprocess |
| `tests/test_phase12_apr_api.py` | 1 | FastAPI router (`POST /defects/{defect_id}/trigger`), `RepairJobService`, `NullSafetyGuardMutator`, `PatchValidator`, `SandboxExecutor` | Synthetic defect snippet created in `tempfile.mkdtemp()`; test commands are dummy shell commands: `python -c "import sys; sys.exit(0)"` | **In-memory SQLite** (via `conftest.py` fixture) | Local subprocess shell in temp directory. **No Docker sandbox used.** |
| `tests/test_defect_apr_bridge.py` | 2 | `_get_or_sync_defect`, `RepairJobService`, `NullSafetyGuardMutator`, `SandboxExecutor`, PR authorization | Synthetic defect snippet created in `tempfile.mkdtemp()`; dummy shell commands: `python -c "import sys; sys.exit(0)"` | **In-memory SQLite** (via `conftest.py` fixture) | Local subprocess shell in temp directory. **No Docker sandbox used.** |
| `tests/security/test_repair_auth.py` | 4 | FastAPI router RBAC permission checks (`get_current_user`, `UserRole`) | Pure HTTP endpoint test; repair execution bypassed on 401/403 tests | **In-memory SQLite** | None |
| `tests/security/test_repair_webhook.py` | 7 | HMAC-SHA256 signature validator, webhook controller, defect status transition | Mocked GitHub webhook payloads; real database updates | **In-memory SQLite** | None |
| `engine/tests/test_healing_safety_gate.py` | 3 | Allowlist/denylist rules, status validator | Pure in-memory unit tests | **None** | None |
| `tests/test_pr_dispatcher_honest.py` | 4 | `AutonomousPRDispatcher`, local Git CLI commands (`git commit`, `git rev-parse`) | GitHub REST API network requests mocked (`POST /repos/.../pulls`) | **None** | Local git repo on host/container |

### 7.3 Detailed Analysis of Live Repair Execution
In `tests/test_phase12_apr_api.py` and `tests/test_defect_apr_bridge.py`:
1. **Production Code Executed:** The FastAPI route `/api/v1/repair/defects/{defect_id}/trigger` executes genuine production logic:
   - Fetches or bridges the defect.
   - Evaluates `RepairEligibilityPolicy`.
   - Creates a temporary working directory via `tempfile.mkdtemp(prefix="astra_repair_repo_")`.
   - Generates minimal target source code for the defect.
   - Executes `RepairJobService.execute_repair()`.
   - Invokes `NullSafetyGuardMutator` to generate AST-safe null guards or division guards.
   - Validates diff syntax and scope with `PatchValidator`.
   - Runs `SandboxExecutor.run_test_command()` via `asyncio.create_subprocess_shell`.
   - Computes ranking score via `ZeroObservedRegressionGate`.
   - Persists genuine `G2RepairCandidate` and `G2RepairVerification` records in the database.
2. **Synthetic Boundaries:**
   - The test commands supplied are minimal placeholder shell commands: `python -c "import sys; sys.exit(0)"`.
   - The repository under repair is an ephemeral temporary folder containing a 3-line Python function, not a realistic multi-file repository with existing test suites.
   - `SandboxExecutor` executes commands as local subprocesses on the container filesystem; it does not dispatch to the isolated `astra_sandbox_runner` container.
   - External Gemini LLM synthesis is never invoked during these tests because the deterministic mutator succeeds first.

### 7.4 Status of Live End-to-End Repair
**A complete live repair execution on an actual multi-file application repository—featuring live Gemini LLM patch synthesis, execution inside the isolated `astra_sandbox_runner` container, and verification against an existing multi-test regression suite—has NOT been executed and remains UNVERIFIED in this test suite.**

---

## 8. Regression Comparison (Before vs After Consolidation)

| Metric | Baseline Before Consolidation | Current Baseline After Consolidation | Delta | Explanation |
| :--- | :---: | :---: | :---: | :--- |
| **Total Collected Items** | 301 | **310** | **+9** | 9 new dedicated integration tests added in `tests/test_gemini_integration.py`. |
| **Passed Tests** | 298 | **307** | **+9** | All 9 Gemini integration tests passed cleanly. |
| **Failed Tests** | 0 | **0** | **0** | Zero regressions introduced across existing backend or engine modules. |
| **Skipped Tests** | 3 | **3** | **0** | Identical 3 raw Docker SDK tests skipped in `test_sandbox_isolation.py`. |
| **Distinct Test Files** | 80 | **81** | **+1** | Added `tests/test_gemini_integration.py`. Purged `engine/intelligence/providers/ollama.py`. |
| **Total Warnings** | 23 | **23** | **0** | Identical 17 collection warnings, 3 deprecation warnings, and 3 async runtime warnings. |
| **Total Duration** | ~255s | **264.82s** | +9.8s | Added runtime from 9 Gemini integration tests and real repair service execution. |

### Subsystem Verification Impact
1. **Ollama Dead Code Purge:** `engine/intelligence/providers/ollama.py` was deleted. All references in `factory.py`, `capabilities.py`, `schemas/intelligence.py`, and `LLMConfigDrawer.tsx` were purged. Zero test failures resulted, confirming Ollama was completely uncalled at runtime.
2. **APR Mock Elimination:** `backend/app/api/v1/repair.py` previously fabricated candidate objects and hardcoded 18/18 test pass results. It now calls `RepairJobService.execute_repair()`, `PatchValidator`, `SandboxExecutor`, and `ZeroObservedRegressionGate`, saving genuine records to `g2_repair_candidates` and `g2_repair_verifications`.
3. **Database Integrity:** Existing tests in `test_soft_deletes.py`, `test_composite_indexes.py`, and `test_database.py` continue to pass with zero schema or query regressions.

---

## 9. Verification Limitations

To maintain absolute scientific honesty, the table below explicitly separates what has been verified by concrete execution evidence from what remains unverified.

| Area | Verified Facts (Supported by Concrete Execution Evidence) | Remaining Unverified Properties (Explicitly Not Verified) |
| :--- | :--- | :--- |
| **Gemini LLM Provider** | 1. Provider defaults to `gemini-1.5-flash` and reads `GEMINI_API_KEY` from environment.<br>2. Secrets are redacted from `repr()` and `str()`.<br>3. Factory returns `GeminiProvider` exclusively.<br>4. Unconfigured provider reports clean error envelope.<br>5. Markdown fences (````json ... ````) are stripped cleanly.<br>6. Simulated HTTP 429 and network timeouts return error envelopes without crashes.<br>7. Offline repair pipeline honestly reports `status="FAILED"` without fabricating fake candidates. | 1. **Live Gemini inference:** No live authenticated API request was made to `generativelanguage.googleapis.com`.<br>2. **Header assertion:** The test suite does not explicitly assert that `x-goog-api-key` is present in `mock_post.call_args` or that the URL is clean of credentials. |
| **Automated Program Repair (APR)** | 1. Hardcoded candidates and fake 18/18 test reports in `repair.py` are completely eliminated.<br>2. `RepairJobService`, `NullSafetyGuardMutator`, `PatchValidator`, `SandboxExecutor`, and `ZeroObservedRegressionGate` execute genuine production code.<br>3. Honest 40-character commit SHAs are generated.<br>4. Verification results are persisted to the database.<br>5. Closed-loop GitHub webhook HMAC validation and defect auto-closure work correctly. | 1. **Live repository repair:** Full repair execution against a realistic multi-file repository with an existing test suite has not been performed.<br>2. **Live LLM synthesis:** Live patch generation via Gemini LLM has not been executed; tested repairs were handled by deterministic mutators. |
| **Container Sandbox Isolation** | 1. `SandboxClient` fallback execution works.<br>2. `SandboxClient` timeout containment triggers exit code 124 on timeout.<br>3. `SandboxClient` can communicate over HTTP with live `astra_sandbox_runner`.<br>4. Mock server container startup, health probe, and shutdown lifecycle verified over HTTP. | 1. **Raw Docker SDK tests:** 3 tests in `test_sandbox_isolation.py` were skipped because `docker` python library is not installed.<br>2. **Active cgroup containment:** Physical kernel memory limit enforcement (512MB OOM termination), PID limits (fork bomb containment), and network egress blocking (`network_mode="none"`) are unverified by active test execution. |
| **Security & Tenancy** | 1. 124 active security test items passed.<br>2. Parameterized multi-tenant matrix enforces 401/403 across 27 project GET endpoints.<br>3. JWT revocation, 15-minute TTL, token versioning, and rate limiting function correctly.<br>4. Code editor path traversal and symlink escapes are blocked. | 1. **Security test item total:** 127 items collected across 13 files (not 150 as previously claimed). |
| **Test Harness & Lifecycle** | 1. 307 tests passed cleanly across 81 distinct files in 264.82s.<br>2. 17 PytestCollectionWarnings represent expected skips of domain model classes prefixed with `Test`. | 1. **Async fixture teardown:** 3 `RuntimeWarning: coroutine was never awaited` warnings indicate suspected lifecycle mismatches in `tests/conftest.py` between session-scoped event loops and connection pool teardown. |

---

## 10. Audit Conclusion

The regression test suite demonstrates that ASTRA's consolidation to Google Gemini as its single external LLM provider, the complete removal of Ollama, and the elimination of hardcoded repair candidate fabrication were executed without breaking any existing system functionality.

All numerical claims in this document reconcile directly with pytest 9.1.1 collection and execution logs:
* **81 distinct test files** (Sum of all 16 subsystem file counts: $6+3+4+4+4+6+9+3+6+6+1+6+5+8+4+6 = \mathbf{81}$)
* **310 total collected items**
* **307 passed tests**
* **3 skipped tests**
* **0 failed tests**
* **23 warnings** ($17 \text{ Collection} + 3 \text{ Deprecation} + 3 \text{ Runtime} = 23$)
* **127 security test items across 13 security test files**

Where live API inference or physical container cgroup containment has not been directly executed by the test suite, it is explicitly classified as **Unverified** above.
