"""Flakiness Score Calculator & Detector Engine."""

import numpy as np
from typing import List, Dict, Any

from ml.common.schemas import FlakinessEvalResult
from ml.flakiness.state_machine import FlakinessStateMachine


class FlakinessDetector:
    def __init__(self, fi_threshold: float = 0.60):
        self.fi_threshold = fi_threshold
        self.state_machine = FlakinessStateMachine()

    def evaluate_test_case_flakiness(
        self,
        test_case_id: str,
        outcome_history: List[str],
        latency_history_ms: List[float],
        env_flake_count: int = 0,
    ) -> FlakinessEvalResult:
        """
        Calculates Flakiness Index (FI):
        FI = 0.5 * TransitionRate + 0.3 * (LatencyStd / (LatencyMean + 1)) + 0.2 * EnvFlakeRatio
        """
        sm_res = self.state_machine.analyze_sequence(outcome_history)

        obs_count = sm_res["observation_count"]
        transition_cnt = sm_res["transition_count"]
        has_sufficient = sm_res["has_sufficient_data"]
        trans_rate = sm_res["transition_rate"]

        if not latency_history_ms:
            lat_mean = 0.0
            lat_std = 0.0
        else:
            lat_mean = float(np.mean(latency_history_ms))
            lat_std = float(np.std(latency_history_ms)) if len(latency_history_ms) > 1 else 0.0

        latency_var_ratio = min(1.0, lat_std / (lat_mean + 1.0))
        env_ratio = min(1.0, env_flake_count / max(1, obs_count))

        # Flakiness Index calculation
        fi_score = 0.5 * trans_rate + 0.3 * latency_var_ratio + 0.2 * env_ratio

        # Determine quarantine recommendation
        recommend = False
        if has_sufficient and transition_cnt >= 2 and fi_score >= self.fi_threshold:
            recommend = True

        status = "RECOMMENDED_QUARANTINE" if recommend else "ACTIVE"

        return FlakinessEvalResult(
            test_case_id=test_case_id,
            flakiness_score=float(np.round(fi_score, 4)),
            observation_count=obs_count,
            transition_count=transition_cnt,
            pass_count=sm_res["pass_count"],
            fail_count=sm_res["fail_count"],
            latency_mean_ms=float(np.round(lat_mean, 2)),
            latency_std_ms=float(np.round(lat_std, 2)),
            recommend_quarantine=recommend,
            status=status,
        )
