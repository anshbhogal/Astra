"""
TestPrioritizer: Rule-based priority queue for scenario budget truncation.
"""

from typing import List, Tuple
from engine.generator.models import TestScenario, TestType


class TestPrioritizer:
    """Prioritizes and truncates candidate test scenarios based on defect-detection probability."""

    PRIORITY_MAP = {
        TestType.HAPPY_PATH: 1,
        TestType.MISSING_REQUIRED: 2,
        TestType.BOUNDARY: 3,
        TestType.EQUIVALENCE_PARTITION: 4,
        TestType.INVALID_TYPE: 5,
        TestType.INVALID_FORMAT: 6,
        TestType.NULL_VALUE: 7,
        TestType.SECURITY_PROBE: 8,
        TestType.COMBINATORIAL: 9,
        TestType.UNAUTHORIZED: 10,
        TestType.METHOD_NOT_ALLOWED: 11,
    }

    @classmethod
    def prioritize_and_cap(
        cls, scenarios: List[TestScenario], max_total_cases: int
    ) -> Tuple[List[TestScenario], int]:
        """
        Sorts scenarios by priority rule and truncates if exceeding max_total_cases.
        Returns (prioritized_scenarios, truncated_count).
        """
        def get_priority(s: TestScenario) -> int:
            return cls.PRIORITY_MAP.get(s.test_type, 99)

        sorted_scenarios = sorted(scenarios, key=get_priority)

        if len(sorted_scenarios) <= max_total_cases:
            return sorted_scenarios, 0

        truncated = len(sorted_scenarios) - max_total_cases
        return sorted_scenarios[:max_total_cases], truncated
