"""Prioritization Metrics Evaluator (APFD vs Baseline Comparison)."""

from typing import List, Dict, Any
import pandas as pd

from ml.common.metrics import compute_apfd, compute_ndcg_at_k
from ml.common.schemas import PrioritizedItem
from ml.prioritization.baseline import HeuristicPrioritizerBaseline
from ml.prioritization.prioritizer import XGBoostTestPrioritizer


class PrioritizationEvaluator:
    @staticmethod
    def evaluate_model_vs_baselines(
        test_df: pd.DataFrame,
        trained_prioritizer: XGBoostTestPrioritizer,
    ) -> Dict[str, Any]:
        """
        Evaluates XGBoost model prioritization ordering against baselines (Heuristic, Random, Historical Rate).
        Computes APFD and NDCG@10 metrics.
        """
        if test_df.empty or "target_failed" not in test_df.columns:
            return {"status": "NO_DATA"}

        actual_fails = test_df[test_df["target_failed"] == 1]["test_case_id"].unique().tolist()

        # 1. Model Ranking
        model_rankings = trained_prioritizer.predict_priorities(test_df)
        model_order = [item.test_case_id for item in model_rankings]
        model_apfd = compute_apfd(model_order, actual_fails)

        # 2. Heuristic Baseline Ranking
        heuristic_rankings = HeuristicPrioritizerBaseline.rank_heuristic(test_df)
        heuristic_order = [item.test_case_id for item in heuristic_rankings]
        heuristic_apfd = compute_apfd(heuristic_order, actual_fails)

        # 3. Random Ranking Baseline
        all_test_ids = test_df["test_case_id"].unique().tolist()
        random_order = list(all_test_ids)
        import random
        random.seed(42)
        random.shuffle(random_order)
        random_apfd = compute_apfd(random_order, actual_fails)

        # 4. Compute NDCG@10 for model predictions
        predicted_probs = [item.failure_probability for item in model_rankings]
        actual_targets = [1 if item.test_case_id in actual_fails else 0 for item in model_rankings]
        ndcg_10 = compute_ndcg_at_k(actual_targets, predicted_probs, k=10)

        return {
            "model_apfd": float(model_apfd),
            "heuristic_apfd": float(heuristic_apfd),
            "random_apfd": float(random_apfd),
            "ndcg_at_10": float(ndcg_10),
            "total_test_cases": len(all_test_ids),
            "actual_failed_count": len(actual_fails),
            "model_beats_heuristic": bool(model_apfd >= heuristic_apfd),
            "model_beats_random": bool(model_apfd > random_apfd),
        }
