"""Unit tests for ML Dataset Builder, Feature Extractor, and Temporal Splitter."""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from ml.features.feature_extractor import FeatureExtractor
from ml.dataset.temporal_split import TemporalSplitter
from ml.dataset.validator import LeakageValidator


def test_feature_extractor_cold_start():
    results = [
        {
            "test_case_id": "tc_1",
            "test_run_id": "run_1",
            "outcome": "PASS",
            "execution_time_ms": 120.0,
            "created_at": datetime.now() - timedelta(days=2),
            "category": "UNKNOWN_FAILURE",
        }
    ]
    df = FeatureExtractor.extract_features_from_history(results)
    assert not df.empty
    assert len(df) == 1
    assert df.iloc[0]["historical_failure_rate_prev"] == 0.0
    assert df.iloc[0]["target_failed"] == 0


def test_feature_extractor_rolling_isolation():
    now = datetime.now()
    results = [
        {"test_case_id": "tc_1", "test_run_id": "run_1", "outcome": "FAIL", "execution_time_ms": 100.0, "created_at": now - timedelta(days=5)},
        {"test_case_id": "tc_1", "test_run_id": "run_2", "outcome": "PASS", "execution_time_ms": 150.0, "created_at": now - timedelta(days=4)},
        {"test_case_id": "tc_1", "test_run_id": "run_3", "outcome": "FAIL", "execution_time_ms": 200.0, "created_at": now - timedelta(days=3)},
    ]
    df = FeatureExtractor.extract_features_from_history(results)
    assert len(df) == 3

    # Run 1: Cold start -> 0.0 prior failure rate
    assert df.iloc[0]["historical_failure_rate_prev"] == 0.0
    # Run 2: Prior run 1 was FAIL -> 1.0 prior failure rate
    assert df.iloc[1]["historical_failure_rate_prev"] == 1.0
    # Run 3: Prior runs 1 and 2 were FAIL, PASS -> 0.5 prior failure rate
    assert df.iloc[2]["historical_failure_rate_prev"] == 0.5


def test_temporal_splitter_chronology():
    now = datetime.now()
    rows = []
    for i in range(10):
        rows.append({
            "test_case_id": f"tc_{i}",
            "created_at": now + timedelta(hours=i),
            "target_failed": i % 2,
        })
    df = pd.DataFrame(rows)

    train_df, val_df, test_df = TemporalSplitter.split_by_run_chronology(df, train_ratio=0.6, val_ratio=0.2)

    assert len(train_df) == 6
    assert len(val_df) == 2
    assert len(test_df) == 2


def test_leakage_validator_pass():
    df = pd.DataFrame({
        "historical_failure_rate_prev": [0.1, 0.2, 0.5],
        "target_failed": [0, 1, 0]
    })
    assert LeakageValidator.assert_no_data_leakage(df) is True
