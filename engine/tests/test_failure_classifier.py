"""
Unit tests for Phase 6 Failure Classifier & Priority Rules
"""

import pytest
from engine.analysis.classifier import FailureClassifier
from engine.analysis.models import FailureCategory, ParsedException, JsonDiffItem, DiffType


def test_classifier_server_crash():
    classifier = FailureClassifier()
    category, confidence, rule_id, summary = classifier.classify(
        expected_status=200,
        actual_status=500,
        raw_logs="Internal Server Error: ZeroDivisionError: division by zero",
    )
    
    assert category == FailureCategory.SERVER_CRASH
    assert confidence >= 0.95
    assert rule_id == "R001"


def test_classifier_database_error():
    classifier = FailureClassifier()
    parsed_sql = ParsedException(
        exception_type="UniqueConstraintViolation",
        message="duplicate key value violates unique constraint",
        sql_state="23505",
        language="sql",
    )
    category, confidence, rule_id, summary = classifier.classify(
        expected_status=200,
        actual_status=500,
        parsed_exception=parsed_sql,
    )
    
    assert category == FailureCategory.DATABASE_ERROR
    assert rule_id == "R002"


def test_classifier_semantic_pass():
    classifier = FailureClassifier()
    # Expected 422, Actual 422 is expected validation response!
    category, confidence, rule_id, summary = classifier.classify(
        expected_status=422,
        actual_status=422,
        execution_result="PASSED",
    )
    
    assert category == FailureCategory.UNKNOWN
    assert rule_id == "PASS_SEMANTIC"


def test_classifier_auth_failure():
    classifier = FailureClassifier()
    category, confidence, rule_id, summary = classifier.classify(
        expected_status=200,
        actual_status=401,
    )
    
    assert category == FailureCategory.AUTHENTICATION_FAILURE
    assert rule_id == "R005"
