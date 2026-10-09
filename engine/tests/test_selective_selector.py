import pytest
from engine.regression.selective_selector import SelectiveSelector
from engine.regression.test_impact_mapper import MappedTestCase
from engine.regression.safety_gate import SafetyCheckResult


def test_selective_selector_partitioning():
    all_test_cases = [
        {"id": "tc-1", "name": "test_get_users", "endpoint": "/api/v1/users", "method": "GET", "avg_duration_ms": 100},
        {"id": "tc-2", "name": "test_delete_post", "endpoint": "/api/v1/posts", "method": "DELETE", "avg_duration_ms": 200},
    ]

    mapped_tests = [
        MappedTestCase(
            test_case_id="tc-1",
            name="test_get_users",
            endpoint="/api/v1/users",
            method="GET",
            impact_confidence=0.95,
            impact_distance=1,
            match_strategy="EXACT_ENDPOINT",
        )
    ]

    safety_res = SafetyCheckResult(
        expansion_triggered=False,
        triggers=[],
        confidence_penalty=0.0,
        expansion_reason=None,
        expanded_test_ids={"tc-1"},
    )

    selector = SelectiveSelector()
    res = selector.select_tests("fp-123", all_test_cases, mapped_tests, safety_res)

    assert res.total_suite_tests == 2
    assert res.selected_tier1_count == 1
    assert res.deferred_tier2_count == 1
    assert res.test_reduction_percent == 50.0
    assert res.estimated_time_avoided_ms == 200.0
    assert res.tier1_test_details[0].test_case_id == "tc-1"
    assert res.tier2_test_details[0].test_case_id == "tc-2"
