"""
E2E Integration unit tests for Phase 6 Root Cause Analyzer Orchestrator
"""

import pytest
from engine.analysis.root_cause_analyzer import RootCauseAnalyzer
from engine.analysis.models import FailureCategory, ReasoningType


def test_analyzer_full_pipeline_python_exception():
    analyzer = RootCauseAnalyzer()
    
    raw_trace = """Traceback (most recent call last):
  File "/app/services/orders.py", line 143, in calculate_total
    discount = payload['discount']
KeyError: 'discount'"""

    report = analyzer.analyze(
        test_result_id="tr_101",
        test_case_id="tc_555",
        expected_status=200,
        actual_status=500,
        raw_stack_trace=raw_trace,
        endpoint_id="POST /orders",
    )

    assert report.category == FailureCategory.SERVER_CRASH
    assert report.exception_type == "KeyError"
    assert report.failing_file == "/app/services/orders.py"
    assert report.failing_line == 143
    assert len(report.fault_locations) == 1
    assert len(report.root_cause_candidates) == 1
    assert report.root_cause_candidates[0].reasoning_type == ReasoningType.EXCEPTION_ORIGIN
    assert len(report.fingerprint) == 64
    assert report.classification_confidence >= 0.95


def test_analyzer_insufficient_evidence():
    analyzer = RootCauseAnalyzer()
    
    report = analyzer.analyze(
        test_result_id="tr_102",
        test_case_id="tc_556",
        expected_status=200,
        actual_status=500,
        raw_stack_trace="",  # No trace, no logs
    )

    assert report.category == FailureCategory.SERVER_CRASH
    assert len(report.fault_locations) == 0
    assert report.root_cause_confidence == 0.0
    assert report.root_cause_candidates[0].reasoning_type == ReasoningType.INSUFFICIENT_EVIDENCE
