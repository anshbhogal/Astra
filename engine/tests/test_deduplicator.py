"""
Unit tests for PayloadDeduplicator multi-part SHA256 payload fingerprinting.
"""

import pytest
from engine.generator.deduplicator import PayloadDeduplicator
from engine.models.test_spec import TestSpecification, TestType


def test_payload_deduplication():
    spec1 = TestSpecification(
        id="spec-1", name="Test 1", endpoint_id="ep-1", test_type=TestType.HAPPY_PATH,
        method="GET", path="/health", query_params={"a": "1"}, headers={"Accept": "application/json"}
    )
    spec2 = TestSpecification(
        id="spec-2", name="Test 2", endpoint_id="ep-1", test_type=TestType.HAPPY_PATH,
        method="GET", path="/health", query_params={"a": "1"}, headers={"Accept": "application/json"}
    )
    spec3 = TestSpecification(
        id="spec-3", name="Test 3", endpoint_id="ep-1", test_type=TestType.BOUNDARY,
        method="GET", path="/health", query_params={"a": "2"}, headers={"Accept": "application/json"}
    )

    deduped, count = PayloadDeduplicator.deduplicate_specifications([spec1, spec2, spec3])

    assert len(deduped) == 2
    assert count == 1
    assert deduped[0].id == "spec-1"
    assert deduped[1].id == "spec-3"
