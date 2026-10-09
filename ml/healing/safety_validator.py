"""Safety Validator Gate for Proposed Specification Patches."""

from typing import Dict, Any, Tuple
from ml.healing.patch_operations import PatchOperationEnforcer


class HealingSafetyValidator:
    """
    Ensures that proposed test specification patches preserve core contract and security assertions.
    Forbidden mutations (e.g. changing 500 server crash into expected 500 status) are strictly rejected.
    """

    @staticmethod
    def validate_healing_candidate(
        original_spec: Dict[str, Any],
        proposed_spec: Dict[str, Any],
        patch_operations: list,
        failure_category: str,
    ) -> Tuple[bool, str]:
        # 1. Reject server crash or DB error mutations (A 500 server crash is NEVER a spec bug)
        if failure_category in ("SERVER_CRASH", "DATABASE_ERROR"):
            return False, f"Rejection: Failure category '{failure_category}' represents an application defect, not a specification drift."

        # 2. Check operation whitelist/blacklist
        is_ops_valid, op_violations = PatchOperationEnforcer.validate_patch_operations(patch_operations)
        if not is_ops_valid:
            return False, f"Safety Violation: {'; '.join(op_violations)}"

        # 3. Ensure expected_status is a valid HTTP status (100-599) and not a 5xx server error
        proposed_status = proposed_spec.get("expected_status")
        if proposed_status is not None:
            try:
                status_int = int(proposed_status)
                if status_int >= 500:
                    return False, f"Safety Violation: Cannot set expected_status to server error code {status_int}."
            except (ValueError, TypeError):
                return False, "Safety Violation: Invalid expected_status type."

        # 4. Check auth/security header preservation
        orig_headers = original_spec.get("expected_headers", {})
        prop_headers = proposed_spec.get("expected_headers", {})
        for auth_key in ("authorization", "x-api-key", "bearer"):
            if auth_key in orig_headers and auth_key not in prop_headers:
                return False, f"Safety Violation: Authentication header '{auth_key}' cannot be removed by healing patch."

        return True, "VALID"
