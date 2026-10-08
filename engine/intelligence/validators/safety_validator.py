"""
Mutation Safety & Policy Filter.
"""

from typing import Optional, Tuple
from engine.intelligence.models import LLMScenarioCandidate


class SafetyValidator:
    DANGEROUS_PAYLOADS = [
        "drop table", "delete from", "format c:", "rm -rf", "shutdown", "eval("
    ]

    @classmethod
    def validate(cls, candidate: LLMScenarioCandidate) -> Tuple[bool, Optional[str]]:
        for mut in candidate.mutations:
            val_str = str(mut.mutated_value).lower()
            for dangerous in cls.DANGEROUS_PAYLOADS:
                if dangerous in val_str:
                    return False, f"Dangerous destructive payload detected in candidate mutation: '{dangerous}'"

        return True, None
