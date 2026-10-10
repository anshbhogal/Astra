# ASTRA: Final Viva Defense Playbook, Slide Outline & Demonstration Guide

**Project**: ASTRA — Autonomous Software Testing, Regression Analysis & Defect Attribution  
**Document**: Final Viva Defense Package  
**Target Audience**: Academic Examiners, Industrial Evaluators, Thesis Defense Committee

---

## Part 1: 15-Slide Presentation Deck Outline & Speaker Notes

### Slide 1: Title & Overview
- **Title**: ASTRA: An Autonomous Platform for Microservice Quality Assurance, Selective Regression & Empirical Defect Attribution
- **Presenter**: Engineering Research Team
- **Key Concepts**: AST Static Analysis, Program Knowledge Graphs (PKG), Machine Learning Prioritization, 50-Bug Empirical Benchmark.
> **Speaker Notes**:  
> "Good morning, respected committee members and examiners. Today we present ASTRA, an end-to-end engineering and research platform that solves the dual dilemma of modern microservice development: how to maintain exhaustive software quality while keeping CI/CD regression build times bounded and deterministic."

### Slide 2: The Core Problem Statement
- **The Microservice Regression Dilemma**:
  - Running all tests on every commit is computationally prohibitive ($O(N)$ test explosion).
  - Naive test selection creates false negatives (broken endpoints slip into production).
  - Trivial HTTP 500 responses obscure true root causes (flakiness vs. business logic vs. server crash).
> **Speaker Notes**:  
> "In contemporary microservice engineering, teams either run every test—wasting hours of cloud computing—or select tests arbitrarily, leading to catastrophic production regressions. ASTRA bridges this gap through semantic static-dynamic synthesis."

### Slide 3: High-Level Platform Architecture (Phases 1–10)
- **Unified 4-Tier Pipeline**:
  - Tier 1: Ingestion & AST Tree-Sitter Analysis
  - Tier 2: Program Knowledge Graph (PKG) & Semantic Reachability
  - Tier 3: Asynchronous Test Execution, SSRF Protection & XGBoost Prioritization
  - Tier 4: Phase 10 Executive Quality Analytics & Empirical Benchmark Harness
> **Speaker Notes**:  
> "Over 10 rigorous milestones, ASTRA evolved from a containerized async foundation into a production-ready quality platform with over 15 PostgreSQL models, full Celery distributed orchestration, and a complete offline empirical evaluation harness."

### Slide 4: Phase 2 — AST Parsing & Program Knowledge Graphs
- **Tree-Sitter Static Extraction**:
  - Deterministic parsing of FastAPI routes, parameter signatures, and schemas.
  - Multi-directed PKG graph tracking endpoint $\rightarrow$ handler $\rightarrow$ model $\rightarrow$ database table dependencies.
> **Speaker Notes**:  
> "Rather than treating code as plain text, Phase 2 builds a directed Program Knowledge Graph. When code changes, ASTRA traverses reachability edges to identify precisely which endpoints are structurally impacted."

### Slide 5: Phase 3 — Invariant & Synthetic Test Generation
- **Property-Based Invariants**:
  - Boundary value synthesis, schema type fuzzing, unauthenticated rejection contracts.
  - Zero hallucinations: all assertions are derived deterministically from AST parameter types.
> **Speaker Notes**:  
> "Phase 3 proves our Zero-LLM Axiom. We generate high-coverage test cases and assertions using deterministic property-based heuristics, ensuring 100% reproducible results without external API tokens."

### Slide 6: Phase 4 — Isolated Sandbox & SSRF Defense-in-Depth
- **Execution Isolation**:
  - ASGITransport and isolated container execution.
  - Strict SSRF Guard blocking private subnet traversal (`10.0.0.0/8`, `192.168.0.0/16`, AWS metadata `169.254.169.254`).
  - Secret redaction for tokens and passwords.
> **Speaker Notes**:  
> "Security is built into the execution engine. Any synthetic test attempting to probe internal metadata or private networks is immediately terminated by our SSRF Guard."

### Slide 7: Phase 6 — Defect Classification & Root Cause Attribution
- **3-Tier Failure Categorization**:
  - `APPLICATION_BUG`, `SERVER_CRASH`, `BUSINESS_LOGIC_DEFECT`, `TEST_SCRIPT_ISSUE`, `SCHEMA_VIOLATION`, `ENVIRONMENT_FLAKE`.
  - SHA256 exception stack fingerprinting and automated defect clustering.
> **Speaker Notes**:  
> "When a test fails, ASTRA does not simply log an error. It parses the stack trace, extracts AST source mismatch, and categorizes the failure into an actionable taxonomy with automated clustering."

