"""
Unit tests for Phase 6 Structural Diff Isolator
"""

import pytest
from engine.analysis.diff.json_diff_isolator import JsonDiffIsolator
from engine.analysis.models import DiffType


def test_json_diff_isolator_status_and_body_mismatch():
    isolator = JsonDiffIsolator()
    
    expected_body = {
        "status": "success",
        "total_amount": 500,
        "items": ["item1", "item2"]
    }
    actual_body = {
        "status": "success",
        "total_amount": 600,
        "items": ["item1"]
    }
    
    diffs = isolator.compare_responses(
        expected_status=200,
        actual_status=500,
        expected_body=expected_body,
        actual_body=actual_body,
    )

    assert len(diffs) >= 3
    
    # 1. Status diff
    status_diff = next(d for d in diffs if d.path == "$.status")
    assert status_diff.expected == 200
    assert status_diff.actual == 500

    # 2. Value mismatch diff
    val_diff = next(d for d in diffs if d.path == "$.body.total_amount")
    assert val_diff.expected == 500
    assert val_diff.actual == 600

    # 3. Array length mismatch diff
    arr_diff = next(d for d in diffs if d.path == "$.body.items.length")
    assert arr_diff.expected == 2
    assert arr_diff.actual == 1


def test_json_diff_isolator_missing_key():
    isolator = JsonDiffIsolator()
    
    expected_body = {"user": {"id": 1, "email": "test@example.com"}}
    actual_body = {"user": {"id": 1}}

    diffs = isolator.compare_responses(
        expected_status=200,
        actual_status=200,
        expected_body=expected_body,
        actual_body=actual_body,
    )

    assert len(diffs) == 1
    assert diffs[0].path == "$.body.user.email"
    assert diffs[0].diff_type == DiffType.MISSING_KEY
