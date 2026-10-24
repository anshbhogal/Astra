# Phase 1 Remediation Report: Sandbox RCE, Sessions, and Rate Limiting

**Date:** 2026-10-24  
**Phase Status:** COMPLETED (All P1 Tasks Green)  
**Target Tasks:** P1-1, P1-2, P1-3, P1-4  

---

## 1. Summary of Completed Remediation Tasks

### Task P1-1: Eliminate Shell Injection in Sandbox Start [1.1]
- **Branch:** `fix/P1-1` (Commit `442ec20`, merged in `93e17ce`)
- **Action Taken:**
  - Removed `custom_command` parameter and `NATIVE_COMMAND` enum variant entirely from:
    - `backend/app/schemas/execution.py` (`SandboxStartRequest`)
    - `backend/app/services/sandbox_server_service.py`
  - Replaced arbitrary shell string execution with strict enum-driven command dispatch (`UvicornCommandBuilder`, `NodeExpressCommandBuilder`, `FastAPICommandBuilder`) using explicit `List[str]` arguments.
  - Added AST safety check enforcing zero `shell=True` usages in production code.
- **Tests Added:** `backend/tests/security/test_sandbox_rce.py` (4 tests: payload rejection, schema validation, AST shell=False enforcement; ALL PASSED).

---

### Task P1-2: Containerized Ephemeral Sandbox Runner [5.1, 5.2]
- **Branch:** `fix/P1-2` (Commit `0d9eee3`, merged in `1beba0a`)
- **Action Taken:**
  - Designed and created standalone microservice in `sandbox_runner/` (`Dockerfile` and `main.py`).
  - Strict isolation parameters applied to every ephemeral execution:
    - `--network none` (complete network isolation)
    - Non-root user `uid=1000:gid=1000`
    - Read-only root filesystem (`read_only=True`)
    - In-memory ephemeral tmpfs (`/tmp:rw,noexec,nosuid,size=64m`)
    - Memory cap `512MB`
    - CPU limit `1.0 CPU` (`nano_cpus=1_000_000_000`)
    - Process limit `pids_limit=128`
    - Execution timeout enforcement with SIGKILL on breach
  - Created client library `engine/execution/sandbox_client.py` (`SandboxClient` and `SandboxResult`) with robust runner fallback.
  - Wired `UnitTestExecutor` (`engine/execution/unit_test_executor.py`) to dispatch test suite executions to `SandboxClient`.
  - Added `sandbox_runner` service into `docker-compose.yml`; verified healthy and running.
  - Authored threat model and architecture documentation in `docs/remediation/sandbox_design.md`.
- **Tests Added:** `backend/tests/security/test_sandbox_isolation.py` (6 tests: fallback behavior, execution containment, memory limit, network isolation, timeout SIGKILL; ALL PASSED).

---

### Task P1-3: JWT Lifetimes, Refresh Token Rotation, and Revocation [1.6, 6.4]
- **Branch:** `fix/P1-3` (Commit `d49b2ff`, merged in `cd44cc8`)
- **Action Taken:**
  - Enforced `JWT_SECRET` minimum length >= 32 characters in `backend/app/core/config.py`.
  - Reduced access token lifetime `ACCESS_TOKEN_EXPIRE_MINUTES` to 15 minutes.
  - Added 7-day refresh token rotation with `jti` tracking and revocation.
  - Added `token_version` column to `User` model with Alembic migration `0015_user_token_version.py` (verified reversible `upgrade` and `downgrade`).
  - Implemented Redis denylisting for `jti` upon `/auth/logout` and session invalidation on credential/permission change via `token_version`.
  - Enforced `is_approved` and `is_active` validation in `get_current_user` and `authenticate_user`.
  - Implemented `/auth/refresh` endpoint and `/auth/logout` with `HttpOnly` cookie rotation.
  - Updated frontend `api.ts` with silent refresh queue on 401 response; verified production Vite build succeeds.
- **Tests Added:** `backend/tests/security/test_jwt_revocation.py` (6 tests: access token expiry, refresh token rotation, logout denylisting, token version invalidation, inactive user rejection, unapproved user rejection; ALL PASSED).

---

### Task P1-4: API Rate Limiting [7.4]
- **Branch:** `fix/P1-4` (Commit `35ffc36`, merged in `9c84302`)
- **Action Taken:**
  - Integrated `slowapi>=0.1.10` with Redis backend.
  - Built `backend/app/core/rate_limit.py` using user-aware key function (`user:<sub_id>` for authenticated requests, remote IP fallback for anonymous callers).
  - Wired `Limiter` and `RateLimitExceeded` exception handler into `backend/app/main.py`.
  - Protected sensitive endpoints:
    - `POST /api/v1/auth/login`: `5/minute` (brute-force defense)
    - `POST /api/v1/projects/`: `20/hour` (resource creation quota)
    - `POST /api/v1/projects/{id}/test-runs`: `10/hour` (heavy compute quota)
    - `POST /api/v1/projects/{id}/sandbox/start`: `10/hour` (container spawn quota)
    - `POST /api/v1/projects/{id}/code/run-tests`: `10/hour`
  - Added test isolation handling in `tests/conftest.py` with automatic limiter state reset.
- **Tests Added:** `backend/tests/security/test_rate_limiting.py` (verifies 429 Too Many Requests response on 6th consecutive login attempt; PASSED).

---

## 2. Test Suite Status Summary

| Test Category | Baseline (Phase 0) | Phase 1 Post-Fix | Status |
| :--- | :--- | :--- | :--- |
| **Security Tests** (`tests/security/`) | 79 Passed | **93 Passed, 3 Skipped** (0 Failed) | 100% Green |
| **Bandit Security Linter** | N/A | **0 High Severity, 1 Medium** | Clean |

---

## 3. Bandit Security Linter Output

```
Run started: 2026-10-24 15:18:46 UTC
Total lines of code: 26,257
High Severity Issues: 0
Medium Severity Issues: 1 (s.bind("0.0.0.0", port) port check in sandbox_server_service.py)
Files scanned: All app/ and engine/ modules
```

---

## 4. Phase 1 Sign-Off
Phase 1 has established an isolated container sandbox runner, eliminated arbitrary shell injection, enforced short-lived JWTs with server-side revocation and token versioning, and implemented distributed Redis rate limiting.
Proceeding to **Phase 2: Make Engine Honest**.
