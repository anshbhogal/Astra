"""Deterministic Heuristic Prioritization Baselines."""

import random
import numpy as np
import pandas as pd
from typing import List, Dict, Any

from ml.common.schemas import PrioritizedItem, RankingStrategy


class HeuristicPrioritizerBaseline:
    """
    Computes deterministic priority scores when ML models are un-trained or data volume is insufficient (< 50 runs).
    """

    @staticmethod
    def rank_heuristic(
        features_df: pd.DataFrame,
        strategy: str = RankingStrategy.BALANCED.value,
    ) -> List[PrioritizedItem]:
        if features_df.empty:
            return []

        df = features_df.copy()

        # Heuristic failure risk = 0.5 * recent_rate + 0.3 * hist_rate + 0.2 * severity
        df["heuristic_failure_risk"] = (
            0.5 * df["recent_failure_rate_5runs"] +
            0.3 * df["historical_failure_rate_prev"] +
            0.2 * df["category_severity_weight"]
        )

        items = []
        for idx, row in df.iterrows():
            cost_ms = max(1.0, float(row.get("avg_latency_prev_ms", 100.0)))
            risk = float(row["heuristic_failure_risk"])
            sev = float(row.get("category_severity_weight", 0.5))

            if strategy == RankingStrategy.RISK_FIRST.value:
                score = risk
                rationale = f"Risk-First strategy: Heuristic failure probability {risk*100:.1f}%"
            elif strategy == RankingStrategy.FAST_FEEDBACK.value:
                score = risk / (cost_ms / 1000.0 + 0.1)
                rationale = f"Fast-Feedback strategy: High risk ({risk*100:.1f}%) with low latency ({cost_ms:.0f}ms)"
            elif strategy == RankingStrategy.SEVERITY_FIRST.value:
                score = risk * sev
                rationale = f"Severity-First strategy: Risk {risk*100:.1f}% weighted by severity {sev:.2f}"
            else:  # BALANCED
                score = (risk * sev) / (cost_ms / 1000.0 + 0.5)
                rationale = f"Balanced strategy: Failure risk {risk*100:.1f}%, severity {sev:.2f}, latency {cost_ms:.0f}ms"

            items.append({
                "test_case_id": str(row["test_case_id"]),
                "failure_probability": float(np.round(risk, 4)),
                "execution_cost_ms": float(np.round(cost_ms, 2)),
                "severity_weight": float(np.round(sev, 2)),
                "priority_score": float(np.round(score, 4)),
                "strategy": strategy,
                "rationale": rationale,
            })

        # Sort descending by priority_score
        items.sort(key=lambda x: x["priority_score"], reverse=True)
        
        results = []
        for rank, item in enumerate(items, start=1):
            results.append(
                PrioritizedItem(
                    test_case_id=item["test_case_id"],
                    failure_probability=item["failure_probability"],
                    execution_cost_ms=item["execution_cost_ms"],
                    severity_weight=item["severity_weight"],
                    priority_score=item["priority_score"],
                    rank_order=rank,
                    strategy=item["strategy"],
                    rationale=item["rationale"],
                )
            )

        return results
