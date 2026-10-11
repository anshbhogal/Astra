"""
ASTRA Engine - Zero-Observed-Regression Safety Gate & Candidate Ranking

Validates plausible candidate patches against the defect test and Phase 8 Tier 1
Selective Regression suite, rejecting any regressions and ranking surviving candidates.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from engine.repair.patch_validator import PatchSanityResult
from engine.repair.sandbox_executor import ExecutionResult, SandboxExecutor


@dataclass
class CandidateVerificationReport:
    candidate_hash: str
    plausible: bool                         # Did defect test flip to PASS?
    defect_test_duration_ms: float
    static_analysis_passed: bool
    regression_passed: bool                 # 0 regressions observed
    regressions_count: int
    regression_tests_total: int
    regression_tests_passed: int
    regression_tests_failed: int
    regression_tests_error: int
    regression_tests_timeout: int
    complexity_delta: int
    ranking_score: float
    verified: bool                          # Meets all criteria for PR
    rejection_reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class ZeroObservedRegressionGate:
    """Enforces mathematical zero-regression gate and computes multi-factor ranking."""

    def __init__(
        self,
        weight_test_adequacy: float = 0.35,
        weight_regression_safety: float = 0.35,
        weight_fault_conf: float = 0.15,
        weight_minimality: float = 0.10,
        weight_complexity: float = 0.05,
    ):
        self.w1 = weight_test_adequacy
        self.w2 = weight_regression_safety
        self.w3 = weight_fault_conf
        self.w4 = weight_minimality
        self.w5 = weight_complexity

    def calculate_score(
        self,
        test_adequate: bool,
        regression_safe: bool,
        fault_confidence: float,
        lines_changed: int,
        complexity_delta: int,
    ) -> float:
        """
        Computes ranking score:
        w1*Adequacy + w2*Safety + w3*Confidence + w4*(1-LineDiffNorm) - w5*Complexity
        """
        s_adequacy = 1.0 if test_adequate else 0.0
        s_safety = 1.0 if regression_safe else 0.0
        s_conf = max(0.0, min(1.0, fault_confidence))
        s_minimality = max(0.0, 1.0 - min(1.0, lines_changed / 50.0))
        s_complexity = max(0.0, min(1.0, complexity_delta / 10.0))

        score = (
            self.w1 * s_adequacy
            + self.w2 * s_safety
            + self.w3 * s_conf
            + self.w4 * s_minimality
            - self.w5 * s_complexity
        )
        return round(score, 4)

    async def verify_candidate(
        self,
        sandbox: SandboxExecutor,
        target_rel_path: str,
        diff_text: str,
        sanity_result: PatchSanityResult,
        defect_test_cmd: str,
        regression_test_cmds: List[str],
        fault_confidence: float = 0.90,
    ) -> CandidateVerificationReport:
        """
        Executes end-to-end sandbox verification:
        1. Applies patch to sandbox.
        2. Executes defect test (must flip to PASS).
        3. Executes Tier 1 regression suite (0 regressions allowed).
        4. Calculates ranking score.
        """
        cand_hash = sanity_result.candidate_hash

        # Step 0: Apply patch
        applied, msg = await sandbox.apply_patch(target_rel_path, diff_text)
        if not applied:
            return CandidateVerificationReport(
                candidate_hash=cand_hash,
                plausible=False,
                defect_test_duration_ms=0.0,
                static_analysis_passed=False,
                regression_passed=False,
                regressions_count=0,
                regression_tests_total=0,
                regression_tests_passed=0,
                regression_tests_failed=0,
                regression_tests_error=0,
                regression_tests_timeout=0,
                complexity_delta=sanity_result.complexity_delta,
                ranking_score=0.0,
                verified=False,
                rejection_reason=f"Failed to apply patch in sandbox: {msg}",
            )

        # Step 1: Plausibility Verification (Defect Test)
        defect_res = await sandbox.run_test_command(defect_test_cmd)
        if not defect_res.passed:
            reason = "Defect test timed out." if defect_res.timed_out else "Defect test failed to pass with proposed patch."
            return CandidateVerificationReport(
                candidate_hash=cand_hash,
                plausible=False,
                defect_test_duration_ms=defect_res.duration_ms,
                static_analysis_passed=sanity_result.syntax_valid,
                regression_passed=False,
                regressions_count=0,
                regression_tests_total=0,
                regression_tests_passed=0,
                regression_tests_failed=0,
                regression_tests_error=0,
                regression_tests_timeout=0,
                complexity_delta=sanity_result.complexity_delta,
                ranking_score=0.0,
                verified=False,
                rejection_reason=reason,
                details={"defect_test_stdout": defect_res.stdout, "defect_test_stderr": defect_res.stderr},
            )

        plausible = True

        # Step 2: Complexity & Code Quality Gate
        if sanity_result.complexity_delta > 30:
            return CandidateVerificationReport(
                candidate_hash=cand_hash,
                plausible=True,
                defect_test_duration_ms=defect_res.duration_ms,
                static_analysis_passed=False,
                regression_passed=False,
                regressions_count=0,
                regression_tests_total=0,
                regression_tests_passed=0,
                regression_tests_failed=0,
                regression_tests_error=0,
                regression_tests_timeout=0,
                complexity_delta=sanity_result.complexity_delta,
                ranking_score=0.0,
                verified=False,
                rejection_reason=f"Excessive complexity expansion (delta: {sanity_result.complexity_delta} > 30 lines).",
            )

        # Step 3: Zero-Observed-Regression Gate (Tier 1 Selective Regression)
        total_reg = len(regression_test_cmds)
        passed_reg = 0
        failed_reg = 0
        timeout_reg = 0

        for r_cmd in regression_test_cmds:
            r_res = await sandbox.run_test_command(r_cmd)
            if r_res.passed:
                passed_reg += 1
            elif r_res.timed_out:
                timeout_reg += 1
                failed_reg += 1
            else:
                failed_reg += 1

        regressions_observed = (failed_reg > 0)
        regression_passed = not regressions_observed

        # Step 4: Multi-Factor Ranking Score
        lines_changed = sanity_result.lines_added + sanity_result.lines_removed
        ranking_score = self.calculate_score(
            test_adequate=plausible,
            regression_safe=regression_passed,
            fault_confidence=fault_confidence,
            lines_changed=lines_changed,
            complexity_delta=sanity_result.complexity_delta,
        )

        verified = (plausible and regression_passed)
        rejection_reason = None
        if not regression_passed:
            rejection_reason = f"Zero-Observed-Regression Gate breached: {failed_reg}/{total_reg} regression tests failed."

        return CandidateVerificationReport(
            candidate_hash=cand_hash,
            plausible=plausible,
            defect_test_duration_ms=defect_res.duration_ms,
            static_analysis_passed=True,
            regression_passed=regression_passed,
            regressions_count=failed_reg,
            regression_tests_total=total_reg,
            regression_tests_passed=passed_reg,
            regression_tests_failed=failed_reg,
            regression_tests_error=0,
            regression_tests_timeout=timeout_reg,
            complexity_delta=sanity_result.complexity_delta,
            ranking_score=ranking_score,
            verified=verified,
            rejection_reason=rejection_reason,
            details={
                "defect_test_passed": True,
                "tier1_tests_total": total_reg,
                "tier1_tests_passed": passed_reg,
            },
        )
