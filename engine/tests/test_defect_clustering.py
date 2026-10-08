"""
Unit tests for Phase 6 Canonical Fingerprinting & Defect Clustering
"""

import pytest
from engine.analysis.fingerprint import FingerprintEngine
from engine.analysis.models import FailureAnalysis, FailureCategory, ClusterMatchPrecision


def test_fingerprint_engine_canonical_hash():
    engine = FingerprintEngine()
    
    fp1 = engine.compute_fingerprint(
        category=FailureCategory.SERVER_CRASH,
        exception_type="KeyError",
        exception_message="'discount'",
        root_function="calculate_discount",
        endpoint="POST /orders",
    )
    
    fp2 = engine.compute_fingerprint(
        category=FailureCategory.SERVER_CRASH,
        exception_type="KeyError",
        exception_message="'discount'",
        root_function="calculate_discount",
        endpoint="POST /orders",
    )

    assert fp1 == fp2
    assert len(fp1) == 64  # SHA256 hex digest length


def test_cluster_failures():
    engine = FingerprintEngine()
    
    failure1 = FailureAnalysis(
        test_result_id="tr1",
        test_case_id="tc1",
        category=FailureCategory.BUSINESS_LOGIC_DEFECT,
        error_message="KeyError: 'discount'",
        exception_type="KeyError",
        failing_function="calculate_discount",
    )
    
    failure2 = FailureAnalysis(
        test_result_id="tr2",
        test_case_id="tc2",
        category=FailureCategory.BUSINESS_LOGIC_DEFECT,
        error_message="KeyError: 'discount'",
        exception_type="KeyError",
        failing_function="calculate_discount",
    )

    clusters = engine.cluster_failures([failure1, failure2], run_id="run_100")

    assert len(clusters) == 1
    assert clusters[0].member_count == 2
    assert clusters[0].occurrence_count == 2
    assert clusters[0].match_precision == ClusterMatchPrecision.EXACT_MATCH
