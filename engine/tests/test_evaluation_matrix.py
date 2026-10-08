"""
Unit tests for Phase 6 Diagnostic Evaluation Matrix
"""

import pytest
from engine.analysis.evaluator import DiagnosticEvaluator, EvaluationScenario
from engine.analysis.models import FailureCategory


def test_evaluation_matrix():
    scenarios = [
        EvaluationScenario(
            name="ZeroDivisionError Crash",
            expected_category=FailureCategory.SERVER_CRASH,
            expected_status=200,
            actual_status=500,
            raw_trace="Traceback (most recent call last):\n  File \"orders.py\", line 143, in calculate\nZeroDivisionError: division by zero",
            should_have_attribution=True,
        ),
        EvaluationScenario(
            name="Missing JSON Field",
            expected_category=FailureCategory.CONTRACT_VIOLATION,
            expected_status=200,
            actual_status=200,
            expected_body={"total_amount": 100},
            actual_body={},
            should_have_attribution=False,
        ),
        EvaluationScenario(
            name="Unauthorized 401",
            expected_category=FailureCategory.AUTHENTICATION_FAILURE,
            expected_status=200,
            actual_status=401,
            should_have_attribution=False,
        ),
        EvaluationScenario(
            name="Insufficient Evidence 500",
            expected_category=FailureCategory.SERVER_CRASH,
            expected_status=200,
            actual_status=500,
            should_be_insufficient=True,
        ),
    ]

    evaluator = DiagnosticEvaluator()
    report = evaluator.evaluate(scenarios)

    assert report.total_scenarios == 4
    assert report.classification_accuracy == 1.0
    assert report.false_positive_restraint == 1.0
    assert report.passed
