"""Unit tests for Flakiness State Machine and Quarantine Recommendation."""

import pytest
from ml.flakiness.state_machine import FlakinessStateMachine
from ml.flakiness.flakiness_detector import FlakinessDetector
from ml.flakiness.quarantine import QuarantineManager


def test_state_machine_transition_analysis():
    sm = FlakinessStateMachine(observation_window=10, min_observations=8, min_transitions=2)

    # Oscillating sequence
    oscillating = ["PASS", "FAIL", "PASS", "FAIL", "PASS", "FAIL", "PASS", "FAIL"]
    res = sm.analyze_sequence(oscillating)
    assert res["observation_count"] == 8
    assert res["transition_count"] == 7
    assert res["has_sufficient_data"] is True

    # Stable sequence
    stable = ["PASS", "PASS", "PASS", "PASS", "PASS", "PASS", "PASS", "PASS"]
    res_s = sm.analyze_sequence(stable)
    assert res_s["transition_count"] == 0


def test_flakiness_detector_quarantine_trigger():
    detector = FlakinessDetector(fi_threshold=0.60)
    history = ["PASS", "FAIL", "PASS", "FAIL", "PASS", "FAIL", "PASS", "FAIL"]
    latencies = [100.0, 500.0, 100.0, 480.0, 110.0, 520.0, 105.0, 490.0]

    eval_res = detector.evaluate_test_case_flakiness("tc_flaky", history, latencies)
    assert eval_res.recommend_quarantine is True
    assert eval_res.flakiness_score >= 0.60
    assert eval_res.status == "RECOMMENDED_QUARANTINE"


def test_quarantine_manager_non_blocking():
    detector = FlakinessDetector(fi_threshold=0.50)
    history = ["PASS", "FAIL", "PASS", "FAIL", "PASS", "FAIL", "PASS", "FAIL"]
    latencies = [100.0, 500.0, 100.0, 500.0, 100.0, 500.0, 100.0, 500.0]
    eval_res = detector.evaluate_test_case_flakiness("tc_flaky", history, latencies)

    # Unapproved recommendation -> not non-blocking
    dec1 = QuarantineManager.process_quarantine_decision(eval_res, user_approved=False)
    assert dec1["status"] == "RECOMMENDED_QUARANTINE"
    assert dec1["is_non_blocking"] is False

    # Approved quarantine -> non-blocking
    dec2 = QuarantineManager.process_quarantine_decision(eval_res, user_approved=True)
    assert dec2["status"] == "QUARANTINED"
    assert dec2["is_non_blocking"] is True
