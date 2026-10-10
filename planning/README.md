# ASTRA Implementation Planning Index

Welcome to the centralized implementation planning directory for the **ASTRA** platform. The planning documentation is divided across two major platform generations:

---

## 🏛️ [ASTRA Gen 1 (Phases 1–10) — Core Platform Foundation](file:///d:/Astra/planning/gen_1/00_master_execution_plan.md)
*Status: 100% Completed & Verified (128/128 Tests Passing)*

Directory: [`planning/gen_1/`](file:///d:/Astra/planning/gen_1/)

| Phase | Planning Guide | Focus Area |
|---|---|---|
| **Phase 1** | [01. Core Foundation](file:///d:/Astra/planning/gen_1/phase_01_core_foundation.md) | FastAPI scaffold, PostgreSQL, JWT Auth, RBAC, Celery/Redis queue, React shell, Docker Compose. |
| **Phase 2** | [02. Project Analyzer](file:///d:/Astra/planning/gen_1/phase_02_project_analyzer.md) | Git cloner, Python AST & Tree-Sitter analyzers, OpenAPI endpoint parser, Code Knowledge Graph. |
| **Phase 3** | [03. Test Execution Engine](file:///d:/Astra/planning/gen_1/phase_03_test_execution_engine.md) | Worker execution pool (Pytest, HTTPX), deterministic assertions, execution recorder. |
| **Phase 4** | [04. Rule-Based Test Generation](file:///d:/Astra/planning/gen_1/phase_04_test_generation_engine.md) | Non-LLM test generator, Boundary Value Analyzer (BVA), Equivalence Partitioning, Synthetic Data. |
| **Phase 5** | [05. Requirement & AI Layer](file:///d:/Astra/planning/gen_1/phase_05_requirement_and_ai_layer.md) | SRS document parser, Gemini/Local LLM integration, zero/few-shot synthesis, prompt engine. |
| **Phase 6** | [06. Failure & Root-Cause Analysis](file:///d:/Astra/planning/gen_1/phase_06_failure_and_root_cause_analysis.md) | Semantic classification, stack trace parser, PKG fault localization, canonical clustering. |
| **Phase 7** | [07. ML Intelligence Engine](file:///d:/Astra/planning/gen_1/phase_07_ml_intelligence.md) | XGBoost test prioritization, temporal cross-validation, flakiness state machine, test healing. |
| **Phase 8** | [08. Selective Regression Engine](file:///d:/Astra/planning/gen_1/phase_08_regression_engine.md) | Git diff parser, AST dependency mapper, Tier 1 / Tier 2 targeted test selector. |
| **Phase 9** | [09. CI/CD & GitHub Integration](file:///d:/Astra/planning/gen_1/phase_09_cicd_and_github_integration.md) | HMAC-SHA256 webhooks, GitHub Check Runs API, PR commenter, Slack/Email alert dispatchers. |
| **Phase 10** | [10. Analytics, Reporting & Evaluation](file:///d:/Astra/planning/gen_1/phase_10_analytics_reporting_evaluation.md) | Quality scorecard, 50-bug benchmark across 4 microservices, 100 negative controls, ablation study, viva package. |

---

## 🚀 [ASTRA Gen 2 (Phases 11–15) — Enterprise Polyglot & Autonomous Self-Healing](file:///d:/Astra/planning/gen_2/00_master_execution_plan.md)
*Status: Planning & Specification*

Directory: [`planning/gen_2/`](file:///d:/Astra/planning/gen_2/)

| Gen 2 Phase | Planning Guide | Focus Area |
|---|---|---|
| **Phase 1 (Phase 11)** | [01. Polyglot Engine Expansion](file:///d:/Astra/planning/gen_2/phase_01_polyglot_engine.md) | Tree-Sitter AST & PKG parsers for **Go (Gin/Fiber)**, **TypeScript/Node.js (Express/NestJS)**, and **Java (Spring Boot)**; universal route extraction; cross-language selective regression. |
| **Phase 2 (Phase 12)** | *02. Automated Program Repair & Auto-PRs (Upcoming)* | AST patch proposal synthesizer, sandboxed patch verification, Zero-Regression Gate, autonomous GitHub Pull Request generator. |
| **Phase 3 (Phase 13)** | *03. OpenTelemetry & Dynamic PKG Tracing (Upcoming)* | Ingestion of Jaeger/Zipkin OTel distributed traces; dynamic multi-microservice dependency edge generation; cross-service impact propagation. |
| **Phase 4 (Phase 14)** | *04. Production Shadow Traffic Replay (Upcoming)* | Gateway access log ingestion, time-travel mock replay, semantic deep JSON diffing to detect silent response changes under real traffic distributions. |
| **Phase 5 (Phase 15)** | *05. Adversarial Red-Team Security Fuzzing (Upcoming)* | Autonomous attacker agent targeting OWASP API Top 10 (IDOR, BOLA, JWT stripping, mass assignment) competing against Blue-Team assertion guards. |