### Slide 8: Phase 7 — ML Test Prioritization & Flakiness Telemetry
- **Cost-Aware Machine Learning**:
  - Temporal train/test splitting (zero data leakage).
  - XGBoost ranking factoring in historical failure probability, test duration, and endpoint complexity.
  - Automated flaky test identification and quarantine workflows.
> **Speaker Notes**:  
> "Phase 7 trains a cost-aware XGBoost model using rigorous temporal cross-validation. Flaky tests are detected across multi-run transition matrices and safely quarantined before polluting CI builds."

### Slide 9: Phase 8 — Change-Impact Selective Regression
- **Zero False Negatives Philosophy**:
  - Git diff AST symbol extraction $\rightarrow$ PKG $k$-hop reachability.
  - Tier 1 (Targeted Impacted Suite) executed synchronously; Tier 2 (Deferred Suite) scheduled asynchronously.
  - Safety expansion heuristics ensuring zero critical tests are skipped.
> **Speaker Notes**:  
> "Our selective regression engine optimizes for zero false negatives. If an AST symbol modification reaches an endpoint through any dependency edge, that test is guaranteed to run in Tier 1."

### Slide 10: Phase 9 — CI/CD Automation & GitHub Integration
- **Closed-Loop CI Pipeline**:
  - Cryptographically verified GitHub webhooks (HMAC-SHA256).
  - GitHub Check Runs API with markdown PR impact summaries.
  - Multi-channel notification delivery (Slack, Webhook, Email).
> **Speaker Notes**:  
> "Phase 9 operationalizes ASTRA into developer workflows. Pull requests automatically trigger selective regression, publish status checks, and post detailed comment summaries to GitHub."

### Slide 11: Phase 10 — Scientific Benchmark Dataset (50 Bugs + 100 Controls)
- **Empirical Ground Truth Microservices**:
  - 4 real FastAPI microservices: `auth`, `ecommerce`, `student`, `banking`.
  - 50 real architectural defects across 7 defect categories.
  - 100 clean negative controls measuring true False Positive Rate ($FPR$).
  - 4-commit Git fixture.
> **Speaker Notes**:  
> "Phase 10 transforms ASTRA from a software tool into an empirically validated scientific contribution. We created 50 real injected bugs and 100 negative controls with clean database reset contracts."

### Slide 12: Phase 10 — Multi-Mode Ablation Study
- **Ablation Comparison Across 5 Modes**:
  - Mode 0: Baseline Clean
  - Mode A: Deterministic Rules
  - Mode B: ML Prioritization
  - Mode C: AI Replay & Synthetic Tests
  - Mode D: Full Hybrid ASTRA
> **Speaker Notes**:  
> "To scientifically prove the value of each component, we executed an ablation study across five modes. All metrics were measured empirically across repeated trials with 1,000-iteration bootstrap confidence intervals."

### Slide 13: Empirical Evaluation Results
- **Key Findings**:
  - Hybrid ASTRA (Mode D): **94.0% Recall** (47/50 bugs detected), **97.9% Precision**, **99.0% Specificity**.
  - Negative Control FPR: **1.0%** (only 1 false positive across 100 controls).
  - Outperforms standalone rules (+18.0% recall) and standalone ML (+30.0% recall).
  - Statistically significant ($p < 0.001$, non-overlapping 95% bootstrap CIs).
> **Speaker Notes**:  
> "Our empirical results clearly show that neither static rules nor machine learning alone are sufficient. Full Hybrid ASTRA achieved 94.0% recall and 99.0% specificity, proving that hybrid static-dynamic analysis is essential."

### Slide 14: Executive Reporting & Artifact Integrity
- **Audit-Grade Reporting Engine**:
  - Clean HTML5 reports with responsive print stylesheets (`@media print`).
  - ReportLab PDF generator with printable HTML fallback.
  - SHA256 digital fingerprint for immutability and compliance auditing.
> **Speaker Notes**:  
> "Quality reports in ASTRA are formal compliance documents. Every generated report carries a cryptographic SHA256 checksum, ensuring immutability for enterprise audit trails."

### Slide 15: Conclusion & Future Work
- **Summary of Contributions**:
  - 10 fully implemented, tested, and containerized engineering milestones.
  - 50-bug microservice benchmark suite with zero-LLM deterministic harness.
  - 100% test pass rate across containerized integration suites.
  - Future Work: Language expansion to Go and Java, distributed multi-region sandboxing.
> **Speaker Notes**:  
> "In conclusion, ASTRA delivers a comprehensive, scientifically evaluated, and enterprise-ready testing platform. We thank the committee and welcome your questions."

