"""
ASTRA Engine - Phase 6 Structural JSON & HTTP Response Diff Isolator

Calculates exact JSONPath-level deltas between expected test specifications and actual HTTP responses,
including JSON body deltas, header mismatches, status code deltas, and latency SLA breaches.
"""

from typing import Any, List, Dict, Optional
from engine.analysis.models import JsonDiffItem, DiffType


class JsonDiffIsolator:
    """Computes JSONPath-style deltas between expected and actual HTTP payloads/responses."""

    def compare_responses(
        self,
        expected_status: Optional[int],
        actual_status: int,
        expected_body: Any,
        actual_body: Any,
        expected_headers: Optional[Dict[str, str]] = None,
        actual_headers: Optional[Dict[str, str]] = None,
        max_latency_ms: Optional[float] = None,
        actual_latency_ms: Optional[float] = None,
    ) -> List[JsonDiffItem]:
        diff_items: List[JsonDiffItem] = []

        # 1. Status Code Diff
        if expected_status is not None and expected_status != actual_status:
            diff_items.append(
                JsonDiffItem(
                    path="$.status",
                    expected=expected_status,
                    actual=actual_status,
                    diff_type=DiffType.VALUE_MISMATCH,
                    message=f"HTTP status code mismatch: expected {expected_status}, got {actual_status}",
                )
            )

        # 2. Latency SLA Diff
        if max_latency_ms is not None and actual_latency_ms is not None and actual_latency_ms > max_latency_ms:
            diff_items.append(
                JsonDiffItem(
                    path="$.latency_ms",
                    expected=f"<= {max_latency_ms}ms",
                    actual=f"{actual_latency_ms}ms",
                    diff_type=DiffType.VALUE_MISMATCH,
                    message=f"SLA latency threshold exceeded: max {max_latency_ms}ms, actual {actual_latency_ms}ms",
                )
            )

        # 3. Headers Diff
        if expected_headers:
            actual_hdr_lower = {k.lower(): v for k, v in (actual_headers or {}).items()}
            for exp_key, exp_val in expected_headers.items():
                actual_val = actual_hdr_lower.get(exp_key.lower())
                if actual_val is None:
                    diff_items.append(
                        JsonDiffItem(
                            path=f"$.headers.{exp_key}",
                            expected=exp_val,
                            actual=None,
                            diff_type=DiffType.MISSING_KEY,
                            message=f"Missing expected header: '{exp_key}'",
                        )
                    )
                elif exp_val != actual_val and exp_val != "*":
                    diff_items.append(
                        JsonDiffItem(
                            path=f"$.headers.{exp_key}",
                            expected=exp_val,
                            actual=actual_val,
                            diff_type=DiffType.VALUE_MISMATCH,
                            message=f"Header value mismatch for '{exp_key}': expected {exp_val}, got {actual_val}",
                        )
                    )

        # 4. JSON Body Structural Diff
        if expected_body is not None:
            self._diff_nodes(expected_body, actual_body, "$.body", diff_items)

        return diff_items

    def _diff_nodes(self, expected: Any, actual: Any, current_path: str, diffs: List[JsonDiffItem]) -> None:
        if expected is None and actual is None:
            return

        if actual is None and expected is not None:
            diffs.append(
                JsonDiffItem(
                    path=current_path,
                    expected=expected,
                    actual=None,
                    diff_type=DiffType.MISSING_KEY,
                    message=f"Missing element at '{current_path}'",
                )
            )
            return

        # Type comparison
        exp_type = type(expected)
        act_type = type(actual)

        # Handle numeric types equality (int vs float)
        if exp_type in (int, float) and act_type in (int, float):
            if expected != actual:
                diffs.append(
                    JsonDiffItem(
                        path=current_path,
                        expected=expected,
                        actual=actual,
                        diff_type=DiffType.VALUE_MISMATCH,
                        message=f"Numeric mismatch at '{current_path}': expected {expected}, got {actual}",
                    )
                )
            return

        if exp_type != act_type and expected is not None:
            diffs.append(
                JsonDiffItem(
                    path=current_path,
                    expected=exp_type.__name__,
                    actual=act_type.__name__,
                    diff_type=DiffType.TYPE_MISMATCH,
                    message=f"Type mismatch at '{current_path}': expected {exp_type.__name__}, got {act_type.__name__}",
                )
            )
            return

        # Dict comparison
        if isinstance(expected, dict):
            for key, exp_val in expected.items():
                child_path = f"{current_path}.{key}"
                if key not in actual:
                    diffs.append(
                        JsonDiffItem(
                            path=child_path,
                            expected=exp_val,
                            actual=None,
                            diff_type=DiffType.MISSING_KEY,
                            message=f"Missing key '{key}' at '{child_path}'",
                        )
                    )
                else:
                    self._diff_nodes(exp_val, actual[key], child_path, diffs)

        # List comparison
        elif isinstance(expected, list):
            if len(expected) != len(actual):
                diffs.append(
                    JsonDiffItem(
                        path=f"{current_path}.length",
                        expected=len(expected),
                        actual=len(actual),
                        diff_type=DiffType.ARRAY_LENGTH_MISMATCH,
                        message=f"Array length mismatch at '{current_path}': expected {len(expected)}, got {len(actual)}",
                    )
                )

            min_len = min(len(expected), len(actual))
            for idx in range(min_len):
                item_path = f"{current_path}[{idx}]"
                self._diff_nodes(expected[idx], actual[idx], item_path, diffs)

        # Scalar primitive comparison (str, bool, etc.)
        else:
            if expected != actual:
                diffs.append(
                    JsonDiffItem(
                        path=current_path,
                        expected=expected,
                        actual=actual,
                        diff_type=DiffType.VALUE_MISMATCH,
                        message=f"Value mismatch at '{current_path}': expected '{expected}', got '{actual}'",
                    )
                )
