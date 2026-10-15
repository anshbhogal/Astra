# ASTRA Remediation Baseline Record

**Date:** 2026-10-15  
**Baseline Git Tag:** `astra-pre-hardening`  
**Git Commit SHA:** `55b761458ffe9d46560f7cb2be133e731022cc07`  

---

## 1. System Versions & Environment

| Component | Version / Identifier | Status |
| :--- | :--- | :--- |
| **Git Commit** | `55b761458ffe9d46560f7cb2be133e731022cc07` | Tagged `astra-pre-hardening` |
| **Alembic Migration** | `0014_automated_program_repair (head)` | Active Head |
| **PostgreSQL Container** | `postgres:16-alpine` (Container ID `a2daa270f126`) | Healthy |
| **Redis Container** | `redis:7-alpine` (Container ID `4252d739d983`) | Healthy |
| **Backend Container** | `astra-backend` (Python 3.11-slim) | Healthy |
| **Celery Container** | `astra-celery_worker` | Active |
| **Frontend Container** | `astra-frontend` (Node 20-alpine) | Active |

---

## 2. Test Execution & Build Baseline

### Backend Test Suite (`pytest tests/ -v`)
- **Total Tests Collected**: 41
- **Passed**: 32
- **Failed**: 9
- **Execution Time**: 46.41s
- **Warnings**: 28

#### Detailed Failure Breakdown:
1. `tests/test_rbac.py::test_developer_can_create_project`: Failed (returned 403 instead of 201 because project creation was restricted to ADMIN only).
2. `tests/test_projects.py::test_project_crud_lifecycle`: Failed (returned 403 on non-admin project create).
3. `tests/test_projects.py::test_create_project_invalid_url_fails`: Failed (returned 403).
4. `tests/test_auth.py::test_login_success`: Failed (returned 403 because approval gate `is_approved=False` was applied to self-registered accounts).
5. `tests/test_auth.py::test_register_admin_role_security_downgrade`: Failed (returned 400 rejection instead of older downgrade behavior).
6. `tests/test_execution.py::test_full_execution_engine_flow`: Failed (returned 403 on test run).
7. `tests/test_analyzer.py::test_trigger_project_analysis_flow`: Failed (returned 403 on analysis trigger).
8. `tests/test_advanced_generator.py::test_advanced_suite_generation_e2e`: Failed.
9. `tests/test_phase10_e2e_integration.py::test_phase10_full_e2e_analytics_and_benchmarks`: Failed.

### Frontend Production Build (`npm run build`)
- **Status**: PASSED (`✓ built in 15.20s`)
- **Output Artifacts**:
  - `dist/index.html`: 1.64 kB (gzip: 0.78 kB)
  - `dist/assets/index-BNAUiD16.css`: 64.99 kB (gzip: 12.02 kB)
  - `dist/assets/index-B7KMBJ3l.js`: 593.51 kB (gzip: 157.72 kB)
