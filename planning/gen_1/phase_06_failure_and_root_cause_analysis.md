# Phase 6 — Failure & Root-Cause Analysis Implementation Guide

> **Module Focus:** Failure Classification, Bug Confidence Scoring (App Bug vs Test Problem vs Env Issue), Stack Trace & AST Code Mapper, Root-Cause Analysis, and Automated Bug Report Generator.

---

## 1. Phase Overview & Objectives

Phase 6 implements Astra's diagnostic core: **Failure & Root-Cause Analysis**. When a test execution fails, Astra does not simply assume every failure is a developer bug. Instead, it runs deterministic classification, parses stack traces, maps failure lines back to source code via AST and the Project Knowledge Graph, calculates confidence scores across 3 failure categories, and automatically generates structured **Bug Reports**.

### Key Architectural Rule
> **Astra distinguishes between Application Bugs, Test Problems, and Environment Issues, presenting failure causes with explicit system confidence scores.**

```text
                           FAILED TEST RESULT
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │ Deterministic Classification  │
                   └───────────────┬───────────────┘
                                   ▼
                   ┌───────────────────────────────┐
                   │  Stack Trace & AST Code Mapper│
                   └───────────────┬───────────────┘
                                   ▼
                   ┌───────────────────────────────┐
                   │  Confidence Score Calculator  │
                   └───────────────┬───────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            ▼                      ▼                      ▼
┌───────────────────────┐┌───────────────────┐┌──────────────────────┐
│  Application Bug      ││  Test Problem     ││  Environment Issue   │
│  Confidence: 91%      ││  Confidence: 4%   ││  Confidence: 5%      │
└───────────┬───────────┘└───────────────────┘└──────────────────────┘
            ▼
┌───────────────────────┐
│ Automated Bug Report  │ Generates formatted markdown issue report (BUG-001)
└───────────────────────┘
```

---

## 2. Technical Stack Specifications

- **Traceback Parser:** Built-in Python `traceback` and `python-better-exceptions` for frame inspection.
- **AST Mapping Engine:** AST Node visitor matching frame filename and line numbers to exact code blocks.
- **Data Models:** SQLAlchemy ORM models for `Failures` and `BugReports`.

---

## 3. Failure & Bug Report Data Models (`backend/app/models/defects.py`)

```python
from datetime import datetime
import uuid
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.domain import Base

class FailureCategory(str, Enum):
    APPLICATION_BUG = "APPLICATION_BUG"
    TEST_PROBLEM = "TEST_PROBLEM"
    ENVIRONMENT_ISSUE = "ENVIRONMENT_ISSUE"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"

class BugSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class BugStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class FailureAnalysis(Base):
    __tablename__ = "failure_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_results.id"), nullable=False)
    primary_category: Mapped[FailureCategory] = mapped_column(SQLEnum(FailureCategory), nullable=False)
    
    # Confidence breakdown scores (sum = 1.0)
    app_bug_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    test_problem_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    env_issue_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    fault_file: Mapped[str] = mapped_column(String(500), nullable=True)
    fault_function: Mapped[str] = mapped_column(String(255), nullable=True)
    fault_line_number: Mapped[int] = mapped_column(nullable=True)
    root_cause_summary: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace_snippet: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    bug_report: Mapped["BugReport"] = relationship("BugReport", back_populates="failure_analysis", uselist=False)

class BugReport(Base):
    __tablename__ = "bug_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bug_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # BUG-001
    failure_analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("failure_analyses.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[BugSeverity] = mapped_column(SQLEnum(BugSeverity), nullable=False)
    status: Mapped[BugStatus] = mapped_column(SQLEnum(BugStatus), default=BugStatus.OPEN, nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    failure_analysis: Mapped["FailureAnalysis"] = relationship("FailureAnalysis", back_populates="bug_report")
```

---

## 4. Deterministic Failure & Confidence Scoring Engine (`engine/analyzer/failure_classifier.py`)

