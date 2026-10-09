"""Unit tests for ML Test Prioritizer, Baseline, and APFD Metric Calculation."""

import pytest
import pandas as pd
from ml.prioritization.prioritizer import XGBoostTestPrioritizer
from ml.prioritization.baseline import HeuristicPrioritizerBaseline
from ml.common.metrics import compute_apfd, compute_ndcg_at_k
from ml.common.schemas import RankingStrategy


def test_apfd_metric_calculation():
    ordered = ["tc_1", "tc_2", "tc_3", "tc_4", "tc_5"]
    faults = ["tc_1", "tc_3"]

    # Faults detected at position 1 and 3 out of 5 tests (2 faults total)
    # APFD = 1 - ( (1 + 3) / (5 * 2) ) + (1 / (2 * 5)) = 1 - 0.4 + 0.1 = 0.7
    apfd = compute_apfd(ordered, faults)
    assert pytest.approx(apfd, 0.01) == 0.7


def test_heuristic_baseline_ranking():
    df = pd.DataFrame([
        {"test_case_id": "tc_low", "recent_failure_rate_5runs": 0.0, "historical_failure_rate_prev": 0.0, "category_severity_weight": 0.3, "avg_latency_prev_ms": 100.0},
        {"test_case_id": "tc_high", "recent_failure_rate_5runs": 0.8, "historical_failure_rate_prev": 0.9, "category_severity_weight": 1.0, "avg_latency_prev_ms": 50.0},
    ])

    rankings = HeuristicPrioritizerBaseline.rank_heuristic(df, strategy=RankingStrategy.RISK_FIRST.value)
    assert len(rankings) == 2
    assert rankings[0].test_case_id == "tc_high"
    assert rankings[0].rank_order == 1
    assert rankings[1].test_case_id == "tc_low"


def test_xgboost_prioritizer_train_and_predict(tmp_path):
    rows = []
    for i in range(20):
        rows.append({
            "sample_id": f"s_{i}",
            "project_id": "proj_1",
            "test_case_id": f"tc_{i % 5}",
            "test_run_id": f"run_{i}",
            "commit_sha": "abc",
            "historical_failure_rate_prev": (i % 5) / 5.0,
            "recent_failure_rate_5runs": (i % 5) / 5.0,
            "transition_entropy_prev": 0.2,
            "avg_latency_prev_ms": 100.0 + (i * 10),
            "latency_std_prev_ms": 10.0,
            "category_severity_weight": 0.8,
            "code_churn_score": 0.1,
            "target_failed": 1 if (i % 5) >= 3 else 0,
        })
    df = pd.DataFrame(rows)

    prioritizer = XGBoostTestPrioritizer(model_dir=str(tmp_path))
    train_res = prioritizer.train(df)

    assert train_res["status"] == "TRAINED"
    assert prioritizer.is_trained is True

    # Save & Load
    file_path = prioritizer.save_model("proj_1", version="v1.0")
    assert prioritizer.load_model("proj_1", version="v1.0") is True

    # Predict
    test_df = df.iloc[:5].copy()
    items = prioritizer.predict_priorities(test_df)
    assert len(items) == 5
    assert items[0].rank_order == 1
