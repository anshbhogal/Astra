import pytest
from engine.cicd.pr_commenter import PRCommenter
from engine.cicd.quality_gate import QualityGateResult
from engine.regression.selective_selector import SelectionResult, TestSelectionDetail


def test_pr_commenter_format():
    gate = QualityGateResult(
        status="PASS",
        blocking=False,
        total_tests=10,
        passed_tests=3,
        failed_tests=0,
        time_saved_ms=5000.0,
    )
    sel_res = SelectionResult(
        analysis_fingerprint="fp-1",
        total_suite_tests=10,
        selected_tier1_count=3,
        deferred_tier2_count=7,
        test_reduction_percent=70.0,
        estimated_time_avoided_ms=5000.0,
        impact_confidence=0.95,
        safety_expansion_triggered=False,
    )

    md = PRCommenter.format_pr_comment(gate, selection_result=sel_res)

    assert "🟢 ASTRA Quality Gate Report" in md
    assert "-70.0%" in md
    assert "Tier 1 Targeted" in md
