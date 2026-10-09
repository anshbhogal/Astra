"""Quarantine Recommendation & Non-Blocking Execution Manager."""

from typing import List, Dict, Any
from ml.common.schemas import FlakinessEvalResult


class QuarantineManager:
    """
    Manages quarantine state transitions for test cases.
    Quarantined tests remain executed during test suite runs, but their failure
    does not cause the overall test suite / CI build gate to fail (Non-Blocking execution mode).
    """

    @staticmethod
    def process_quarantine_decision(
        eval_result: FlakinessEvalResult,
        user_approved: bool = False,
    ) -> Dict[str, Any]:
        if user_approved:
            new_status = "QUARANTINED"
            is_non_blocking = True
        elif eval_result.recommend_quarantine:
            new_status = "RECOMMENDED_QUARANTINE"
            is_non_blocking = False  # Not non-blocking until human approves
        else:
            new_status = "ACTIVE"
            is_non_blocking = False

        return {
            "test_case_id": eval_result.test_case_id,
            "flakiness_score": eval_result.flakiness_score,
            "status": new_status,
            "is_non_blocking": is_non_blocking,
            "requires_human_review": bool(eval_result.recommend_quarantine and not user_approved),
        }
