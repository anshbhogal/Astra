"""Whitelist & Blacklist Patch Operations Enforcer."""

from typing import List, Dict, Any, Tuple

# Allowed repair operations
ALLOWED_WHITELIST_OPERATIONS = {
    "REPLACE_EXPECTED_STATUS",
    "ADD_EXPECTED_HEADER",
    "REMOVE_EXPECTED_HEADER",
    "RENAME_JSON_PATH",
    "UPDATE_JSON_VALUE_CONSTRAINT",
    "UPDATE_LATENCY_THRESHOLD",
}

# Forbidden security-weakening operations
FORBIDDEN_BLACKLIST_OPERATIONS = {
    "REMOVE_AUTH_ASSERTION",
    "REMOVE_SECURITY_TEST",
    "DISABLE_ASSERTION",
    "CHANGE_HTTP_METHOD",
    "CHANGE_TARGET_HOST",
    "DISABLE_SSL_VALIDATION",
    "DELETE_VALIDATION_RULE",
}


class PatchOperationEnforcer:
    @staticmethod
    def validate_patch_operations(patch_ops: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validates that all proposed patch operations belong to the ALLOWED_WHITELIST
        and that no FORBIDDEN_BLACKLIST operation is present.
        """
        if not patch_ops:
            return False, ["Empty patch operations list."]

        violations = []
        for op in patch_ops:
            op_type = str(op.get("op_type", "")).upper()

            if op_type in FORBIDDEN_BLACKLIST_OPERATIONS:
                violations.append(f"Forbidden operation '{op_type}' detected: Security or contract assertions cannot be removed.")

            if op_type not in ALLOWED_WHITELIST_OPERATIONS:
                violations.append(f"Operation '{op_type}' is not in the approved healing whitelist.")

        is_valid = len(violations) == 0
        return is_valid, violations
