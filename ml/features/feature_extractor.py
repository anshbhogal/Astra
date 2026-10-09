"""Feature Extractor & Feature Vector Generator."""

import math
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional

CATEGORY_SEVERITY_MAP = {
    "SERVER_CRASH": 1.0,
    "DATABASE_ERROR": 0.9,
    "DEPENDENCY_FAILURE": 0.85,
    "CONTRACT_VIOLATION": 0.8,
    "BUSINESS_LOGIC_DEFECT": 0.75,
    "TIMEOUT_PERFORMANCE": 0.7,
    "AUTHENTICATION_FAILURE": 0.65,
    "AUTHORIZATION_FAILURE": 0.65,
    "REQUEST_VALIDATION_ERROR": 0.6,
    "RESOURCE_NOT_FOUND": 0.55,
    "METHOD_NOT_ALLOWED": 0.5,
    "ENVIRONMENT_FLAKE": 0.3,
    "UNKNOWN_FAILURE": 0.4,
}


class FeatureExtractor:
    @staticmethod
    def extract_features_from_history(historical_results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Converts raw database test run history into ML feature vectors, ensuring strict temporal isolation.
        historical_results list of dicts with:
          test_case_id, test_run_id, outcome ('FAIL', 'PASS'), execution_time_ms, created_at, category (optional), code_churn (optional)
        """
        if not historical_results:
            return pd.DataFrame()

        df = pd.DataFrame(historical_results)
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"])
            df = df.sort_values(by="created_at", ascending=True).reset_index(drop=True)

        rows = []
        # Group by test_case_id and compute rolling prior metrics for each run
        for test_case_id, group in df.groupby("test_case_id"):
            group_rows = group.to_dict("records")
            for i, current_run in enumerate(group_rows):
                prior_runs = group_rows[:i]  # Strictly prior runs (prevents data leakage)

                if not prior_runs:
                    # Cold-Start defaults for the first run
                    hist_fail_rate = 0.0
                    recent_fail_rate = 0.0
                    transition_entropy = 0.0
                    avg_latency = float(current_run.get("execution_time_ms", 100.0))
                    latency_std = 0.0
                else:
                    outcomes = [r.get("outcome", "PASS") for r in prior_runs]
                    latencies = [float(r.get("execution_time_ms", 100.0)) for r in prior_runs]

                    fails = sum(1 for o in outcomes if o == "FAIL")
                    hist_fail_rate = fails / len(outcomes)

                    # Last 5 runs
                    recent_outcomes = outcomes[-5:]
                    recent_fail_rate = sum(1 for o in recent_outcomes if o == "FAIL") / len(recent_outcomes)

                    # Transition count (PASS -> FAIL or FAIL -> PASS)
                    transitions = sum(1 for j in range(1, len(outcomes)) if outcomes[j] != outcomes[j - 1])
                    transition_entropy = transitions / max(1, len(outcomes) - 1)

                    avg_latency = float(np.mean(latencies))
                    latency_std = float(np.std(latencies)) if len(latencies) > 1 else 0.0

                category = current_run.get("category", "UNKNOWN_FAILURE")
                severity_weight = CATEGORY_SEVERITY_MAP.get(category, 0.5)
                code_churn = float(current_run.get("code_churn", 0.0))
                target_failed = 1 if current_run.get("outcome") == "FAIL" else 0

                rows.append({
                    "sample_id": f"{test_case_id}_{current_run.get('test_run_id', i)}",
                    "project_id": str(current_run.get("project_id", "")),
                    "test_case_id": str(test_case_id),
                    "test_run_id": str(current_run.get("test_run_id", "")),
                    "commit_sha": current_run.get("commit_sha"),
                    "created_at": current_run.get("created_at"),
                    "historical_failure_rate_prev": float(np.round(hist_fail_rate, 4)),
                    "recent_failure_rate_5runs": float(np.round(recent_fail_rate, 4)),
                    "transition_entropy_prev": float(np.round(transition_entropy, 4)),
                    "avg_latency_prev_ms": float(np.round(avg_latency, 2)),
                    "latency_std_prev_ms": float(np.round(latency_std, 2)),
                    "category_severity_weight": float(severity_weight),
                    "code_churn_score": float(code_churn),
                    "target_failed": target_failed,
                })

        res_df = pd.DataFrame(rows)
        if "created_at" in res_df.columns:
            res_df = res_df.sort_values(by="created_at", ascending=True).reset_index(drop=True)
        return res_df