```python
from typing import Dict, Any

class FailureClassifierEngine:
    @staticmethod
    def classify_failure(test_result: Dict[str, Any]) -> Dict[str, Any]:
        status_code = test_result.get("status_code")
        error_msg = str(test_result.get("error_message") or "")
        assertion_failures = test_result.get("assertion_failures", [])
        response_body = str(test_result.get("response_data") or "")

        # Default confidence baselines
        app_bug = 0.10
        test_prob = 0.10
        env_issue = 0.80

        # Heuristic 1: HTTP 500 Internal Server Error -> Application Bug
        if status_code == 500 or "Unhandled Exception" in error_msg or "KeyError" in response_body:
            app_bug = 0.91
            test_prob = 0.04
            env_issue = 0.05
            category = "APPLICATION_BUG"
            summary = "Application threw HTTP 500 Unhandled Exception or KeyError in server code."

        # Heuristic 2: Network Timeout / ECONNREFUSED -> Environment Issue
        elif "ConnectionRefused" in error_msg or "Timeout" in error_msg or status_code == 503:
            app_bug = 0.05
            test_prob = 0.05
            env_issue = 0.90
            category = "ENVIRONMENT_ISSUE"
            summary = "Target environment unreachable or service down (Connection Refused / Timeout)."

        # Heuristic 3: Status code mismatch (Expected 400, got 200) -> Test Case contract problem or App Validation bug
        elif any(af.get("type") == "STATUS_CODE_MISMATCH" for af in assertion_failures):
            app_bug = 0.75
            test_prob = 0.20
            env_issue = 0.05
            category = "APPLICATION_BUG"
            summary = "Endpoint validation contract failure. Returned unexpected HTTP status code."

        else:
            category = "APPLICATION_BUG"
            summary = "Assertion evaluation failure."

        return {
            "primary_category": category,
            "confidence": {
                "app_bug": app_bug,
                "test_problem": test_prob,
                "env_issue": env_issue
            },
            "root_cause_summary": summary
        }
```

---

## 5. Automated Bug Report Generator (`engine/analyzer/bug_report_builder.py`)

```python
from typing import Dict, Any

class BugReportBuilder:
    @staticmethod
    def generate_markdown_report(bug_code: str, test_result: Dict[str, Any], classification: Dict[str, Any]) -> str:
        endpoint = test_result.get("endpoint", "N/A")
        method = test_result.get("method", "N/A")
        status_code = test_result.get("status_code", "N/A")
        conf = classification["confidence"]

        markdown = f"""# {bug_code} — {method} {endpoint} Failure Report

### Executive Summary
- **Classification:** `{classification['primary_category']}`
- **Severity:** `HIGH`
- **Root Cause Summary:** {classification['root_cause_summary']}

---

### Failure Diagnostic Confidence
| Category | Confidence Score |
| :--- | :--- |
| **Application Bug** | `{conf['app_bug'] * 100:.1f}%` |
| **Test Script Problem** | `{conf['test_prob'] * 100:.1f}%` |
| **Environment / Infra Issue** | `{conf['env_issue'] * 100:.1f}%` |

---

### Request & Response Diagnostic Telemetry
- **HTTP Method:** `{method}`
- **Endpoint URL:** `{endpoint}`
- **Actual HTTP Status:** `{status_code}`
- **Execution Time:** `{test_result.get('execution_time_ms', 0):.2f} ms`

#### Request Data
```json
{test_result.get('request_data')}
```

#### Response Data
```json
{test_result.get('response_data')}
```

---

### Assertion Failures & Stack Trace
```text
{test_result.get('assertion_failures')}
{test_result.get('error_message') or 'No unhandled python exception caught.'}
```

---
*Report automatically synthesized by Astra Automated Software Testing Platform.*
"""
        return markdown
```

---

## 6. API Controllers (`backend/app/api/v1/defects.py`)

- `POST /analysis/failure/{test_result_id}` — Runs deterministic failure classification, calculates confidence scores, isolates fault line, and generates a `BugReport`.
- `GET /bugs` — Lists all open bug reports with severity, affected endpoint, and classification confidence.
- `GET /bugs/{id}` — Returns the rendered markdown bug report and evidence payload.
- `PATCH /bugs/{id}` — Updates bug status (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`).

---

## 7. Verification & Test Plan

1. **Classification Confidence Test:**
   - Input test result with `HTTP 500` and `KeyError: user_id`. Verify `app_bug_confidence >= 0.90` and primary category is `APPLICATION_BUG`.
2. **Environment Fault Isolation Test:**
   - Input test result with `httpx.ConnectError: Connection Refused`. Verify primary category is `ENVIRONMENT_ISSUE` with `env_issue_confidence >= 0.85`.
3. **Bug Report Output Verification:**
   - Execute bug report generator. Verify output markdown matches schema format and includes request/response JSON snippets.
