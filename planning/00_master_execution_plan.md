# ASTRA — Master Execution Plan & Architecture Blueprint

> **ASTRA — An Intelligent Automated Software Testing, Defect Detection and Root-Cause Analysis System**

---

## Executive Overview & Architectural Philosophy

ASTRA is a next-generation automated software quality and defect detection platform. Unlike conventional AI test generators that rely entirely on Large Language Models (LLMs), ASTRA is built upon a **hybrid deterministic-ML-AI architecture**. 

### Primary Architectural Axiom
> **ASTRA does not depend on an LLM to function.**

ASTRA operates across three complementary intelligence layers:
1. **Deterministic Layer (Core Engine):** AST analysis, rule engines, Swagger/OpenAPI parsing, boundary analysis, boundary condition solvers, and deterministic pytest/HTTPX test execution.
2. **Machine Learning Layer (Statistical Intelligence):** XGBoost / Random Forest test prioritization, historical failure frequency analysis, DBSCAN/K-Means failure clustering, and flaky test detection.
3. **Generative AI Layer (Optional NLP Intelligence):** Natural language requirement extraction, zero-shot/few-shot edge case synthesis, LLM-based root-cause explanation, and automated developer bug report draft generation.

If external LLM services (e.g., Gemini API, OpenAI) are unreachable or rate-limited, ASTRA seamlessly falls back to its deterministic rule engine and AST/ML pipelines without breaking test execution or report generation.

---

## System Architecture Diagram

```text
                               ┌───────────────────────────┐
                               │       USER / DEV / QA     │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   React 18 + Vite Web App │
                               │  Tailwind CSS + Recharts  │
                               └─────────────┬─────────────┘
                                             │ REST / WebSocket
                                             ▼
                               ┌───────────────────────────┐
                               │      FastAPI REST API     │
                               │  Async SQLAlchemy + Pydantic│
                               └─────────────┬─────────────┘
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      ▼                                      ▼                                      ▼
┌───────────────┐                  ┌───────────────────┐                  ┌──────────────────┐
│ PostgreSQL 16 │                  │ Redis 7 / Celery  │                  │  GitHub Actions  │
│  (Data Store) │                  │  (Task Engine)    │                  │  & Webhooks      │
└───────────────┘                  └─────────┬─────────┘                  └──────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │    ASTRA Execution Engine │
                               └─────────────┬─────────────┘
                                             │
          ┌──────────────────────────────────┼──────────────────────────────────┐
          ▼                                  ▼                                  ▼
┌───────────────────┐              ┌───────────────────┐              ┌───────────────────┐
│  Project Analyzer │              │   Test Generator  │              │ Failure & Root    │
│ (AST, Tree-Sitter)│              │  & Execution Core │              │  Cause Analyzer   │
└───────────────────┘              └───────────────────┘              └───────────────────┘
                                             │                                  │
                                             ▼                                  ▼
                               ┌───────────────────────────┐      ┌───────────────────────┐
                               │ Pytest / HTTPX Runner     │      │ Hybrid Intelligence   │
                               │ Playwright Worker         │      │ Rules + ML + Opt AI   │
                               └───────────────────────────┘      └───────────────────────┘
```

---

## 10-Phase Roadmap Matrix