---

## Part 2: 5-Minute Live Demonstration Script

| Time | Action / Screen | Key Talking Points |
|---|---|---|
| **0:00 - 0:45** | **Dashboard Overview & Projects List** | Log into ASTRA (`/login`), show platform-wide overview, navigate to tracked projects list showing FastAPI microservices. |
| **0:45 - 1:30** | **Project Detail & Knowledge Graph** | Open `Phase 10 Target Service`, show Discovered Endpoints (28 endpoints), view Program Knowledge Graph nodes and dependencies. |
| **1:30 - 2:30** | **Executive Quality Dashboard** | Navigate to `/analytics`, explain composite Quality Scorecard (92.4/100), Defect Density per endpoint, SVG pass rate trend line, and Phase 6 failure donut chart. Click **Generate Audit Report** and demonstrate instant HTML and PDF export with SHA256 checksum. |
| **2:30 - 3:45** | **Scientific Benchmark Hub** | Navigate to `/benchmarks`. Show the Ground Truth Bug Catalog (50 bugs + 100 controls). Filter by `banking_service`, click on `BUG-BANK-001` (Double Spend Race Condition), demonstrate the **Three-State Detection Traceability Drawer** ($\text{Triggered} \rightarrow \text{Detected} \rightarrow \text{Attributed}$). |
| **3:45 - 4:45** | **Live Ablation Execution** | In the Ablation Study launcher, select Modes (Mode 0, Mode A, Mode D), select `IN_PROCESS_DETERMINISTIC`, set 3 trials, and click **Run Ablation Study**. Show live execution feedback, matrix update, and 95% bootstrap confidence intervals. |
| **4:45 - 5:00** | **Wrap-up** | Conclude live demo, highlight 100% offline determinism and zero LLM hallucination risk. |

---

## Part 3: Examiner Q&A Defense Playbook

### Q1: "Why did you build your own benchmark microservices instead of using established benchmarks like Defects4J or Bugs.jar?"
> **Examiner Intent**: Testing whether the student took a shortcut or genuinely understood benchmark limitations.  
> **Defense Answer**:  
> "Defects4J and Bugs.jar are monumental benchmarks, but they were engineered for **monolithic Java libraries** (e.g., Apache Commons, Joda-Time). They evaluate unit-level method faults, not **microservice-level architectural defects** such as broken JWT authentication, distributed double-spend concurrency, API schema violations, or cross-service inventory underflows. Furthermore, Defects4J cannot evaluate HTTP selective regression or OpenAPI invariant synthesis. Our 50-bug benchmark specifically models microservice failure modes with toggleable seed contracts, real Git histories, and 100 negative controls to evaluate false positive rates."

### Q2: "How do you guarantee that your XGBoost failure predictor does not suffer from data leakage?"
> **Examiner Intent**: Evaluating ML rigor and temporal validity.  
> **Defense Answer**:  
> "In Phase 7, we strictly avoided random k-fold cross-validation, which would leak future commit signals into past test predictions. Instead, we implemented **temporal train/test splitting**, sorting test execution records strictly chronologically by `created_at`. The model is trained exclusively on runs up to time $T$ and evaluated on subsequent runs at $T + \Delta t$. Additionally, feature engineering uses only backward-looking historical frequencies and static AST metrics, completely preventing data leakage."

### Q3: "In Mode D, why did ASTRA detect 47 bugs out of 50? What caused the 3 false negatives?"
> **Examiner Intent**: Verifying whether the student actually understands the system's empirical limits.  
> **Defense Answer**:  
> "The 3 false negatives occurred on subtle multi-step state sequence defects:
> 1. `BUG-STUD-012` (subtle course prerequisite circular chain) which required a sequence of 4 distinct prerequisite enrollments exceeding our standard 3-hop invariant budget.
> 2. `BUG-BANK-009` (micro-penny rounding discrepancy after 100 iterations) which stayed within our single-transaction tolerance threshold of $0.01.
> 3. `BUG-ECOM-014` (delayed race condition under specific thread interleaving) which resolved before the in-process SQLite lock was contested.  
> In our Threats to Validity section, we explicitly document these edge cases as directions for multi-hop graph expansion."

### Q4: "How does ASTRA ensure zero false negatives in Phase 8 selective regression testing?"
> **Examiner Intent**: Challenging the safety of test avoidance in CI/CD.  
> **Defense Answer**:  
> "Our selective regression philosophy prioritizes test safety over test reduction. When a commit diff occurs, ASTRA extracts modified AST symbols and traverses the Program Knowledge Graph using transitive closure ($k$-hop reachability). Any endpoint that has a direct or indirect path to a modified symbol is placed in **Tier 1 (Targeted)**. Furthermore, if the AST parser detects an ambiguous reflection call or dynamic import, our **Safety Expansion Heuristic** automatically falls back to full suite execution. Finally, Tier 2 (Deferred) tests are never discarded—they run asynchronously in low-priority background workers."

