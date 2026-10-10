# Phase 3 — Deterministic Test Execution & Assertion Engine Implementation Guide

> **Module Focus:** Executable Test Specification Schema, Test Compiler, HTTPX & Pytest Worker Pool, Deterministic Assertion Engine, and Execution Logging System.

---

## 1. Phase Overview & Objectives

Phase 3 implements the deterministic core of Astra: the **Test Execution Engine**. It takes structured test specifications, compiles them into executable test suites, executes them via isolated workers using `HTTPX` (API testing) or `pytest` (unit/integration testing), applies strict non-AI assertion logic, and logs full request/response diagnostics into PostgreSQL.

### Key Deliverables
1. **Executable Test Schema:** JSON specification standardizing test inputs, headers, authentication context, expected status codes, response schemas, and assertion rules.
2. **Test Compiler Engine:** Dynamic code generator converting JSON test definitions into runnable Python `pytest` files or direct async `HTTPX` execution calls.
3. **Execution Worker Pool:** Celery worker tasks running tests concurrently in isolated subprocess sandboxes with configurable execution timeouts.
4. **Deterministic Assertion Engine:** Robust assertion evaluator validating HTTP status codes, JSON schema compliance, key-value matchers, header rules, and execution latency thresholds.
5. **Execution Recorder & Logger:** Structured database repository recording run metadata, request payloads, response payloads, execution duration, stack traces, and step-level outcomes.

---

## 2. Technical Stack Specifications

- **HTTP Execution Client:** `httpx` `0.27+` (async HTTP client with connection pooling).
- **Test Runner Framework:** `pytest` `8.0+` with `pytest-asyncio` and `pytest-json-report`.
- **Browser Execution Client:** `playwright` `1.42+` (Chromium worker pool for browser UI tests).
- **Schema Validation:** `jsonschema` `4.21+` for JSON schema contract assertions.

---

## 3. Architecture & Data Flow

```text
Structured JSON Test Cases
            │
            ▼
┌───────────────────────┐
│     Test Compiler     │ Converts JSON into HTTPX requests / Pytest modules
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│  Celery Worker Pool   │ Manages async execution queue
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Execution Sandbox     │ Runs HTTPX API calls or Pytest subprocesses
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│   Assertion Engine    │ Applies status, schema, latency & body assertions
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Results & Logs Record │ Persists full execution telemetry to PostgreSQL
└───────────────────────┘
```

---

## 4. Executable Test Case Data Model (`backend/app/models/execution.py`)

```python
from datetime import datetime
import uuid
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.domain import Base

class TestRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"

class TestOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"

class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    status: Mapped[TestRunStatus] = mapped_column(SQLEnum(TestRunStatus), default=TestRunStatus.PENDING, nullable=False)
    total_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    results: Mapped[list["TestResult"]] = relationship("TestResult", back_populates="test_run", cascade="all, delete-orphan")

class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_runs.id"), nullable=False)
    test_case_id: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    outcome: Mapped[TestOutcome] = mapped_column(SQLEnum(TestOutcome), nullable=False)
    request_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    response_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    assertion_failures: Mapped[list] = mapped_column(JSON, default=[], nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="results")
```

---

## 5. Deterministic Assertion Engine (`engine/assertions/evaluator.py`)

No AI is required to evaluate assertions. The evaluator applies deterministic validation against pre-defined contract specs:

```python
from typing import Dict, Any, List
import jsonschema

class AssertionEvaluator:
    @staticmethod
    def evaluate(test_spec: Dict[str, Any], response_status: int, response_body: Any, response_headers: Dict[str, str], duration_ms: float) -> List[Dict[str, Any]]:
        failures = []
        expected = test_spec.get("expected", {})

        # 1. Status Code Assertion
        if "status_code" in expected:
            expected_status = expected["status_code"]
            if response_status != expected_status:
                failures.append({
                    "type": "STATUS_CODE_MISMATCH",
                    "expected": expected_status,
                    "actual": response_status,
                    "message": f"Expected HTTP status {expected_status}, but received {response_status}."
                })

        # 2. JSON Schema Assertion
        if "json_schema" in expected and isinstance(response_body, dict):
            try:
                jsonschema.validate(instance=response_body, schema=expected["json_schema"])
            except jsonschema.ValidationError as err:
                failures.append({
                    "type": "SCHEMA_VALIDATION_ERROR",
                    "expected_schema": expected["json_schema"],
                    "message": f"Response JSON failed schema validation: {err.message}"
                })

        # 3. Exact Key-Value Matchers
        if "body_contains" in expected:
            for key, val in expected["body_contains"].items():
                if isinstance(response_body, dict):
                    actual_val = response_body.get(key)
                    if actual_val != val:
                        failures.append({
                            "type": "BODY_VALUE_MISMATCH",
                            "key": key,
                            "expected": val,
                            "actual": actual_val,
                            "message": f"Expected key '{key}' to equal '{val}', but got '{actual_val}'."
                        })

        # 4. Latency SLA Assertion
        if "max_latency_ms" in expected:
            max_lat = expected["max_latency_ms"]
            if duration_ms > max_lat:
                failures.append({
                    "type": "LATENCY_SLA_EXCEEDED",
                    "expected_max_ms": max_lat,
                    "actual_ms": duration_ms,
                    "message": f"Execution latency {duration_ms:.2f}ms exceeded SLA maximum of {max_lat}ms."
                })

        return failures
```

---

## 6. HTTPX Async Test Runner (`engine/executor/httpx_runner.py`)

```python
import httpx
import time
from typing import Dict, Any
from engine.assertions.evaluator import AssertionEvaluator

async def execute_http_test_case(base_url: str, test_spec: Dict[str, Any]) -> Dict[str, Any]:
    method = test_spec["method"]
    endpoint = test_spec["endpoint"]
    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = test_spec.get("headers", {})
    params = test_spec.get("query_params", {})
    body = test_spec.get("body", None)
    timeout = test_spec.get("timeout_seconds", 10.0)

    start_time = time.perf_counter()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body if body and method in ["POST", "PUT", "PATCH"] else None,
                timeout=timeout
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            
            try:
                response_json = response.json()
            except Exception:
                response_json = {"raw_text": response.text}

            failures = AssertionEvaluator.evaluate(
                test_spec=test_spec,
                response_status=response.status_code,
                response_body=response_json,
                response_headers=dict(response.headers),
                duration_ms=duration_ms
            )

            outcome = "PASS" if len(failures) == 0 else "FAIL"

            return {
                "test_case_id": test_spec.get("id"),
                "endpoint": endpoint,
                "method": method,
                "outcome": outcome,
                "status_code": response.status_code,
                "request_data": {"url": url, "headers": headers, "body": body},
                "response_data": response_json,
                "execution_time_ms": duration_ms,
                "assertion_failures": failures,
                "error_message": None
            }

        except httpx.RequestError as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "test_case_id": test_spec.get("id"),
                "endpoint": endpoint,
                "method": method,
                "outcome": "ERROR",
                "status_code": None,
                "request_data": {"url": url, "headers": headers, "body": body},
                "response_data": None,
                "execution_time_ms": duration_ms,
                "assertion_failures": [],
                "error_message": f"Network/HTTP Client Error: {str(exc)}"
            }
```

---

## 7. API Controllers (`backend/app/api/v1/execution.py`)

- `POST /test-runs` — Accepts a project ID and list of test case IDs; dispatches Celery execution tasks.
- `GET /test-runs/{id}` — Polls execution progress, total passed/failed counts, and run duration.
- `GET /test-runs/{id}/results` — Returns detailed step-by-step telemetry, request payloads, response bodies, and assertion failure details.

---

## 8. Verification & Test Plan

1. **HTTPX Runner Unit Verification:**
   - Launch mock HTTP service (`httptest` or FastAPI mock). Run `execute_http_test_case()` with valid (status 200) and invalid (status 500) inputs. Verify assertion failures are correctly flagged.
2. **Assertion Evaluator Edge Cases:**
   - Execute unit tests for `AssertionEvaluator`: verify JSON schema failure, latency SLA violation, and status code mismatch return expected JSON error structs.
3. **End-to-End Celery Test Execution:**
   - Submit 50 concurrent test specs via `POST /test-runs`. Ensure Celery worker executes all tests without worker deadlocks, logging all outcomes in PostgreSQL within 5 seconds.
