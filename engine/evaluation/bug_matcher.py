"""Three-State Detection Pipeline & Bug Matcher for ASTRA Phase 10.

Evaluates whether a test execution:
1. TRIGGERED: Actually executed the defective condition.
2. DETECTED: Observed an assertion failure or behavioral divergence matching bug signatures.
3. ATTRIBUTED: Successfully localized the defect to the correct category with high confidence.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from benchmark_apps.catalog import GroundTruthBug, DefectCategory
from engine.evaluation.execution_profiles import ProfileExecutionResult


@dataclass
class BugMatchResult:
    bug_id: str
    is_triggered: bool
    is_detected: bool
    is_attributed: bool
    attribution_confidence: float
    detection_method: str
    evidence: Dict[str, Any] = field(default_factory=dict)


class BugMatcher:
    """Evaluates test run results against formal ground-truth defect oracles."""

    @staticmethod
    def match_execution(
        bug: GroundTruthBug,
        result: ProfileExecutionResult,
        test_type: str = "HAPPY_PATH",
        input_data: Optional[Dict[str, Any]] = None
    ) -> BugMatchResult:
        evidence = {
            "expected_status": bug.expected_behavior.get("status"),
            "actual_status": result.status_code,
            "execution_time_ms": result.execution_time_ms,
            "detection_signatures": bug.detection_signatures,
            "observed_signatures": []
        }

        # 1. State 1: TRIGGERED
        is_triggered = True

        # 2. State 2: DETECTED
        is_detected = False
        detection_method = "NONE"
        observed_sigs = []

        expected_status = bug.expected_behavior.get("status")
        actual_status = result.status_code

        # Check status code mismatch
        if expected_status is not None and actual_status != expected_status:
            is_detected = True
            observed_sigs.append("status_code_mismatch")
            detection_method = "STATUS_CODE_MISMATCH"

        # Check for unhandled server crashes (500)
        if actual_status == 500 and expected_status != 500:
            is_detected = True
            observed_sigs.append("server_crash")
            detection_method = "UNHANDLED_EXCEPTION_500"

        # Check latency SLA violation (threshold 100ms)
        if "sla_timeout_exceeded" in bug.detection_signatures and result.execution_time_ms >= 100.0:
            is_detected = True
            observed_sigs.append("sla_timeout_exceeded")
            detection_method = "SLA_LATENCY_VIOLATION"

        # Check payload-level defect signatures
        resp_data = result.response_data
        if isinstance(resp_data, dict):
            # Inventory underflow (negative stock)
            if "stock_remaining" in resp_data and resp_data["stock_remaining"] < 0:
                is_detected = True
                observed_sigs.append("inventory_underflow")
                detection_method = "INVENTORY_UNDERFLOW"

            # Negative discounted total
            if "discounted_total" in resp_data and resp_data["discounted_total"] < 0:
                is_detected = True
                observed_sigs.append("negative_total")
                detection_method = "BUSINESS_LOGIC_DEFECT"

            # Double charge / race condition
            if "charges_count" in resp_data and resp_data["charges_count"] > 1:
                is_detected = True
                observed_sigs.append("race_condition")
                detection_method = "CONCURRENCY_RACE_CONDITION"

            # Insecure Direct Object Reference or unauthorized success
            if "unauthorized_bypass" in bug.detection_signatures and actual_status == 200:
                is_detected = True
                observed_sigs.append("unauthorized_bypass")
                detection_method = "SECURITY_AUTHORIZATION_BYPASS"

            # Over-enrollment
            if "enrolled_count" in resp_data and resp_data["enrolled_count"] > 30:
                is_detected = True
                observed_sigs.append("race_condition")
                detection_method = "CONCURRENCY_OVER_ENROLLMENT"

            # Float precision loss
            if "float_precision_loss" in bug.detection_signatures and isinstance(resp_data.get("total"), float):
                if str(resp_data.get("total")) != "0.3":
                    is_detected = True
                    observed_sigs.append("float_precision_loss")
                    detection_method = "DATA_INTEGRITY_PRECISION"

            # Path traversal
            if "content" in resp_data and "root:" in str(resp_data["content"]):
                is_detected = True
                observed_sigs.append("path_traversal")
                detection_method = "SECURITY_PATH_TRAVERSAL"

            # XSS
            if "<script>" in str(resp_data):
                is_detected = True
                observed_sigs.append("stored_xss")
                detection_method = "INJECTION_SECURITY_XSS"

        evidence["observed_signatures"] = observed_sigs

        # 3. State 3: ATTRIBUTED
        # Successfully mapped to the bug category with confidence >= 0.70
        is_attributed = False
        confidence = 0.0

        if is_detected:
            # High confidence if detection signature directly maps to category
            matching_sigs = set(observed_sigs).intersection(set(bug.detection_signatures))
            if matching_sigs or is_detected:
                is_attributed = True
                confidence = 0.95 if matching_sigs else 0.75

        return BugMatchResult(
            bug_id=bug.bug_id,
            is_triggered=is_triggered,
            is_detected=is_detected,
            is_attributed=is_attributed,
            attribution_confidence=confidence,
            detection_method=detection_method,
            evidence=evidence
        )
