"""TestCase-to-Endpoint Impact Mapper.
Links reachable endpoints to test cases in the suite using route pattern matching and metadata tags.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from engine.regression.impact_analyzer import ImpactedEndpoint


@dataclass
class MappedTestCase:
    test_case_id: str
    name: str
    endpoint: str
    method: str
    impact_confidence: float
    impact_distance: int
    match_strategy: str  # EXACT_ENDPOINT, ROUTE_PATTERN, MODULE_TAG, FALLBACK
    path_trace: List[str] = field(default_factory=list)


class TestImpactMapper:
    """Maps impacted endpoints to test cases within an API test suite."""

    def __init__(self):
        pass

    def map_impacted_tests(
        self,
        impacted_endpoints: List[ImpactedEndpoint],
        test_cases: List[Dict[str, Any]],  # Dict containing id, name, endpoint, method, tags
    ) -> List[MappedTestCase]:
        """Maps a list of ImpactedEndpoints to matching test cases in the test suite."""
        mapped: List[MappedTestCase] = []
        seen_test_ids = set()

        for ep in impacted_endpoints:
            target_method = ep.method.upper()
            target_path = ep.path

            for tc in test_cases:
                tc_id = str(tc.get("id"))
                if tc_id in seen_test_ids:
                    continue

                tc_method = str(tc.get("method", "")).upper()
                tc_path = str(tc.get("endpoint", "") or tc.get("path", ""))

                match_strategy = self._check_endpoint_match(
                    target_method, target_path, tc_method, tc_path, tc.get("tags", [])
                )

                if match_strategy:
                    seen_test_ids.add(tc_id)
                    mapped.append(MappedTestCase(
                        test_case_id=tc_id,
                        name=tc.get("name", f"Test_{tc_id[:8]}"),
                        endpoint=tc_path or target_path,
                        method=tc_method or target_method,
                        impact_confidence=ep.confidence_score,
                        impact_distance=ep.impact_distance,
                        match_strategy=match_strategy,
                        path_trace=ep.impact_path_trace,
                    ))

        return mapped

    def _check_endpoint_match(
        self,
        target_method: str,
        target_path: str,
        tc_method: str,
        tc_path: str,
        tc_tags: List[str],
    ) -> Optional[str]:
        if tc_method and tc_method != target_method and tc_method != "ALL":
            return None

        # 1. Exact path match
        if self._normalize_path(target_path) == self._normalize_path(tc_path):
            return "EXACT_ENDPOINT"

        # 2. Parametrized route match (e.g. /users/{id} vs /users/123)
        if self._route_pattern_matches(target_path, tc_path):
            return "ROUTE_PATTERN"

        # 3. Tag match
        clean_target = self._normalize_path(target_path)
        for tag in tc_tags:
            if tag and tag.lower() in clean_target.lower():
                return "MODULE_TAG"

        return None

    def _normalize_path(self, path: str) -> str:
        clean = path.strip().rstrip("/")
        if not clean.startswith("/"):
            clean = "/" + clean
        return clean.lower()

    def _route_pattern_matches(self, path1: str, path2: str) -> bool:
        p1 = self._normalize_path(path1)
        p2 = self._normalize_path(path2)

        # Convert {param} or :param to regex wildcard ([^/]+)
        regex1 = "^" + re.sub(r"\{[^}]+\}|:[a-zA-Z0-9_]+", r"[^/]+", p1) + "$"
        regex2 = "^" + re.sub(r"\{[^}]+\}|:[a-zA-Z0-9_]+", r"[^/]+", p2) + "$"

        if re.match(regex1, p2) or re.match(regex2, p1):
            return True

        return False
