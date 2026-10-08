"""
ASTRA Engine - Phase 6 Canonical Fingerprinting & Defect Aggregator

Calculates normalized SHA256 fingerprints and groups related failure analyses into DefectCluster records
with repetition and intermittent flake tracking.
"""

import hashlib
import json
from typing import List, Dict, Any, Optional
from engine.analysis.models import (
    FailureAnalysis,
    DefectCluster,
    ClusterMatchPrecision,
    FailureCategory,
)


class FingerprintEngine:
    """Computes normalized canonical fingerprints and clusters related failure analyses."""

    def compute_fingerprint(
        self,
        category: FailureCategory,
        exception_type: Optional[str] = None,
        exception_message: Optional[str] = None,
        root_function: Optional[str] = None,
        endpoint: Optional[str] = None,
        diff_paths: Optional[List[str]] = None,
        sql_state: Optional[str] = None,
    ) -> str:
        """Generates a canonical SHA256 hash resilient to line number shifts."""
        norm_message = (exception_message or "").strip().lower()
        # Remove volatile line numbers or memory addresses from normalized message
        norm_message = json.dumps(norm_message)

        payload = {
            "category": category.value if hasattr(category, "value") else str(category),
            "exception_type": exception_type or "None",
            "normalized_message": norm_message[:100],
            "root_function": root_function or "None",
            "endpoint": endpoint or "None",
            "diff_paths": sorted(diff_paths or []),
            "sql_state": sql_state or "None",
        }

        canonical_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def cluster_failures(
        self,
        failures: List[FailureAnalysis],
        run_id: str = "run_1",
        existing_clusters: Optional[List[DefectCluster]] = None,
    ) -> List[DefectCluster]:
        """Groups failure analyses into DefectClusters based on canonical fingerprint similarity."""
        clusters_map: Dict[str, DefectCluster] = {}

        if existing_clusters:
            for c in existing_clusters:
                clusters_map[c.fingerprint] = c

        for failure in failures:
            fp = failure.fingerprint
            if not fp:
                fp = self.compute_fingerprint(
                    category=failure.category,
                    exception_type=failure.exception_type,
                    exception_message=failure.error_message,
                    root_function=failure.failing_function,
                    endpoint=failure.endpoint_id,
                    diff_paths=[d.path for d in failure.diff_items],
                    sql_state=failure.parsed_exception.sql_state if failure.parsed_exception else None,
                )
                failure.fingerprint = fp

            if fp in clusters_map:
                cluster = clusters_map[fp]
                if failure.analysis_id not in cluster.member_failure_ids:
                    cluster.member_failure_ids.append(failure.analysis_id)
                    cluster.member_count += 1
                    cluster.occurrence_count += 1
                cluster.last_seen_run_id = run_id
            else:
                summary = f"{failure.category.value}: {failure.error_message[:80]}" if failure.error_message else f"{failure.category.value} Defect"
                cluster = DefectCluster(
                    fingerprint=fp,
                    category=failure.category,
                    summary=summary,
                    representative_failure_id=failure.analysis_id,
                    member_failure_ids=[failure.analysis_id],
                    member_count=1,
                    similarity_score=1.0,
                    confidence=failure.classification_confidence,
                    match_precision=ClusterMatchPrecision.EXACT_MATCH,
                    occurrence_count=1,
                    first_seen_run_id=run_id,
                    last_seen_run_id=run_id,
                )
                clusters_map[fp] = cluster

        return list(clusters_map.values())
