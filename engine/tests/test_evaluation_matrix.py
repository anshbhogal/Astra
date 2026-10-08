"""
Comprehensive unit test suite for Phase 6 Diagnostic Evaluation Matrix (13 Taxonomy Categories).
"""

import pytest
from engine.analysis.evaluator import DiagnosticEvaluator, EvaluationScenario
from engine.analysis.models import FailureCategory


def test_comprehensive_evaluation_matrix_13_categories():
    scenarios = [
        # 1. SERVER_CRASH
        EvaluationScenario(
            name="Python ZeroDivisionError Crash",
            expected_category=FailureCategory.SERVER_CRASH,
            expected_status=200,
            actual_status=500,
            raw_trace="Traceback (most recent call last):\n  File \"services/orders.py\", line 143, in calculate_total\nZeroDivisionError: division by zero",
            expected_file="services/orders.py",
            expected_line=143,
            expected_function="calculate_total",
        ),
        # 2. DATABASE_ERROR
        EvaluationScenario(
            name="PostgreSQL Unique Constraint Violation",
            expected_category=FailureCategory.DATABASE_ERROR,
            expected_status=200,
            actual_status=500,
            raw_trace="ERROR: duplicate key value violates unique constraint \"users_email_key\" (SQLSTATE 23505)",
        ),
        # 3. TIMEOUT_PERFORMANCE
        EvaluationScenario(
            name="SLA Execution Timeout",
            expected_category=FailureCategory.TIMEOUT_PERFORMANCE,
            expected_status=200,
            actual_status=504,
            raw_logs="Execution result = TIMEOUT",
        ),
        # 4. ENVIRONMENT_FLAKE
        EvaluationScenario(
            name="Target Connection Refused",
            expected_category=FailureCategory.ENVIRONMENT_FLAKE,
            expected_status=200,
            actual_status=503,
            raw_logs="ConnectionRefusedError: [Errno 111] Connection refused",
        ),
        # 5. AUTHENTICATION_FAILURE
        EvaluationScenario(
            name="HTTP 401 Unauthorized",
            expected_category=FailureCategory.AUTHENTICATION_FAILURE,
            expected_status=200,
            actual_status=401,
            raw_logs="Missing Authorization Bearer token",
        ),
        # 6. AUTHORIZATION_FAILURE
        EvaluationScenario(
            name="HTTP 403 Forbidden",
            expected_category=FailureCategory.AUTHORIZATION_FAILURE,
            expected_status=200,
            actual_status=403,
            raw_logs="Insufficient role permissions: admin required",
        ),
        # 7. NOT_FOUND_DEFECT
        EvaluationScenario(
            name="HTTP 404 Entity Missing",
            expected_category=FailureCategory.NOT_FOUND_DEFECT,
            expected_status=200,
            actual_status=404,
            raw_logs="Order entity #9999 not found",
        ),
        # 8. METHOD_NOT_ALLOWED
        EvaluationScenario(
            name="HTTP 405 Method Not Allowed",
            expected_category=FailureCategory.METHOD_NOT_ALLOWED,
            expected_status=200,
            actual_status=405,
            raw_logs="Method POST not allowed on route /health",
        ),
        # 9. REQUEST_VALIDATION_DEFECT
        EvaluationScenario(
            name="FastAPI 422 Unprocessable Entity Validation",
            expected_category=FailureCategory.REQUEST_VALIDATION_DEFECT,
            expected_status=200,
            actual_status=422,
            raw_logs="ValidationError: field required 'email'",
        ),
        # 10. CONTRACT_VIOLATION
        EvaluationScenario(
            name="JSON Schema Missing Key Delta",
            expected_category=FailureCategory.CONTRACT_VIOLATION,
            expected_status=200,
            actual_status=200,
            expected_body={"status": "ok", "total_amount": 500},
            actual_body={"status": "ok"},
            expected_diff_path="$.body.total_amount",
        ),
        # 11. BUSINESS_LOGIC_DEFECT
        EvaluationScenario(
            name="Domain Rule Rejection 400",
            expected_category=FailureCategory.BUSINESS_LOGIC_DEFECT,
            expected_status=200,
            actual_status=400,
            raw_logs="Transaction amount exceeds allowed limit of $1000",
        ),
        # 12. DEPENDENCY_FAILURE
        EvaluationScenario(
            name="502 Bad Gateway Downstream Upstream Outage",
            expected_category=FailureCategory.DEPENDENCY_FAILURE,
            expected_status=200,
            actual_status=502,
            raw_logs="Upstream payment gateway response bad gateway 502",
        ),
        # 13. False-Positive Restraint (Insufficient Evidence)
        EvaluationScenario(
            name="Generic 500 without stack trace or logs",
            expected_category=FailureCategory.SERVER_CRASH,
            expected_status=200,
            actual_status=500,
            should_be_insufficient=True,
        ),
    ]

    evaluator = DiagnosticEvaluator()
    report = evaluator.evaluate(scenarios)

    failed_details = [d for d in report.details if not d["classification_passed"]]
    assert not failed_details, f"Failed details: {failed_details}"

    assert report.total_scenarios == 13
    assert report.classification_accuracy == 1.0
    assert report.attribution_accuracy == 1.0
    assert report.diff_precision == 1.0
    assert report.false_positive_restraint == 1.0
    assert report.passed
