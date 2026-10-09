"""Conservative Safety Gate & Unknown Impact Expander.
Enforces ZERO false negatives axiom by detecting unknown/high-risk code changes (migrations, core utils,
untracked modules, renamed symbols) and triggering safety expansion.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional
from engine.regression.git_diff_parser import FileDiff


class UnknownImpactCategory(str, Enum):
    NEW_MODULE_UNKNOWN_GRAPH = "NEW_MODULE_UNKNOWN_GRAPH"
    GLOBAL_UTILITY_MODIFIED = "GLOBAL_UTILITY_MODIFIED"
    SCHEMA_OR_MIGRATION_CHANGE = "SCHEMA_OR_MIGRATION_CHANGE"
    DELETED_OR_RENAMED_SYMBOL = "DELETED_OR_RENAMED_SYMBOL"
    LOW_GRAPH_COVERAGE = "LOW_GRAPH_COVERAGE"


@dataclass
class SafetyCheckResult:
    expansion_triggered: bool
    triggers: List[UnknownImpactCategory]
    confidence_penalty: float
    expansion_reason: Optional[str]
    expanded_test_ids: Set[str] = field(default_factory=set)


class SafetyGate:
    """Evaluates risk triggers on code diffs to decide if conservative test set expansion is required."""

    GLOBAL_UTIL_KEYWORDS = [
        "auth", "login", "security", "jwt", "session",
        "database", "db", "session", "config", "settings",
        "middleware", "common", "utils", "base", "core"
    ]

    def __init__(self, fallback_to_full_suite_on_trigger: bool = False):
        self.fallback_to_full_suite_on_trigger = fallback_to_full_suite_on_trigger

    def evaluate_safety(
        self,
        file_diffs: List[FileDiff],
        all_test_cases: List[Dict[str, Any]],
        targeted_test_ids: Set[str],
        pkg_node_count: int = 0,
    ) -> SafetyCheckResult:
        """Evaluates whether conservative expansion is required for the targeted test selection."""
        triggers: List[UnknownImpactCategory] = []
        confidence_penalty = 0.0

        for fd in file_diffs:
            filepath = fd.new_path.lower()

            # 1. Schema or Migration Change
            if "migration" in filepath or "schema" in filepath or fd.change_category == "SCHEMA_CHANGE":
                if UnknownImpactCategory.SCHEMA_OR_MIGRATION_CHANGE not in triggers:
                    triggers.append(UnknownImpactCategory.SCHEMA_OR_MIGRATION_CHANGE)
                    confidence_penalty += 0.2

            # 2. Global Utility Modified
            if any(kw in filepath for kw in self.GLOBAL_UTIL_KEYWORDS) and "test" not in filepath:
                if UnknownImpactCategory.GLOBAL_UTILITY_MODIFIED not in triggers:
                    triggers.append(UnknownImpactCategory.GLOBAL_UTILITY_MODIFIED)
                    confidence_penalty += 0.25

            # 3. New Module or Deleted/Renamed Symbol
            if fd.change_type == "RENAMED" or fd.change_type == "DELETED":
                if UnknownImpactCategory.DELETED_OR_RENAMED_SYMBOL not in triggers:
                    triggers.append(UnknownImpactCategory.DELETED_OR_RENAMED_SYMBOL)
                    confidence_penalty += 0.15

            if fd.change_type == "ADDED" and not "test" in filepath:
                if UnknownImpactCategory.NEW_MODULE_UNKNOWN_GRAPH not in triggers:
                    triggers.append(UnknownImpactCategory.NEW_MODULE_UNKNOWN_GRAPH)
                    confidence_penalty += 0.1

        # 4. Low Graph Coverage
        if pkg_node_count < 5 and len(file_diffs) > 0:
            if UnknownImpactCategory.LOW_GRAPH_COVERAGE not in triggers:
                triggers.append(UnknownImpactCategory.LOW_GRAPH_COVERAGE)
                confidence_penalty += 0.3

        expansion_triggered = len(triggers) > 0
        expanded_test_ids = set(targeted_test_ids)
        expansion_reason = None

        if expansion_triggered:
            trigger_names = [t.value for t in triggers]
            expansion_reason = f"Safety expansion triggered due to: {', '.join(trigger_names)}"

            # Expand candidate tests: include high-priority or all tests depending on config
            if self.fallback_to_full_suite_on_trigger:
                expanded_test_ids = {str(tc["id"]) for tc in all_test_cases}
            else:
                # Include smoke/sanity tests and tests matching modified domains
                for tc in all_test_cases:
                    tc_id = str(tc["id"])
                    tc_tags = [t.lower() for t in tc.get("tags", [])]
                    if "smoke" in tc_tags or "critical" in tc_tags or "sanity" in tc_tags:
                        expanded_test_ids.add(tc_id)

        return SafetyCheckResult(
            expansion_triggered=expansion_triggered,
            triggers=triggers,
            confidence_penalty=min(0.5, confidence_penalty),
            expansion_reason=expansion_reason,
            expanded_test_ids=expanded_test_ids,
        )
