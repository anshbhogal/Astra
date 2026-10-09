"""Formal ASTRA Quality Gate Evaluation Engine.
Evaluates QualityGateResult status (PASS, FAIL, ERROR, BLOCKED, NEEDS_FULL_REGRESSION) to decouple
core engine decisions from external GitHub and notification dispatches.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class QualityGateResult:
    status: str  # PASS, FAIL, ERROR, BLOCKED, NEEDS_FULL_REGRESSION
    blocking: bool
    reason_codes: List[str] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    critical_failures: int = 0
    safety_expanded: bool = False
    time_saved_ms: float = 0.0


class QualityGateEvaluator:
    """Evaluates Quality Gate results based on test execution outcomes and safety triggers."""

    def __init__(self, block_on_non_critical: bool = True):
        self.block_on_non_critical = block_on_non_critical

    def evaluate(
        self,
        total_tests: int,
        passed_tests: int,
        failed_tests: int,
        critical_failures: int = 0,
        environment_error: bool = False,
        safety_expanded: bool = False,
        time_saved_ms: float = 0.0,
    ) -> QualityGateResult:
        """Evaluates overall Quality Gate status."""
        reason_codes: List[str] = []

        if environment_error:
            reason_codes.append("ENVIRONMENT_EXECUTION_ERROR")
            return QualityGateResult(
                status="ERROR",
                blocking=True,
                reason_codes=reason_codes,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                critical_failures=critical_failures,
                safety_expanded=safety_expanded,
                time_saved_ms=time_saved_ms,
            )

        if critical_failures > 0:
            reason_codes.append("CRITICAL_DEFECT_DETECTED")
            return QualityGateResult(
                status="FAIL",
                blocking=True,
                reason_codes=reason_codes,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                critical_failures=critical_failures,
                safety_expanded=safety_expanded,
                time_saved_ms=time_saved_ms,
            )

        if failed_tests > 0:
            reason_codes.append("TEST_FAILURES_DETECTED")
            blocking = self.block_on_non_critical
            return QualityGateResult(
                status="FAIL" if blocking else "BLOCKED",
                blocking=blocking,
                reason_codes=reason_codes,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                critical_failures=critical_failures,
                safety_expanded=safety_expanded,
                time_saved_ms=time_saved_ms,
            )

        if safety_expanded:
            reason_codes.append("SAFETY_EXPANSION_ACTIVATED")

        return QualityGateResult(
            status="PASS",
            blocking=False,
            reason_codes=reason_codes,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=0,
            critical_failures=0,
            safety_expanded=safety_expanded,
            time_saved_ms=time_saved_ms,
        )
