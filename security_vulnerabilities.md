# ASTRA Backend — Full Security Audit Report

**Auditor**: Antigravity AI  
**Date**: 2026-10-11  
**Scope**: All backend Python source, engine modules, tasks, DB migrations, Docker config, and `.env`  
**Verdict**: ⚠️ **7 Critical · 6 High · 5 Medium · 4 Low** vulnerabilities found

---

## 🔴 CRITICAL Vulnerabilities

---

### CRIT-1 — Hardcoded Authentication Bypass in Production Auth Service
**File**: [`auth_service.py:53-55`](file:///d:/Astra/backend/app/services/auth_service.py#L53-L55)  
**Risk**: Account Takeover · Privilege Escalation

```python
# VULNERABLE CODE
if not valid_password and user.email == "admin@astra.local" and payload.password in ("Admin123!", "Password123!"):
    valid_password = True
```

**Issue**: A hardcoded plaintext password bypass exists in the production authentication flow. Any attacker who discovers the admin email (`admin@astra.local` — which is exposed in the frontend source code and the `.env` seed) can log in as ADMIN **without knowing the actual Argon2 hashed password**. This completely nullifies the Argon2 password hashing and constitutes a hard backdoor.

**Additionally**: The `auth.py` login schema `UserLogin` auto-maps the shorthand `"admin"` username to `"admin@astra.local"` (line 35), making this bypass trivially discoverable.

**Fix**:
```python
# REMOVE the entire bypass block. Never hardcode credentials.
# Use a proper seed migration that hashes passwords via get_password_hash() at DB seed time.
# Remove the shorthand username mapping from UserLogin validator.
```

---

### CRIT-2 — Weak & Hardcoded JWT Secret with Insecure 7-Day Expiry
**Files**: [`config.py:25-29`](file:///d:/Astra/backend/app/core/config.py#L25-L29), [`.env:28`](file:///d:/Astra/.env#L28)  
**Risk**: Token Forgery · Session Hijacking

```python
# config.py - VULNERABLE: weak default secret committed to code
JWT_SECRET: str = Field(default="super_secure_astra_jwt_secret_key_change_in_production_2026")
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
```

**Issues**:
1. The JWT secret is a **guessable string** baked into the source code. Anyone with repo access can forge tokens.
2. The `.env` file uses the **same weak secret** — if `.env` is leaked (it IS tracked in the repo currently — see CRIT-6), attackers can forge JWTs for any user.
3. **7-day JWT expiry** with no refresh token mechanism means stolen tokens remain valid for 168 hours. The `.env` also sets `ACCESS_TOKEN_EXPIRE_MINUTES=60` (1 hour) while config.py defaults to 7 days — a **silent discrepancy** that creates confusion about the actual running value.
4. JWT tokens have **no JTI (JWT ID) claim** — there is **no token revocation** mechanism. Compromised tokens cannot be invalidated.

**Fix**:
```python
# Generate secret: python -c "import secrets; print(secrets.token_hex(64))"
# Enforce in config.py with a startup validator:
@field_validator("JWT_SECRET")
def validate_jwt_secret_strength(cls, v: str) -> str:
    if len(v) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters")
    if "change_in_production" in v.lower():
        raise ValueError("JWT_SECRET is using the default placeholder. Set a real secret.")
    return v

# Reduce expiry to 60 minutes. Add a separate refresh token mechanism.
# Add JTI claim and a Redis blocklist for revocation.
```

---

### CRIT-3 — Fake Notification Channel "Encryption" (No Real Crypto)
**File**: [`cicd_service.py:161-163`](file:///d:/Astra/backend/app/services/cicd_service.py#L161-L163)  
**Risk**: Credential Exposure · Webhook URL Leakage

```python
# VULNERABLE — Not encryption. Just a string prefix.
encrypted_target = f"enc_v1:{target_url}"
```

**Issue**: The `NotificationChannelModel.encrypted_target_url` column in the database stores **plaintext webhook URLs** (Slack, MS Teams, Email) with only the prefix `enc_v1:` prepended. The `_mask_target_url()` method un-prefixes and reads the raw URL. Anyone with database read access — including a SQL injection attacker, a misconfigured DB backup, or a rogue admin — gets full webhook URLs in plaintext. These URLs are secrets (Slack incoming webhook URLs grant full message posting capability).

**Fix**: Use real symmetric encryption with a server-side key from Vault/KMS:
```python
from cryptography.fernet import Fernet
# Key stored in Vault; never in .env or DB
cipher = Fernet(settings.NOTIFICATION_ENCRYPTION_KEY)
encrypted_target = cipher.encrypt(target_url.encode()).decode()
```

---

### CRIT-4 — SSRF via DNS Rebinding (Time-of-Check/Time-of-Use on IP Resolution)
**File**: [`ssrf_protector.py:60-77`](file:///d:/Astra/engine/security/ssrf_protector.py#L60-L77)  
**Risk**: SSRF to Internal Network / Cloud Metadata

```python
# VULNERABLE: DNS resolved once at validation time. Not pinned for the actual request.
addr_info = socket.getaddrinfo(hostname, None)
```

**Issue**: The SSRF check resolves DNS during `SSRFProtector.validate_url()` but the actual HTTP request in `httpx_runner.py` re-resolves DNS independently. An attacker can configure a domain to return a safe public IP during validation and a private/metadata IP (`169.254.169.254`) during the actual request (**DNS rebinding attack**).

**Additionally**: `LOCAL_SANDBOX` mode allows any hostname starting with `"test"`, `"astra"`, `"backend"` etc. (line 57). An attacker could register `backend.evil.com` and bypass the allowlist.

**Fix**:
```python
# After validation, pin the resolved IPs:
# Pass resolved_ip directly to httpx instead of re-resolving the hostname:
async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport()) as client:
    # Use httpx's custom transport to inject pre-resolved IP
    # Or: use the ip directly in the URL, set Host header manually

# Fix the allowlist prefix match to require exact hostnames, not prefix:
EXACT_SANDBOX_HOSTS = {"localhost", "127.0.0.1", "backend", "testserver"}
if hostname.lower() in EXACT_SANDBOX_HOSTS:
    return True, hostname
```

---

### CRIT-5 — GIT_SSL_NO_VERIFY Globally Disables TLS Certificate Validation
**File**: [`repo_cloner.py:42`](file:///d:/Astra/engine/analyzer/repo_cloner.py#L42)  
**Risk**: Man-in-the-Middle Attack on Git Clone · Code Injection

```python
# VULNERABLE: Disables TLS verification for ALL git operations
clone_env["GIT_SSL_NO_VERIFY"] = "true"
```

**Issue**: Setting `GIT_SSL_NO_VERIFY=true` disables TLS certificate verification for every `git clone` operation. This enables a MITM attacker on the network path to substitute the repository content with malicious code. Since the cloned code is then **statically parsed and executed** by the analysis engine, this is a direct code injection vector into the analysis pipeline.

**Fix**:
```python
# Remove this line entirely. Let git use the system CA bundle.
# If self-signed certs are needed in dev, use GIT_SSL_CAINFO to point to the cert.
del clone_env["GIT_SSL_NO_VERIFY"]
```

---

### CRIT-6 — `.env` File Containing Production Credentials Not Tracked in `.gitignore` Correctly
**File**: [`.gitignore:8`](file:///d:/Astra/.gitignore#L8), [`.env`](file:///d:/Astra/.env)  
**Risk**: Secret Exfiltration via Version Control

**Issue**: While `.env` is listed in `.gitignore`, the `.env` file is **present in the repository directory** with:
- `POSTGRES_PASSWORD=astra_secret_password`
- `JWT_SECRET=super_secure_astra_jwt_secret_key_change_in_production_2026`
- `DATABASE_URL` with embedded credentials

If this was ever committed before the `.gitignore` rule was added, or if any developer runs `git add -f .env`, these secrets are permanently in git history. The presence of a committed `.env.example` alongside a `.env` with real (not example) values compounds this risk.

**Fix**:
```bash
# Verify .env is not tracked:
git ls-files .env  # Must return nothing

# If it was ever tracked:
git rm --cached .env
git filter-branch or BFG Repo Cleaner to purge history

# .env should contain only placeholder values.
# Real secrets must come from environment injection in CI/CD or a secrets manager.
```

---

### CRIT-7 — `failure_analysis.py` Missing Project Ownership Check (IDOR Vulnerability)
**File**: [`failure_analysis.py:22-31`](file:///d:/Astra/backend/app/api/v1/failure_analysis.py#L22-L31)  
**Risk**: Insecure Direct Object Reference · Cross-Tenant Data Leakage

```python
# VULNERABLE: Only checks project exists, NOT that current_user owns it
async def _verify_project_access(project_id: uuid.UUID, db: AsyncSession) -> Project:
    stmt = select(Project).where(Project.id == project_id)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(...)
    return project  # No ownership check!
```

**Issue**: The `_verify_project_access` helper in `failure_analysis.py` accepts no `current_user` parameter. Any authenticated user can call:
- `POST /projects/{any_project_id}/runs/{run_id}/failure-analysis/analyze`
- `GET /projects/{any_project_id}/runs/{run_id}/failure-analysis`
- `GET /projects/{any_project_id}/defects`

…and read or trigger failure analysis for **any project in the system**, regardless of who owns it. This is a classic IDOR (Insecure Direct Object Reference) vulnerability.

**Fix**:
```python
# Same pattern as project_service.py and cicd.py
async def _verify_project_access(project_id: uuid.UUID, current_user: User, db: AsyncSession) -> Project:
    project = ...
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")  # 404 to prevent enumeration
    return project

# All 3 endpoints must pass current_user to this helper.
```

---

## 🟠 HIGH Vulnerabilities

---

### HIGH-1 — Unhandled Exception Leaks Stack Traces in HTTP 500 Responses
**File**: [`main.py:50-55`](file:///d:/Astra/backend/app/main.py#L50-L55)  
**Risk**: Information Disclosure · Internal Path/Version Exposure

```python
# VULNERABLE: Returns str(exc) in the HTTP response
return JSONResponse(
    content={"detail": "An internal server error occurred.", "error": str(exc)},
)
```

**Issue**: `str(exc)` can contain file paths, internal class names, database query fragments, or connection strings (e.g., `sqlalchemy.exc.OperationalError: (asyncpg.exceptions._base.UnknownPostgresError) ... url=postgresql+asyncpg://astra_user:astra_secret_password@...`). This provides attackers with reconnaissance data.

**Fix**: Never return `str(exc)` to clients. Log it server-side only:
```python
return JSONResponse(
    status_code=500,
    content={"detail": "An internal server error occurred."}
    # Error details are in server logs only, never in the response
)
```

---

### HIGH-2 — `SSL verify=False` Default on All HTTP Test Execution
**File**: [`target_env.py:18`](file:///d:/Astra/engine/models/target_env.py#L18), [`httpx_runner.py:49`](file:///d:/Astra/engine/executor/httpx_runner.py#L49)

```python
verify_ssl: bool = False  # DEFAULT — SSL disabled for all environments
httpx.AsyncClient(verify=config.verify_ssl)  # verify=False for all requests
```

**Issue**: SSL verification is **off by default** for all HTTP test execution. When ASTRA tests a staging or production endpoint over HTTPS, it does not validate the server's TLS certificate. This enables MITM attacks against the target and means ASTRA's test results may be produced against a spoofed server.

**Fix**: Change default to `True`. Provide an explicit `allow_insecure: bool = False` override for local dev:
```python
verify_ssl: bool = True  # Safe default
```

---

### HIGH-3 — No Rate Limiting on Authentication or Any API Endpoint
**Files**: All API routers  
**Risk**: Brute Force · Credential Stuffing · DoS

**Issue**: There is **zero rate limiting** across the entire API. No `slowapi`, `fastapi-limiter`, or Nginx rate limit configuration exists. This means:
- `/auth/login` is open to unlimited brute-force password attempts
- `/auth/register` can be used for email enumeration spam  
- `/projects/{id}/analyze` can be spammed to exhaust Celery workers
- Benchmark `/run` endpoint can be triggered continuously (computationally expensive)

**Fix**:
```python
# Install slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)

@router.post("/login")
@limiter.limit("10/minute")  # Max 10 login attempts per minute per IP
async def login(...):
```

---

### HIGH-4 — `docker-compose.yml` Mounts Entire Codebase as Writable Volume
**File**: [`docker-compose.yml:54-58`](file:///d:/Astra/docker-compose.yml#L54-L58)

```yaml
volumes:
  - ./backend:/app      # Entire backend mounted writable
  - ./engine:/app/engine
  - ./ml:/app/ml
  - ./scratch:/app/scratch
```

**Issue**: All source code directories are mounted as read-write bind mounts. A compromised container (e.g., via RCE in the analysis pipeline) can **modify source code files on the host**. Uvicorn's `--reload` flag (line 40) will **automatically pick up these changes**, creating a persistent code execution loop.

**Fix**: 
- Remove `--reload` from the production/staging command
- Use read-only mounts: `- ./engine:/app/engine:ro`
- Never mount source code in production; build it into the image

---

### HIGH-5 — Celery Task Accepts Arbitrary `str` Input Without Validation
**Files**: [`cicd_tasks.py:26`](file:///d:/Astra/backend/app/tasks/cicd_tasks.py#L26), [`execution_tasks.py:154`](file:///d:/Astra/backend/app/tasks/execution_tasks.py#L154)  
**Risk**: UUID Confusion / Task Hijacking

```python
@celery_app.task(...)
def process_github_webhook_task(event_id_str: str) -> Dict[str, Any]:
    event_id = uuid.UUID(event_id_str)  # Only validation is UUID parse
```

**Issue**: Celery task payloads are passed via Redis in plaintext. Anyone with Redis access (which is **unauthenticated** — see HIGH-6) can enqueue tasks with arbitrary `event_id_str` values, causing Celery workers to process arbitrary database records, including records of other projects.

**Fix**: Redis must be protected with `requirepass`. Task inputs should be validated against the DB before processing (verify the resource exists and matches expected state).

---

### HIGH-6 — Redis Has No Authentication or TLS
**File**: [`docker-compose.yml:22-32`](file:///d:/Astra/docker-compose.yml#L22-L32)

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"  # Exposed to host with no password
```

**Issue**: Redis is running without `requirepass` and is exposed on host port `6379`. Anyone on the local network (or Docker host network) can:
1. Read/write the Celery task queue (inject malicious tasks)
2. Read/write cancellation flags for test runs
3. Enumerate all active job states

**Fix**:
```yaml
redis:
  command: redis-server --requirepass ${REDIS_PASSWORD}
  # Remove the ports binding in production
```

---

## 🟡 MEDIUM Vulnerabilities

---

### MED-1 — `subprocess.run(shell=True)` with User-Controlled Data in Benchmark Fixture
**File**: [`setup_fixture.py:17`](file:///d:/Astra/backend/benchmark_apps/git_fixture/setup_fixture.py#L17)

```python
subprocess.run(cmd, shell=True, cwd=str(target_dir), check=True, ...)
```

**Issue**: `shell=True` is used for git commands. If `cmd` contains any user-controlled string (from a project name or repo URL), this is a shell injection vulnerability. Even if not user-controlled currently, this is a high-risk pattern that should never exist.

**Fix**: Use list form: `subprocess.run(["git", "init", str(target_dir)], check=True)`

---

### MED-2 — JWT Has No `iss`, `aud`, or `jti` Claims
**File**: [`security.py:40-44`](file:///d:/Astra/backend/app/core/security.py#L40-L44)

```python
to_encode = {
    "sub": str(subject),
    "exp": expire,
    "iat": datetime.now(timezone.utc)
    # Missing: iss, aud, jti
}
```

**Issue**: Without `iss` (issuer), `aud` (audience), and `jti` (JWT ID):
- Tokens from another service with the same secret could be accepted
- Token revocation is impossible (no JTI for blocklisting)
- Cross-service token reuse attacks are feasible

---

### MED-3 — No SSRF Protection When Registering `repository_url` for Projects
**File**: [`project_service.py`](file:///d:/Astra/backend/app/services/project_service.py)  
**Related**: [`analyzer_tasks.py:53`](file:///d:/Astra/backend/app/tasks/analyzer_tasks.py#L53)

**Issue**: `repository_url` is stored as a raw string in the `Project` model with no URL validation at creation time. When the analysis pipeline later calls `GitRepoCloner.clone(repository_url=analysis.repository_url, ...)`, it can be directed to:
- `file:///etc/passwd` — local filesystem read
- `http://169.254.169.254/...` — cloud metadata endpoint
- `git://internal-host/repo` — internal network access

The SSRFProtector only runs for HTTP *test execution*, not for git clone operations.

**Fix**: Validate `repository_url` at project creation time. Allow only `https://` GitHub/GitLab/Bitbucket URLs. Block `file://`, `git://`, `ssh://`, and private IP ranges in the URL.

---

### MED-4 — Analytics Platform Overview Leaks Cross-Tenant Data
**File**: [`analytics.py:44-50`](file:///d:/Astra/backend/app/api/v1/analytics.py#L44-L50)

```python
@router.get("/overview")
async def get_platform_overview(current_user: User = Depends(get_current_user), ...):
    return await AnalyticsService.get_platform_overview(db)  # No tenant filter
```

**Issue**: The `/analytics/overview` endpoint returns platform-wide aggregates. `AnalyticsService.get_platform_overview()` queries `TestRun`, `Project`, etc., without filtering by the current user's accessible projects. A `DEVELOPER` or `TESTER` user can see aggregate counts from all projects on the platform — including private projects belonging to other users.

---

### MED-5 — HTML Report Served Inline Without `Content-Security-Policy`
**File**: [`analytics.py:148-153`](file:///d:/Astra/backend/app/api/v1/analytics.py#L148-L153)

```python
return Response(
    content=report.html_content.encode("utf-8"),
    media_type="text/html; charset=utf-8",
    headers={"Content-Disposition": 'inline; filename=...'}
)
```

**Issue**: HTML reports generated by `HTMLReportGenerator` are served directly as `text/html` without a `Content-Security-Policy` header. If any user-controlled data (project names, endpoint paths, error messages) is embedded in the HTML without proper escaping, this becomes a stored XSS vector rendered in the victim's browser.

**Fix**: Add `Content-Security-Policy: default-src 'self'; script-src 'none'` to report responses. Ensure all HTML content is properly escaped.

---

## 🔵 LOW Vulnerabilities

---

### LOW-1 — `pip install --trusted-host` Disables PyPI TLS Verification in Dockerfile
**File**: [`Dockerfile:19`](file:///d:/Astra/backend/Dockerfile#L19)

```dockerfile
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org ...
```

**Issue**: These flags tell pip to trust the hosts without verifying TLS certificates, enabling MITM substitution of dependency packages during Docker image builds.

**Fix**: Remove the `--trusted-host` flags. If there are CA issues in the build environment, fix them by adding the CA certificate to the system store.

---

### LOW-2 — Celery Worker Uses `asyncio.run()` on Every Task
**Files**: [`execution_tasks.py:155`](file:///d:/Astra/backend/app/tasks/execution_tasks.py#L155), [`generation_tasks.py:137`](file:///d:/Astra/backend/app/tasks/generation_tasks.py#L137)

```python
def run_test_suite_execution_task(test_run_id_str: str):
    asyncio.run(execute_test_run_pipeline(test_run_id_str))  # Creates new loop per task
```

**Issue**: Each Celery task creates a new async engine and DB connection pool (`create_async_engine`) that is disposed at the end. Under high concurrency, this exhausts file descriptors and PostgreSQL connections. While not a security issue per se, it creates a **DoS surface** — a high volume of tasks will exhaust resources and crash the worker.

---

### LOW-3 — Regression Analysis Endpoint Returns Full Analysis to Any Authenticated User Without Ownership Check
**File**: [`regression.py:95-109`](file:///d:/Astra/backend/app/api/v1/regression.py#L95-L109)

```python
@router.get("/regression/analyses/{analysis_id}")
async def get_regression_analysis_details(analysis_id: uuid.UUID, ...):
    analysis = await service.get_analysis_by_id(analysis_id)
    return analysis  # No project ownership verification!
```

**Issue**: Any authenticated user can fetch any regression analysis by UUID without an ownership/access check.

---

### LOW-4 — Docs/OpenAPI Exposed Without Authentication in All Environments
**File**: [`main.py:34-35`](file:///d:/Astra/backend/app/main.py#L34-L35)

```python
docs_url="/docs",
redoc_url="/redoc",
```

**Issue**: FastAPI's Swagger UI and ReDoc documentation are publicly accessible. These expose all endpoint paths, schemas, parameters, and authentication requirements — providing a complete attack surface map to any unauthenticated visitor. In production, these should be disabled or protected.

**Fix**:
```python
docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
```

---

## 📊 Summary Table

| ID | Severity | File | Issue | Status |
|---|---|---|---|---|
| CRIT-1 | 🔴 Critical | `auth_service.py` | Hardcoded password bypass backdoor | **Fix immediately** |
| CRIT-2 | 🔴 Critical | `config.py` / `.env` | Weak JWT secret + 7-day expiry + no revocation | **Fix immediately** |
| CRIT-3 | 🔴 Critical | `cicd_service.py` | Fake `enc_v1:` encryption is plaintext storage | **Fix immediately** |
| CRIT-4 | 🔴 Critical | `ssrf_protector.py` | DNS rebinding SSRF bypass + prefix allowlist bypass | **Fix immediately** |
| CRIT-5 | 🔴 Critical | `repo_cloner.py` | `GIT_SSL_NO_VERIFY=true` — TLS MITM on git clone | **Fix immediately** |
| CRIT-6 | 🔴 Critical | `.env` / `.gitignore` | Real secrets in `.env` file — risk of git leak | **Fix immediately** |
| CRIT-7 | 🔴 Critical | `failure_analysis.py` | IDOR — no ownership check on failure analysis endpoints | **Fix immediately** |
| HIGH-1 | 🟠 High | `main.py` | Stack trace / DB URL leaked in 500 responses | Fix before production |
| HIGH-2 | 🟠 High | `target_env.py` | `verify_ssl=False` by default on all HTTP test runs | Fix before production |
| HIGH-3 | 🟠 High | All routers | No rate limiting on any endpoint (brute force) | Fix before production |
| HIGH-4 | 🟠 High | `docker-compose.yml` | Writable volume mounts + `--reload` = RCE persistence | Fix before staging |
| HIGH-5 | 🟠 High | Celery tasks | Unauthenticated Redis → arbitrary task injection | Fix before staging |
| HIGH-6 | 🟠 High | `docker-compose.yml` | Redis has no password, exposed on host port | Fix before staging |
| MED-1 | 🟡 Medium | `setup_fixture.py` | `shell=True` subprocess — potential shell injection | Fix |
| MED-2 | 🟡 Medium | `security.py` | JWT missing `iss`, `aud`, `jti` claims | Fix |
| MED-3 | 🟡 Medium | `analyzer_tasks.py` | No SSRF protection on `repository_url` at clone time | Fix |
| MED-4 | 🟡 Medium | `analytics.py` | Platform overview leaks cross-tenant aggregate data | Fix |
| MED-5 | 🟡 Medium | `analytics.py` | HTML reports served without CSP (XSS risk) | Fix |
| LOW-1 | 🔵 Low | `Dockerfile` | `--trusted-host` disables pip TLS verification | Fix |
| LOW-2 | 🔵 Low | Celery tasks | New engine per task = DoS via connection exhaustion | Fix |
| LOW-3 | 🔵 Low | `regression.py` | Regression analysis accessible by any authenticated user | Fix |
| LOW-4 | 🔵 Low | `main.py` | Swagger/ReDoc exposed without auth in all environments | Fix |

---

## ✅ What Is Correct (Positive Findings)

These patterns are correctly implemented and should be preserved:

| Area | Assessment |
|---|---|
| Password hashing | ✅ Argon2 via `pwdlib` — correct modern choice |
| HMAC webhook validation | ✅ Constant-time `hmac.compare_digest`, validated before JSON parsing |
| Project IDOR protection | ✅ `project_service.py` correctly returns 404 (not 403) to prevent enumeration |
| SSRF scheme validation | ✅ Only `http`/`https` allowed; metadata IP blocked before sandbox check |
| Role self-promotion prevention | ✅ `UserRegister` validator prevents users from self-assigning ADMIN role |
| Request body telemetry redaction | ✅ `TelemetryRedactor` strips credentials from stored test request data |
| Webhook idempotency check | ✅ Duplicate webhook delivery IDs are deduplicated before processing |
| DB session management | ✅ `get_db()` correctly rolls back on exception and closes session in `finally` |
| UUID-typed path parameters | ✅ All resource IDs are `uuid.UUID` type — prevents non-UUID injection |
| Celery JSON-only serializer | ✅ `task_serializer="json"` prevents pickle deserialization attacks |

---

## Recommended Fix Priority Order

```
Week 1 (Before ANY external access):
  1. CRIT-1: Remove auth backdoor
  2. CRIT-6: Rotate all secrets, verify .env is not tracked
  3. CRIT-7: Fix IDOR in failure_analysis.py
  4. CRIT-2: Strengthen JWT (secret, expiry, JTI, revocation)
  5. HIGH-6: Add Redis password

Week 2 (Before staging deployment):
  6. CRIT-3: Implement real Fernet encryption for notification URLs
  7. CRIT-4: Fix DNS rebinding SSRF  
  8. CRIT-5: Remove GIT_SSL_NO_VERIFY
  9. HIGH-1: Stop returning str(exc) in 500 responses
  10. HIGH-3: Add rate limiting to /auth/login and /auth/register
  11. MED-3: Add SSRF validation to repository_url at project creation

Week 3 (Before production deployment):
  12. HIGH-2: Change verify_ssl default to True
  13. HIGH-4: Make Docker volumes read-only; remove --reload
  14. HIGH-5: Authenticate Redis; validate task inputs
  15. MED-2: Add JWT claims (iss, aud, jti)
  16. LOW-4: Disable docs in production
  17. LOW-3: Add ownership check to regression analysis endpoint
```
