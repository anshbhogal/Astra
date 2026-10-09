"""Unit tests for Dynamic Value Text Normalizer & Cosine DBSCAN Semantic Failure Clusterer."""

import pytest
from ml.clustering.normalizer import FailureTextNormalizer
from ml.clustering.semantic_clusterer import SemanticFailureClusterer


def test_failure_text_normalizer():
    raw = "KeyError: 'user_id' at 2026-10-09T10:32:00Z for user 938472 in file /app/orders.py"
    normalized = FailureTextNormalizer.normalize_text(raw)

    assert "2026-10-09T10:32:00Z" not in normalized
    assert "<TIMESTAMP>" in normalized
    assert "938472" not in normalized
    assert "<ID>" in normalized


def test_semantic_failure_clusterer_dbscan():
    records = [
        {
            "result_id": "res_1",
            "test_case_id": "tc_1",
            "endpoint": "/orders",
            "error_message": "KeyError: 'discount' at 2026-10-09T10:00:00Z user 1111",
            "category": "SERVER_CRASH",
        },
        {
            "result_id": "res_2",
            "test_case_id": "tc_2",
            "endpoint": "/orders",
            "error_message": "KeyError: 'discount' at 2026-10-09T11:00:00Z user 2222",
            "category": "SERVER_CRASH",
        },
        {
            "result_id": "res_3",
            "test_case_id": "tc_3",
            "endpoint": "/auth",
            "error_message": "HTTP 401 Unauthorized token expired",
            "category": "AUTHENTICATION_FAILURE",
        },
    ]

    clusterer = SemanticFailureClusterer(eps=0.4, min_samples=2)
    clusters = clusterer.cluster_failures(records)

    assert len(clusters) >= 1
    # res_1 and res_2 should be grouped semantically into the same cluster
    res1_cluster = [c for c in clusters if "tc_1" in c.affected_test_ids][0]
    assert "tc_2" in res1_cluster.affected_test_ids
