"""Structural Spec Patch Candidate Generator."""

import copy
from typing import Dict, Any, List, Optional
from ml.common.schemas import HealingPatchProposal
from ml.healing.safety_validator import HealingSafetyValidator


class CandidateGenerator:
    """
    Generates proposed specification patches based on Phase 6 FailureAnalysis output,
    actual vs expected status/header/body diffs, and contract drift.
    """

    @staticmethod
    def generate_candidate(
        test_case_id: str,
        failure_analysis_id: str,
        source_run_id: str,
        original_spec: Dict[str, Any],
        actual_response_data: Dict[str, Any],
        actual_status_code: int,
        failure_category: str,
        diff_items: List[Dict[str, Any]],
    ) -> Optional[HealingPatchProposal]:
        if not original_spec:
            return None

        # Do not generate healing for server crashes or DB errors
        if failure_category in ("SERVER_CRASH", "DATABASE_ERROR"):
            return None

        proposed_spec = copy.deepcopy(original_spec)
        patch_ops = []

        # 1. Status Code Drift (e.g. expected 200, actual 201 Created)
        expected_status = original_spec.get("expected_status")
        if actual_status_code in (201, 202, 204) and expected_status == 200:
            proposed_spec["expected_status"] = actual_status_code
            patch_ops.append({
                "op_type": "REPLACE_EXPECTED_STATUS",
                "field": "expected_status",
                "old_value": expected_status,
                "new_value": actual_status_code,
                "reason": f"API endpoint behavior updated from {expected_status} to {actual_status_code}",
            })

        # 2. JSON Body Path Shift / Contract Violation
        for diff in diff_items:
            path = diff.get("path", "")
            d_type = diff.get("diff_type", "")
            actual_val = diff.get("actual")

            if d_type == "MISSING_KEY" and path:
                # Check if field was renamed (e.g. $.user_id -> $.account_id)
                new_key = path.replace("$.", "").replace("user_id", "account_id")
                if isinstance(actual_response_data, dict) and new_key in actual_response_data:
                    patch_ops.append({
                        "op_type": "RENAME_JSON_PATH",
                        "field": path,
                        "old_value": path,
                        "new_value": f"$.{new_key}",
                        "reason": f"Contract field path renamed from {path} to $.{new_key}",
                    })
                    # Update expected body spec if dict
                    exp_body = proposed_spec.get("expected_body")
                    if isinstance(exp_body, dict) and "user_id" in exp_body:
                        val = exp_body.pop("user_id")
                        exp_body["account_id"] = val

        if not patch_ops:
            return None

        # Validate against Safety Gate
        is_safe, reason = HealingSafetyValidator.validate_healing_candidate(
            original_spec, proposed_spec, patch_ops, failure_category
        )

        return HealingPatchProposal(
            test_case_id=test_case_id,
            failure_analysis_id=failure_analysis_id,
            source_run_id=source_run_id,
            original_specification=original_spec,
            proposed_specification=proposed_spec,
            patch_operations=patch_ops,
            confidence=0.85 if is_safe else 0.0,
            is_safe=is_safe,
            rejection_reason=None if is_safe else reason,
        )
