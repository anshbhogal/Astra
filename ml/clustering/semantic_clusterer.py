"""Cosine DBSCAN Semantic Failure Clusterer."""

import uuid
import numpy as np
from typing import List, Dict, Any
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

from ml.common.schemas import SemanticClusterResult
from ml.clustering.vectorizer import FailureVectorizer
from ml.clustering.normalizer import FailureTextNormalizer


class SemanticFailureClusterer:
    def __init__(self, eps: float = 0.35, min_samples: int = 2):
        self.eps = eps
        self.min_samples = min_samples
        self.vectorizer = FailureVectorizer()

    def cluster_failures(self, failure_records: List[Dict[str, Any]]) -> List[SemanticClusterResult]:
        """
        Cluster failures by stack trace & error message text similarity using TF-IDF + Cosine DBSCAN.
        failure_records dict list with:
          id/result_id, test_case_id, error_message, endpoint, category, fingerprint (optional)
        """
        if not failure_records:
            return []

        if len(failure_records) == 1:
            item = failure_records[0]
            fid = item.get("result_id") or item.get("id") or str(uuid.uuid4())
            t_id = item.get("test_case_id", "unknown_case")
            return [
                SemanticClusterResult(
                    cluster_id=f"cluster_{item.get('fingerprint', fid[:8])}",
                    cluster_name=f"Cluster {item.get('category', 'FAILURE')}",
                    affected_test_ids=[str(t_id)],
                    member_count=1,
                    match_precision="EXACT_MATCH",
                    representative_failure_id=str(fid),
                    confidence=1.0,
                )
            ]

        # Extract texts for vectorization
        texts = []
        for f in failure_records:
            ep = f.get("endpoint", "")
            err = f.get("error_message", "")
            cat = f.get("category", "")
            summary = f"{cat} {ep} {err}"
            texts.append(summary)

        matrix = self.vectorizer.vectorize_failures(texts)
        if matrix is None or matrix.shape[0] == 0:
            # Fallback grouping by fingerprint or category
            return self._fallback_cluster(failure_records)

        # Apply DBSCAN with cosine metric
        db = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="cosine")
        labels = db.fit_predict(matrix)

        clusters_dict: Dict[int, List[Dict[str, Any]]] = {}
        for idx, label in enumerate(labels):
            if label not in clusters_dict:
                clusters_dict[label] = []
            clusters_dict[label].append(failure_records[idx])

        results = []
        for label, group in clusters_dict.items():
            member_ids = [g.get("test_case_id") or g.get("result_id") for g in group]
            rep_id = str(group[0].get("result_id") or group[0].get("id") or uuid.uuid4())
            cat = group[0].get("category", "GENERIC_FAILURE")

            if label == -1:
                # Noise / Unclustered Outliers
                match_prec = "POSSIBLY_SAME"
                conf = 0.5
                c_name = f"Outlier Defect Group ({cat})"
                c_id = f"outlier_{uuid.uuid4().hex[:6]}"
            else:
                match_prec = "LIKELY_SAME"
                conf = 0.85
                c_name = f"Semantic Defect Cluster #{label} ({cat})"
                c_id = f"cluster_semantic_{label}_{uuid.uuid4().hex[:6]}"

            results.append(
                SemanticClusterResult(
                    cluster_id=c_id,
                    cluster_name=c_name,
                    affected_test_ids=[str(m) for m in member_ids],
                    member_count=len(group),
                    match_precision=match_prec,
                    representative_failure_id=rep_id,
                    confidence=conf,
                )
            )

        return results

    def _fallback_cluster(self, failure_records: List[Dict[str, Any]]) -> List[SemanticClusterResult]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for f in failure_records:
            fp = f.get("fingerprint") or f.get("category") or "DEFAULT"
            if fp not in groups:
                groups[fp] = []
            groups[fp].append(f)

        results = []
        for fp, group in groups.items():
            rep_id = str(group[0].get("result_id") or group[0].get("id") or uuid.uuid4())
            member_ids = [g.get("test_case_id") or g.get("result_id") for g in group]
            results.append(
                SemanticClusterResult(
                    cluster_id=f"cluster_fp_{fp[:8]}",
                    cluster_name=f"Cluster {group[0].get('category', 'DEFECT')}",
                    affected_test_ids=[str(m) for m in member_ids],
                    member_count=len(group),
                    match_precision="EXACT_MATCH" if len(group) > 1 else "POSSIBLY_SAME",
                    representative_failure_id=rep_id,
                    confidence=0.9 if len(group) > 1 else 0.6,
                )
            )
        return results
