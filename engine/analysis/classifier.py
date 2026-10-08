"""
ASTRA Engine - Phase 6 Rule-Based Failure Classifier

Evaluates test failure context against priority classification rules to deterministically categorize failures.
"""

from typing import List, Tuple, Optional
from engine.analysis.models import FailureCategory, ParsedException, JsonDiffItem
from engine.analysis.rules.classification_rules import RuleContext, ClassificationRule, get_default_classification_rules


class FailureClassifier:
    """Evaluates rule precedence to determine taxonomic failure category and confidence."""

    def __init__(self, rules: Optional[List[ClassificationRule]] = None):
        self.rules = sorted(
            rules or get_default_classification_rules(),
            key=lambda r: r.priority,
            reverse=True,
        )

    def classify(
        self,
        expected_status: Optional[int],
        actual_status: int,
        test_type: str = "HTTP",
        parsed_exception: Optional[ParsedException] = None,
        diff_items: Optional[List[JsonDiffItem]] = None,
        raw_logs: str = "",
        execution_result: str = "FAILED",
        latency_ms: Optional[float] = None,
        max_latency_ms: Optional[float] = None,
    ) -> Tuple[FailureCategory, float, str, str]:
        """Returns (category, classification_confidence, rule_id, summary)."""

        # Semantic Pass Check: If expected_status == actual_status and no diff items, it's not a failure category
        if expected_status is not None and expected_status == actual_status and not diff_items and not parsed_exception and execution_result == "PASSED":
            return FailureCategory.UNKNOWN, 1.0, "PASS_SEMANTIC", "Test passed semantically"

        context = RuleContext(
            expected_status=expected_status,
            actual_status=actual_status,
            test_type=test_type,
            parsed_exception=parsed_exception,
            diff_items=diff_items or [],
            raw_logs=raw_logs,
            execution_result=execution_result,
            latency_ms=latency_ms,
            max_latency_ms=max_latency_ms,
        )

        for rule in self.rules:
            if rule.condition(context):
                return rule.category, rule.confidence, rule.rule_id, rule.description

        return FailureCategory.UNKNOWN, 0.60, "R030", "Fallback unclassified failure"
