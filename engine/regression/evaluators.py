"""Regression Oracle Evaluator.
Compares Tier 1 selective execution decisions against actual ground-truth (Oracle) full test suite results.
Computes selection recall, precision, false negative rate, and time savings.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Any
from engine.regression.selective_selector import SelectionResult


@dataclass
class EvaluationReport:
    total_tests: int
    true_positives: int  # Selected & Failed
    false_positives: int  # Selected & Passed
    true_negatives: int  # Deferred & Passed
    false_negatives: int  # Deferred & Failed (CRITICAL RECALL FAILURE IF > 0)
    recall: float
    precision: float
    accuracy: float
    time_saved_ms: float
    zero_false_negative_pass: bool
    details: List[Dict[str, Any]] = field(default_factory=list)


class RegressionOracleEvaluator:
    """Evaluates accuracy of selective regression choices against full suite test execution outcomes."""

    def __init__(self):
        pass

    def evaluate(
        self,
        selection_result: SelectionResult,
        full_suite_outcomes: Dict[str, str],  # test_case_id -> "PASSED" | "FAILED" | "ERROR"
        test_durations_ms: Dict[str, float],
    ) -> EvaluationReport:
        """Evaluates precision, recall, and false negatives of the selective run."""
        tier1_ids = {t.test_case_id for t in selection_result.tier1_test_details}
        tier2_ids = {t.test_case_id for t in selection_result.tier2_test_details}

        tp = 0
        fp = 0
        tn = 0
        fn = 0

        details = []

        for tc_id, outcome in full_suite_outcomes.items():
            failed = (outcome in ["FAILED", "ERROR"])
            duration = test_durations_ms.get(tc_id, 100.0)

            if tc_id in tier1_ids:
                if failed:
                    tp += 1
                    status = "TRUE_POSITIVE"
                else:
                    fp += 1
                    status = "FALSE_POSITIVE"
            else:
                if failed:
                    fn += 1
                    status = "FALSE_NEGATIVE"
                else:
                    tn += 1
                    status = "TRUE_NEGATIVE"

            details.append({
                "test_case_id": tc_id,
                "tier": "TIER1" if tc_id in tier1_ids else "TIER2",
                "outcome": outcome,
                "eval_status": status,
                "duration_ms": duration,
            })

        total = tp + fp + tn + fn
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0
        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
        accuracy = round((tp + tn) / total, 4) if total > 0 else 1.0

        time_saved = sum(test_durations_ms.get(t_id, 100.0) for t_id in tier2_ids)

        return EvaluationReport(
            total_tests=total,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            recall=recall,
            precision=precision,
            accuracy=accuracy,
            time_saved_ms=time_saved,
            zero_false_negative_pass=(fn == 0),
            details=details,
        )