### Q5: "What prevents synthetic test generation in Phase 3 from generating illegal or hallucinated tests?"
> **Examiner Intent**: Inquiring about test validity and LLM hallucinations.  
> **Defense Answer**:  
> "Phase 3 test generation operates under our **Zero-LLM Axiom**. We do not use probabilistic language models to guess test schemas. Instead, our generator queries the AST and OpenAPI schema directly, extracting Pydantic field types, regex constraints, and required query parameters. Fuzzing values are generated using deterministic boundary heuristics (e.g., negative integers, max length strings, SQL injection probes). Because all generated inputs adhere strictly to typed schema contracts, they are 100% deterministic and free from hallucinations."

### Q6: "Why is a 3-state detection pipeline ($\text{Triggered} \rightarrow \text{Detected} \rightarrow \text{Attributed}$) necessary? Isn't an assertion failure enough?"
> **Examiner Intent**: Probing the scientific rigor of the evaluation harness.  
> **Defense Answer**:  
> "In microservice testing, an assertion failure alone can be misleading. A test might fail with an HTTP 500 error because of an unrelated network glitch or a database connection pool exhaustion, not because the injected bug was triggered. By requiring that a bug traverse all three states:
> 1. **Triggered**: proving the faulty code path was actually executed,
> 2. **Detected**: proving the invariant assertion caught the specific error condition, and
> 3. **Attributed**: proving the root-cause engine correctly mapped the defect to the known ground-truth category,
> we ensure that every True Positive represents genuine detection, eliminating accidental passes and false attributions."

### Q7: "How does ASTRA handle flaky tests in continuous integration?"
> **Examiner Intent**: Evaluating practical production readiness.  
> **Defense Answer**:  
> "Phase 7 implements flakiness telemetry based on transition counts across identical commit SHAs. If a test case flips between PASS and FAIL without any underlying code modification, ASTRA calculates a flakiness score:
> $$\text{Flakiness Score} = \frac{\text{Transitions}}{N - 1} \times \left(1 + \frac{\sigma_{\text{latency}}}{\mu_{\text{latency}}}\right)$$
> When this score exceeds the policy threshold, the test is automatically tagged for quarantine. Quarantined tests still execute to collect telemetry, but their failures do not block the Phase 9 CI quality gate, eliminating flaky build interruptions."

### Q8: "How does the system defend against Server-Side Request Forgery (SSRF) during synthetic test execution?"
> **Examiner Intent**: Evaluating security engineering.  
> **Defense Answer**:  
> "In Phase 4, we implemented an invariant `SSRFGuard` proxy. Every synthetic HTTP request URL is parsed and resolved to its canonical IP address before socket binding. If the target IP falls into private IPv4/IPv6 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`) or the cloud metadata service (`169.254.169.254`), the request is immediately aborted with an `SSRFViolationError`. Only explicitly whitelisted local Docker sandbox endpoints are permitted."

### Q9: "Why use both HTML and PDF export for executive quality reports?"
> **Examiner Intent**: Understanding reporting and compliance design choices.  
> **Defense Answer**:  
> "Different stakeholders require different artifacts. Engineering leads and developers benefit from interactive, responsive HTML5 reports with print styles (`@media print`) that can be embedded directly into browser workflows and intranet portals. Executive management, auditors, and compliance officers require formal, paginated PDF artifacts generated via ReportLab with fixed layouts. Crucially, both formats include the same cryptographic SHA256 checksum of the underlying dataset, ensuring complete data consistency across both representations."

### Q10: "If you had 6 more months to work on ASTRA, what would you add?"
> **Examiner Intent**: Assessing long-term vision, self-awareness, and research maturity.  
> **Defense Answer**:  
> "We would focus on three high-impact enhancements:
> 1. **Multi-Language PKG Expansion**: Extend our Tree-Sitter parser from Python FastAPI to Go (Gin) and Java (Spring Boot) to evaluate polyglot microservice meshes.
> 2. **Automated Program Repair (APR)**: Close the loop from Phase 6 defect attribution by generating AST patch candidates that pass the regression suite.
> 3. **Multi-Hop Distributed Tracing Integration**: Ingest OpenTelemetry distributed traces to map cross-microservice network dependencies directly into the Program Knowledge Graph."
