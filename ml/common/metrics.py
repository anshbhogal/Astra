"""ML Ranking & Evaluation Metrics (APFD, APFDc, NDCG@K)."""

import numpy as np
from typing import List, Dict, Any


def compute_apfd(ordered_test_case_ids: List[str], failed_test_case_ids: List[str]) -> float:
    """
    Computes Average Percentage of Faults Detected (APFD).
    Formula: APFD = 1 - (sum(TF_i) / (n * m)) + (1 / (2 * n))
    n = total tests, m = total faults detected
    TF_i = position in rank order where fault i was first detected (1-indexed)
    """
    n = len(ordered_test_case_ids)
    if n == 0:
        return 0.0
    
    # Filter to unique failed test IDs present in the ordering
    unique_faults = set(failed_test_case_ids)
    m = len(unique_faults)
    if m == 0:
        return 1.0  # Perfect score if no faults existed

    tf_sum = 0
    for fault_id in unique_faults:
        try:
            rank_pos = ordered_test_case_ids.index(fault_id) + 1  # 1-indexed
        except ValueError:
            rank_pos = n  # Fallback if fault not in list
        tf_sum += rank_pos

    apfd = 1.0 - (tf_sum / (n * m)) + (1.0 / (2.0 * n))
    return max(0.0, min(1.0, float(apfd)))


def compute_apfd_distinct_faults(
    ordered_test_case_ids: List[str],
    test_fault_map: Dict[str, Any],
    all_active_faults: Any = None,
) -> Dict[str, Any]:
    """
    Computes Average Percentage of Faults Detected (APFD) using distinct ground-truth fault mappings.
    Formula: APFD = 1 - (sum(TF_i) / (n * m)) + (1 / (2 * n))
    where:
      n = total test cases in the prioritized suite
      m = total distinct faults exposed by the test suite (or active in cycle)
      TF_i = 1-based index in ordered_test_case_ids where fault i was FIRST detected
    """
    n = len(ordered_test_case_ids)
    if n == 0:
        return {
            "apfd": 0.0,
            "total_tests": 0,
            "distinct_faults_count": 0,
            "fault_first_detected_pos": {},
            "detected_faults": [],
            "undetected_faults": [],
        }

    # Normalize test_fault_map to Dict[str, Set[str]]
    normalized_map = {}
    all_detectable_faults = set()
    for tid, f_ids in test_fault_map.items():
        if isinstance(f_ids, (set, list, tuple)):
            f_set = set(f_ids)
        elif isinstance(f_ids, str):
            f_set = {f_ids}
        else:
            f_set = set()
        normalized_map[str(tid)] = f_set
        all_detectable_faults.update(f_set)

    # Determine universe of faults to evaluate
    if all_active_faults is not None:
        target_faults = set(all_active_faults)
    else:
        target_faults = all_detectable_faults

    m = len(target_faults)
    if m == 0:
        return {
            "apfd": 1.0,  # Zero-fault cycle
            "total_tests": n,
            "distinct_faults_count": 0,
            "fault_first_detected_pos": {},
            "detected_faults": [],
            "undetected_faults": [],
            "zero_fault_cycle": True,
        }

    # Find first position (1-indexed) where each fault was detected
    first_detected = {}
    for pos, test_id in enumerate(ordered_test_case_ids, start=1):
        detected_by_test = normalized_map.get(str(test_id), set())
        for fault_id in detected_by_test:
            if fault_id in target_faults and fault_id not in first_detected:
                first_detected[fault_id] = pos

    detected_faults = list(first_detected.keys())
    undetected_faults = [f for f in target_faults if f not in first_detected]

    # For undetected faults, assign penalty rank = (n + 1) (formal penalized APFD variant)
    penalty_rank = n + 1
    tf_sum = sum(first_detected.values()) + (len(undetected_faults) * penalty_rank)

    apfd = 1.0 - (tf_sum / (n * m)) + (1.0 / (2.0 * n))
    apfd_bounded = max(0.0, min(1.0, float(apfd)))

    return {
        "apfd": round(apfd_bounded, 4),
        "total_tests": n,
        "distinct_faults_count": m,
        "detected_faults_count": len(detected_faults),
        "fault_first_detected_pos": first_detected,
        "detected_faults": sorted(detected_faults),
        "undetected_faults": sorted(undetected_faults),
        "zero_fault_cycle": False,
        "metric_variant": "penalized_distinct_faults_apfd",
        "undetected_penalty_rank": penalty_rank,
    }


def compute_ndcg_at_k(actual_outcomes: List[int], predicted_scores: List[float], k: int = 10) -> float:
    """
    Computes Normalized Discounted Cumulative Gain at rank K (NDCG@K).
    
    Academic Evaluation Note:
    Relevance labels represent binary test-case failure outcomes (1 for failed test,
    0 for passed test), measuring failure prediction ranking density in the top-K slots,
    rather than distinct-fault coverage.
    
    actual_outcomes: 1 for FAIL, 0 for PASS
    predicted_scores: model failure probability predictions
    """
    if not actual_outcomes or not predicted_scores or len(actual_outcomes) != len(predicted_scores):
        return 0.0

    k = min(k, len(actual_outcomes))
    
    # Sort actual outcomes by predicted scores descending
    sorted_pairs = sorted(zip(predicted_scores, actual_outcomes), key=lambda x: x[0], reverse=True)
    top_k_outcomes = [pair[1] for pair in sorted_pairs[:k]]

    # DCG@K
    dcg = sum((2 ** rel - 1) / np.log2(idx + 2) for idx, rel in enumerate(top_k_outcomes))

    # Ideal DCG@K (sorted by true relevance descending)
    ideal_outcomes = sorted(actual_outcomes, reverse=True)[:k]
    idcg = sum((2 ** rel - 1) / np.log2(idx + 2) for idx, rel in enumerate(ideal_outcomes))

    if idcg == 0:
        return 1.0  # If no actual fails, ranking is trivially optimal
    return float(dcg / idcg)
