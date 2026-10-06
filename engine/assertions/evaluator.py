from typing import List, Dict, Any, Optional
import jsonschema
from engine.models.test_spec import TestSpecification, AssertionRule, AssertionType


class AssertionEvaluator:
    """Evaluates composable, non-AI deterministic contract assertion rules."""

    @classmethod
    def evaluate(
        cls,
        spec: TestSpecification,
        status_code: int,
        response_body: Any,
        response_headers: Dict[str, str],
        duration_ms: float
    ) -> List[Dict[str, Any]]:
        failures: List[Dict[str, Any]] = []

        # 1. Primary Status Code Assertion
        expected_statuses = spec.expected_status if isinstance(spec.expected_status, list) else [spec.expected_status]
        if status_code not in expected_statuses:
            failures.append({
                "type": "STATUS_CODE_MISMATCH",
                "expected": expected_statuses,
                "actual": status_code,
                "message": f"Expected HTTP status code in {expected_statuses}, but received {status_code}."
            })

        # 2. JSON Schema Assertion
        if spec.expected_schema and isinstance(response_body, (dict, list)):
            try:
                jsonschema.validate(instance=response_body, schema=spec.expected_schema)
            except jsonschema.ValidationError as err:
                failures.append({
                    "type": "SCHEMA_VALIDATION_ERROR",
                    "expected_schema": spec.expected_schema,
                    "message": f"Response JSON failed schema contract validation: {err.message}"
                })

        # 3. Composable Assertion Rules Loop
        for rule in spec.assertions:
            rule_type = rule.type.value if hasattr(rule.type, "value") else str(rule.type)

            if rule_type == AssertionType.STATUS_CODE.value:
                exp_list = rule.expected if isinstance(rule.expected, list) else [rule.expected]
                if status_code not in exp_list:
                    failures.append({
                        "type": "STATUS_CODE_MISMATCH",
                        "expected": exp_list,
                        "actual": status_code,
                        "message": rule.message or f"Expected status in {exp_list}, got {status_code}."
                    })

            elif rule_type == AssertionType.CONTENT_TYPE.value:
                content_type = response_headers.get("content-type", response_headers.get("Content-Type", ""))
                if str(rule.expected).lower() not in content_type.lower():
                    failures.append({
                        "type": "CONTENT_TYPE_MISMATCH",
                        "expected": rule.expected,
                        "actual": content_type,
                        "message": rule.message or f"Expected Content-Type containing '{rule.expected}', got '{content_type}'."
                    })

            elif rule_type in [AssertionType.KEY_VALUE.value, AssertionType.JSON_PATH.value]:
                path = rule.path
                if path and isinstance(response_body, dict):
                    actual_val = cls._get_nested_value(response_body, path)
                    if actual_val != rule.expected:
                        failures.append({
                            "type": "KEY_VALUE_MISMATCH",
                            "path": path,
                            "expected": rule.expected,
                            "actual": actual_val,
                            "message": rule.message or f"Expected '{path}' to equal '{rule.expected}', but got '{actual_val}'."
                        })

            elif rule_type == AssertionType.BODY_CONTAINS.value:
                body_str = str(response_body)
                if str(rule.expected) not in body_str:
                    failures.append({
                        "type": "BODY_CONTAINS_FAILED",
                        "expected_substring": rule.expected,
                        "message": rule.message or f"Response body did not contain expected substring '{rule.expected}'."
                    })

            elif rule_type == AssertionType.BODY_NOT_CONTAINS.value:
                body_str = str(response_body)
                if str(rule.expected) in body_str:
                    failures.append({
                        "type": "BODY_NOT_CONTAINS_FAILED",
                        "forbidden_substring": rule.expected,
                        "message": rule.message or f"Response body contained forbidden substring '{rule.expected}'."
                    })

            elif rule_type == AssertionType.LATENCY_SLA.value:
                max_sla = float(rule.expected)
                if duration_ms > max_sla:
                    failures.append({
                        "type": "LATENCY_SLA_EXCEEDED",
                        "expected_max_ms": max_sla,
                        "actual_ms": round(duration_ms, 2),
                        "message": rule.message or f"Execution latency {duration_ms:.2f}ms exceeded SLA maximum of {max_sla}ms."
                    })

        return failures

    @classmethod
    def _get_nested_value(cls, data: Dict[str, Any], path: str) -> Any:
        keys = path.split(".")
        current = data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current
