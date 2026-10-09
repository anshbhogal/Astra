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


def compute_ndcg_at_k(actual_outcomes: List[int], predicted_scores: List[float], k: int = 10) -> float:
    """
    Computes Normalized Discounted Cumulative Gain at rank K (NDCG@K).
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
