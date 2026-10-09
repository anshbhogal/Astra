"""Dynamic Tiered Selective Selector & Metrics Engine.
Partitions test suites into Tier 1 Targeted (immediate execution) and Tier 2 Deferred Full (scheduled execution).
Calculates telemetry metrics (reduction %, estimated time saved, confidence score, machine-readable rationale).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional
from engine.regression.test_impact_mapper import MappedTestCase
from engine.regression.safety_gate import SafetyCheckResult


@dataclass
class TestSelectionDetail:
    test_case_id: str
    name: str
    tier: str  # TIER1_TARGETED, TIER2_DEFERRED_FULL
    selection_reason: str
    confidence: float
    estimated_duration_ms: float = 100.0


@dataclass
class SelectionResult:
    analysis_fingerprint: str
    total_suite_tests: int
    selected_tier1_count: int
    deferred_tier2_count: int
    test_reduction_percent: float
    estimated_time_avoided_ms: float
    impact_confidence: float
    safety_expansion_triggered: bool
    tier1_test_details: List[TestSelectionDetail] = field(default_factory=list)
    tier2_test_details: List[TestSelectionDetail] = field(default_factory=list)
    analysis_warnings: List[str] = field(default_factory=list)


class SelectiveSelector:
    """Selects Tier 1 targeted tests and defers Tier 2 full tests with full explainability and metrics."""

    def __init__(self, default_test_duration_ms: float = 120.0):
        self.default_test_duration_ms = default_test_duration_ms

    def select_tests(
        self,
        analysis_fingerprint: str,
        all_test_cases: List[Dict[str, Any]],
        mapped_impacted_tests: List[MappedTestCase],
        safety_result: SafetyCheckResult,
    ) -> SelectionResult:
        """Partitions all test cases into Tier 1 Targeted vs Tier 2 Deferred Full."""
        total_suite_tests = len(all_test_cases)
        if total_suite_tests == 0:
            return SelectionResult(
                analysis_fingerprint=analysis_fingerprint,
                total_suite_tests=0,
                selected_tier1_count=0,
                deferred_tier2_count=0,
                test_reduction_percent=0.0,
                estimated_time_avoided_ms=0.0,
                impact_confidence=1.0,
                safety_expansion_triggered=False,
            )

        mapped_dict = {m.test_case_id: m for m in mapped_impacted_tests}
        tier1_ids: Set[str] = set(mapped_dict.keys()).union(safety_result.expanded_test_ids)

        tier1_details: List[TestSelectionDetail] = []
        tier2_details: List[TestSelectionDetail] = []

        total_saved_ms = 0.0

        for tc in all_test_cases:
            tc_id = str(tc["id"])
            tc_name = tc.get("name", f"Test_{tc_id[:8]}")
            duration_ms = float(tc.get("avg_duration_ms", self.default_test_duration_ms))

            if tc_id in tier1_ids:
                mapped = mapped_dict.get(tc_id)
                if mapped:
                    reason = f"Impacted by route {mapped.method} {mapped.endpoint} via {mapped.match_strategy} (dist={mapped.impact_distance})"
                    conf = mapped.impact_confidence
                elif safety_result.expansion_triggered:
                    reason = f"Selected via Safety Expansion: {safety_result.expansion_reason}"
                    conf = max(0.5, 1.0 - safety_result.confidence_penalty)
                else:
                    reason = "Directly targeted by change impact analysis"
                    conf = 0.9

                tier1_details.append(TestSelectionDetail(
                    test_case_id=tc_id,
                    name=tc_name,
                    tier="TIER1_TARGETED",
                    selection_reason=reason,
                    confidence=conf,
                    estimated_duration_ms=duration_ms,
                ))
            else:
                reason = "No direct or indirect PKG reachability from commit diff; deferred to scheduled full regression run"
                tier2_details.append(TestSelectionDetail(
                    test_case_id=tc_id,
                    name=tc_name,
                    tier="TIER2_DEFERRED_FULL",
                    selection_reason=reason,
                    confidence=1.0,
                    estimated_duration_ms=duration_ms,
                ))
                total_saved_ms += duration_ms

        selected_count = len(tier1_details)
        deferred_count = len(tier2_details)
        reduction_pct = round(((total_suite_tests - selected_count) / total_suite_tests) * 100.0, 2)

        # Base confidence calculation
        if mapped_impacted_tests:
            base_conf = sum(m.impact_confidence for m in mapped_impacted_tests) / len(mapped_impacted_tests)
        else:
            base_conf = 1.0 if selected_count == 0 else 0.85

        final_conf = max(0.4, round(base_conf - safety_result.confidence_penalty, 2))

        warnings = []
        if safety_result.expansion_triggered and safety_result.expansion_reason:
            warnings.append(safety_result.expansion_reason)

        return SelectionResult(
            analysis_fingerprint=analysis_fingerprint,
            total_suite_tests=total_suite_tests,
            selected_tier1_count=selected_count,
            deferred_tier2_count=deferred_count,
            test_reduction_percent=reduction_pct,
            estimated_time_avoided_ms=total_saved_ms,
            impact_confidence=final_conf,
            safety_expansion_triggered=safety_result.expansion_triggered,
            tier1_test_details=tier1_details,
            tier2_test_details=tier2_details,
            analysis_warnings=warnings,
        )