| Phase | Title | Main Deliverables & Objectives | Estimated Timeline |
| :--- | :--- | :--- | :--- |
| **Phase 1** | [Core Foundation & Infrastructure](file:///d:/Astra/planning/phase_01_core_foundation.md) | Database schemas, FastAPI backend scaffold, JWT Auth, RBAC, React dashboard shell, Docker orchestrator. | Weeks 1–2 |
| **Phase 2** | [Project & Repository Analyzer](file:///d:/Astra/planning/phase_02_project_analyzer.md) | Git repo cloner, AST static analyzer (Python AST & Tree-Sitter), API router & endpoint extractor, Knowledge Graph builder. | Weeks 3–4 |
| **Phase 3** | [Test Execution & Assertion Engine](file:///d:/Astra/planning/phase_03_test_execution_engine.md) | Execution worker pool (Pytest, HTTPX, Playwright), deterministic assertion evaluator, execution log recorder. | Weeks 5–6 |
| **Phase 4** | [Rule-Based Test & Data Generation](file:///d:/Astra/planning/phase_04_test_generation_engine.md) | Non-LLM test case generator, OpenAPI schema parser, Boundary Value Analyzer (BVA), Equivalence Partitioning, Synthetic Data Engine. | Weeks 7–8 |
| **Phase 5** | [Requirement Intelligence & AI Layer](file:///d:/Astra/planning/phase_05_requirement_and_ai_layer.md) | NLP SRS requirement extractor, Gemini/Local LLM integration with strict fallback, complex scenario generator, root-cause prompt engine. | Weeks 9–10 |
| **Phase 6** | [Failure & Root-Cause Analysis](file:///d:/Astra/planning/phase_06_failure_and_root_cause_analysis.md) | Failure classification engine (App Bug vs Test Issue vs Env), Stack trace parser, AST code-to-failure link, automated markdown bug generator. | Week 11 |
| **Phase 7** | [ML Intelligence Engine](file:///d:/Astra/planning/phase_07_ml_intelligence.md) | XGBoost test prioritization, flaky test classifier, K-Means/DBSCAN failure clustering engine. | Week 12 |
| **Phase 8** | [Regression Testing & Impact Analysis](file:///d:/Astra/planning/phase_08_regression_engine.md) | Git diff parser, AST dependency mapper, targeted test selector, change impact assessment. | Week 13 |
| **Phase 9** | [CI/CD Pipeline & GitHub Integration](file:///d:/Astra/planning/phase_09_cicd_and_github_integration.md) | GitHub Webhooks, PR status checks, GitHub Actions workflow runner, Slack/Email alert dispatchers. | Week 14 |
| **Phase 10** | [Analytics, Reporting & Evaluation](file:///d:/Astra/planning/phase_10_analytics_reporting_evaluation.md) | Quality analytics dashboard, defect density metrics, evaluation on deliberately defective benchmark apps, research documentation suite. | Weeks 15–16 |

---

## Directory Structure Strategy

```text
astra/
│
├── planning/                             # Implementation Roadmap Specifications (Phases 1-10)
│   ├── 00_master_execution_plan.md
│   ├── phase_01_core_foundation.md
│   ├── phase_02_project_analyzer.md
│   ├── phase_03_test_execution_engine.md
│   ├── phase_04_test_generation_engine.md
│   ├── phase_05_requirement_and_ai_layer.md
│   ├── phase_06_failure_and_root_cause_analysis.md
│   ├── phase_07_ml_intelligence.md
│   ├── phase_08_regression_engine.md
│   ├── phase_09_cicd_and_github_integration.md
│   └── phase_10_analytics_reporting_evaluation.md
│
├── frontend/                             # React + Vite + Tailwind CSS Frontend
│   ├── src/
│   │   ├── components/                   # Reusable UI components (Tables, Charts, Cards)
│   │   ├── pages/                        # Page views (Dashboard, Project, TestRuns, Bugs)
│   │   ├── services/                     # Axios API clients & WebSocket managers
│   │   └── store/                        # State management (Zustand/Redux)
│   ├── index.html
│   └── package.json
│
├── backend/                              # FastAPI Core Service
│   ├── app/
│   │   ├── api/                          # REST Endpoint Controllers (v1)
│   │   ├── core/                         # Config, Security, DB session, Celery app
│   │   ├── models/                       # SQLAlchemy Database Models
│   │   ├── schemas/                      # Pydantic Request/Response Models
│   │   ├── services/                     # Business logic services
│   │   └── db/                           # Alembic migrations & seeders
│   ├── requirements.txt
│   └── main.py
│
├── engine/                               # Testing Engine & Analysis Core
│   ├── analyzer/                         # Static AST & Tree-Sitter Analyzers
│   ├── requirements/                     # SRS & OpenAPI Spec Processors
│   ├── generator/                        # Rule-based & Synthetic Data Generators
│   ├── executor/                         # Pytest / HTTPX Runner Pool
│   ├── assertions/                       # Deterministic Assertion Engine
│   └── regression/                       # Impact & Diff Analysis Core
│
├── ai/                                   # LLM Abstraction & Prompt Engineering
│   ├── providers/                        # Gemini, Local LLM, Provider Base
│   ├── prompts/                          # Structured system prompts
│   └── rag/                              # Knowledge Context Builders
│
├── ml/                                   # Statistical ML Models
│   ├── prioritization/                   # XGBoost / Random Forest models
│   ├── flaky_detection/                  # Flaky test scoring models
│   └── clustering/                       # DBSCAN / K-Means failure clusterers
│
├── workers/                              # Celery Async Execution Tasks
│
├── benchmark_apps/                       # Defective Benchmark Target Apps for Evaluation
│   ├── app_1_auth_api/
│   ├── app_2_ecommerce_api/
│   └── app_3_banking_api/
│
├── docker/                               # Container specs & Compose configuration
└── docker-compose.yml
```

---

## MVP Milestones Strategy (Phases 1 → 4)

To guarantee early validation and avoid over-engineering:
1. **Milestone 1 (End of Phase 2):** Connect Git repo -> Analyze AST -> Output JSON list of discovered endpoints/functions.
2. **Milestone 2 (End of Phase 4):** Generate boundary/equivalence HTTP test cases using rules only (no LLM) -> Execute via HTTPX runner -> Store results in PostgreSQL.
3. **Milestone 3 (End of Phase 6):** Run defective benchmark app -> Classify failures into App Bug vs Env -> Produce Markdown Bug Report.
4. **Milestone 4 (End of Phase 10):** Train ML prioritization -> Integrate with GitHub Actions -> Present visual dashboard & empirical benchmark evaluation.
