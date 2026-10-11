"""
ASTRA Engine - Repair Eligibility Policy Engine

Determines whether a defect and fault location are safe for autonomous repair
prior to allocating compute or generating patches.
"""

import re
from typing import List, Optional, Tuple


class RepairEligibilityPolicy:
    """Enforces safety guardrails before patch synthesis."""

    FORBIDDEN_PATH_PATTERNS: List[str] = [
        r"^auth/",
        r".*auth.*\.py$",
        r".*permission.*",
        r".*crypto.*",
        r".*token.*",
        r"^migrations/",
        r".*alembic.*",
        r"^\.github/",
        r"^docker/",
        r".*dockerfile.*",
        r"^scripts/deploy",
        r".*billing.*",
        r".*payment.*",
        r".*secret.*",
    ]

    FORBIDDEN_EXCEPTION_TYPES: List[str] = [
        "AuthenticationError",
        "PermissionDenied",
        "IntegrityError",
        "DatabaseError",
        "SecurityException",
        "UnauthorizedException",
    ]

    SUPPORTED_EXTENSIONS: Tuple[str, ...] = (
        ".py",
        ".ts",
        ".js",
        ".go",
        ".java",
    )

    @classmethod
    def evaluate(
        cls,
        severity: str,
        file_path: str,
        exception_type: Optional[str] = None,
        is_security_boundary: bool = False,
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a defect is eligible for autonomous program repair.
        Returns (is_eligible, reason).
        """
        # 1. Severity check
        if severity.upper() == "CRITICAL":
            return False, "CRITICAL severity requires manual human architectural triage."

        # 2. Security boundary flag
        if is_security_boundary:
            return False, "Target component is explicitly marked as a security boundary."

        # 3. Path pattern check
        normalized_path = file_path.replace("\\", "/").lower()
        for pattern in cls.FORBIDDEN_PATH_PATTERNS:
            if re.search(pattern, normalized_path, re.IGNORECASE):
                return False, f"Target file '{file_path}' matches forbidden security/infrastructure pattern: {pattern}"

        # 4. Exception type check
        if exception_type:
            for forbidden_ex in cls.FORBIDDEN_EXCEPTION_TYPES:
                if forbidden_ex.lower() in exception_type.lower():
                    return False, f"Exception '{exception_type}' involves auth, security, or database integrity."

        # 5. Supported language extension
        if not any(normalized_path.endswith(ext) for ext in cls.SUPPORTED_EXTENSIONS):
            return False, f"Unsupported file extension for automated repair: {file_path}"

        return True, "ELIGIBLE"
