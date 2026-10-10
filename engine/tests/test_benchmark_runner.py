"""Unit tests for BenchmarkRunner, BugMatcher, and AblationModes."""

import pytest
from engine.evaluation.ablation_modes import OperationalMode, TestBudget, AblationModeGenerator
from engine.evaluation.bug_matcher import BugMatcher
from engine.evaluation.execution_profiles import ProfileExecutionResult
from engine.evaluation.benchmark_runner import BenchmarkRunner
from benchmark_apps.catalog import BenchmarkBugCatalog, DefectCategory, DefectSeverity, GroundTruthBug


def test_ablation_mode_generator():
    """Verify test scenarios generated across all 5 operational modes."""
    modes = [
        OperationalMode.MODE_0_BASELINE,
        OperationalMode.MODE_A_RULES,
        OperationalMode.MODE_B_ML,
        OperationalMode.MODE_C_AI,
        OperationalMode.MODE_D_HYBRID,
    ]

    for mode in modes:
        scenarios = AblationModeGenerator.generate_scenarios_for_mode(mode)
        assert len(scenarios) > 0
        assert all(s.service in ("auth", "ecommerce", "student", "banking") for s in scenarios)


def test_bug_matcher_three_states():
    """Verify Triggered, Detected, Attributed states in BugMatcher."""
    sample_bug = BenchmarkBugCatalog.get_bug("BUG-AUTH-001")
    assert sample_bug is not None

    # Case 1: Defect triggered and detected (200 OK bypass observed instead of expected 401)
    res_detected = ProfileExecutionResult(
        status_code=200,
        response_data={"authenticated": True, "token": "token_admin_override"},
        execution_time_ms=45.0
    )
    match1 = BugMatcher.match_execution(sample_bug, res_detected)
    assert match1.is_triggered is True
    assert match1.is_detected is True
    assert match1.is_attributed is True
    assert match1.attribution_confidence >= 0.70

    # Case 2: Clean expected response (401 Unauthorized as expected -> not a defect)
    res_clean = ProfileExecutionResult(
        status_code=401,
        response_data={"detail": "Unauthorized"},
        execution_time_ms=25.0
    )
    match2 = BugMatcher.match_execution(sample_bug, res_clean)
    assert match2.is_detected is False


@pytest.mark.asyncio
async def test_benchmark_runner_mode_d_and_mode_0():
    """Verify BenchmarkRunner executes and computes confusion matrix metrics correctly."""
    # Run Mode D (Hybrid ASTRA)
    report_d = await BenchmarkRunner.run_evaluation(
        mode=OperationalMode.MODE_D_HYBRID,
        budget=TestBudget(max_tests=50, is_constrained=False),
        repetitions=1,
        seed=42
    )

    # Confusion matrix integrity
    assert report_d.total_injected_bugs == 50
    assert report_d.true_positives + report_d.false_negatives == 50
    assert report_d.true_positives > 0
    assert report_d.recall > 80.0  # Hybrid ASTRA achieves high recall
    assert report_d.specificity >= 90.0
    assert report_d.category_coverage > 70.0
    assert len(report_d.bug_results) == 50

    # Run Mode 0 (Baseline)
    report_0 = await BenchmarkRunner.run_evaluation(
        mode=OperationalMode.MODE_0_BASELINE,
        budget=TestBudget(max_tests=50, is_constrained=False),
        repetitions=1,
        seed=42
    )
    assert report_0.true_positives + report_0.false_negatives == 50
    # Mode D recall must strictly exceed Mode 0 recall (validating Hypothesis H1)
    assert report_d.recall > report_0.recall
