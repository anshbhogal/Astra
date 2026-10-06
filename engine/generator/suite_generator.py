import uuid
from typing import List, Dict, Any, Optional
from engine.models.test_spec import TestSpecification, TestType, StatusSource, AssertionRule, AssertionType


class SyntheticTestSuiteGenerator:
    """Generates synthetic TestSpecification lists from discovered AST endpoints."""

    def generate_suite_for_endpoints(
        self, endpoints: List[Any], suite_name: str = "Synthetic Test Suite"
    ) -> List[TestSpecification]:
        specs: List[TestSpecification] = []
        execution_order = 1

        for ep in endpoints:
            # 1. HAPPY_PATH Test Case
            happy_spec = self._create_happy_path_spec(ep, execution_order)
            specs.append(happy_spec)
            execution_order += 1

            # 2. MISSING_REQUIRED Test Case (if parameters exist)
            params = ep.parameters if hasattr(ep, "parameters") else []
            required_params = [p for p in params if (isinstance(p, dict) and p.get("required")) or (hasattr(p, "required") and getattr(p, "required"))]
            if required_params:
                missing_spec = self._create_missing_param_spec(ep, required_params[0], execution_order)
                specs.append(missing_spec)
                execution_order += 1

            # 3. INVALID_TYPE Test Case (if parameters exist)
            if params:
                invalid_type_spec = self._create_invalid_type_spec(ep, params[0], execution_order)
                specs.append(invalid_type_spec)
                execution_order += 1

            # 4. UNAUTHORIZED Test Case
            unauth_spec = self._create_unauthorized_spec(ep, execution_order)
            specs.append(unauth_spec)
            execution_order += 1

        return specs

    def _create_happy_path_spec(self, ep: Any, order: int) -> TestSpecification:
        method = ep.method.upper() if hasattr(ep, "method") else "GET"
        path = ep.path if hasattr(ep, "path") else "/"
        ep_id = str(ep.id) if hasattr(ep, "id") else str(uuid.uuid4())

        path_params, query_params, body = self._build_synthetic_inputs(ep, mode="valid")
        expected_status = [200, 201, 204] if method in ["POST", "PUT"] else [200]

        assertions = [
            AssertionRule(type=AssertionType.STATUS_CODE, expected=expected_status),
            AssertionRule(type=AssertionType.CONTENT_TYPE, expected="application/json"),
            AssertionRule(type=AssertionType.LATENCY_SLA, expected=5000)
        ]

        return TestSpecification(
            id=str(uuid.uuid4()),
            name=f"Happy Path — {method} {path}",
            endpoint_id=ep_id,
            test_type=TestType.HAPPY_PATH,
            method=method,
            path=path,
            path_params=path_params,
            query_params=query_params,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            body=body,
            auth_ref={"type": "bearer", "credential_ref": "default-test-token"},
            expected_status=expected_status,
            expected_status_source=StatusSource.STATIC_RULE,
            assertions=assertions,
            timeout_ms=10000,
            execution_order=order,
            metadata={"generated_by": "SyntheticTestSuiteGenerator v3.0"}
        )

    def _create_missing_param_spec(self, ep: Any, target_param: Any, order: int) -> TestSpecification:
        method = ep.method.upper() if hasattr(ep, "method") else "GET"
        path = ep.path if hasattr(ep, "path") else "/"
        ep_id = str(ep.id) if hasattr(ep, "id") else str(uuid.uuid4())

        param_name = target_param.get("name") if isinstance(target_param, dict) else getattr(target_param, "name", "id")

        path_params, query_params, body = self._build_synthetic_inputs(ep, mode="omit", omit_param=param_name)
        expected_status = [400, 422]

        assertions = [
            AssertionRule(type=AssertionType.STATUS_CODE, expected=expected_status)
        ]

        return TestSpecification(
            id=str(uuid.uuid4()),
            name=f"Missing Parameter '{param_name}' — {method} {path}",
            endpoint_id=ep_id,
            test_type=TestType.MISSING_REQUIRED,
            method=method,
            path=path,
            path_params=path_params,
            query_params=query_params,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            body=body,
            auth_ref={"type": "bearer", "credential_ref": "default-test-token"},
            expected_status=expected_status,
            expected_status_source=StatusSource.FRAMEWORK_CONVENTION,
            assertions=assertions,
            timeout_ms=10000,
            execution_order=order,
            metadata={"omitted_parameter": param_name}
        )

    def _create_invalid_type_spec(self, ep: Any, target_param: Any, order: int) -> TestSpecification:
        method = ep.method.upper() if hasattr(ep, "method") else "GET"
        path = ep.path if hasattr(ep, "path") else "/"
        ep_id = str(ep.id) if hasattr(ep, "id") else str(uuid.uuid4())

        param_name = target_param.get("name") if isinstance(target_param, dict) else getattr(target_param, "name", "id")

        path_params, query_params, body = self._build_synthetic_inputs(ep, mode="invalid_type", invalid_param=param_name)
        expected_status = [400, 422]

        assertions = [
            AssertionRule(type=AssertionType.STATUS_CODE, expected=expected_status)
        ]

        return TestSpecification(
            id=str(uuid.uuid4()),
            name=f"Invalid Data Type for '{param_name}' — {method} {path}",
            endpoint_id=ep_id,
            test_type=TestType.INVALID_TYPE,
            method=method,
            path=path,
            path_params=path_params,
            query_params=query_params,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            body=body,
            auth_ref={"type": "bearer", "credential_ref": "default-test-token"},
            expected_status=expected_status,
            expected_status_source=StatusSource.FRAMEWORK_CONVENTION,
            assertions=assertions,
            timeout_ms=10000,
            execution_order=order,
            metadata={"invalid_parameter": param_name}
        )

    def _create_unauthorized_spec(self, ep: Any, order: int) -> TestSpecification:
        method = ep.method.upper() if hasattr(ep, "method") else "GET"
        path = ep.path if hasattr(ep, "path") else "/"
        ep_id = str(ep.id) if hasattr(ep, "id") else str(uuid.uuid4())

        path_params, query_params, body = self._build_synthetic_inputs(ep, mode="valid")
        expected_status = [401, 403, 200]  # Allow 200 if route is public

        assertions = [
            AssertionRule(type=AssertionType.STATUS_CODE, expected=expected_status)
        ]

        return TestSpecification(
            id=str(uuid.uuid4()),
            name=f"Unauthorized Access — {method} {path}",
            endpoint_id=ep_id,
            test_type=TestType.UNAUTHORIZED,
            method=method,
            path=path,
            path_params=path_params,
            query_params=query_params,
            headers={"Accept": "application/json"},
            body=body,
            auth_ref=None,  # Intentionally omit auth
            expected_status=expected_status,
            expected_status_source=StatusSource.STATIC_RULE,
            assertions=assertions,
            timeout_ms=10000,
            execution_order=order,
            metadata={"auth_omitted": True}
        )

    def _build_synthetic_inputs(
        self, ep: Any, mode: str = "valid", omit_param: Optional[str] = None, invalid_param: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]:
        params = ep.parameters if hasattr(ep, "parameters") else []

        path_params = {}
        query_params = {}
        body = {}

        for p in params:
            p_name = p.get("name") if isinstance(p, dict) else getattr(p, "name", "")
            p_type = p.get("type", "str") if isinstance(p, dict) else getattr(p, "type", "str")
            p_loc = p.get("location", "query") if isinstance(p, dict) else getattr(p, "location", "query")

            if mode == "omit" and p_name == omit_param:
                continue

            val = self._generate_value(p_name, p_type, is_invalid=(mode == "invalid_type" and p_name == invalid_param))

            if p_loc == "path":
                path_params[p_name] = val
            elif p_loc == "body":
                body[p_name] = val
            else:
                query_params[p_name] = val

        body_payload = body if body and (hasattr(ep, "method") and ep.method.upper() in ["POST", "PUT", "PATCH"]) else None
        return path_params, query_params, body_payload

    def _generate_value(self, name: str, type_str: str, is_invalid: bool = False) -> Any:
        if is_invalid:
            return "NOT_AN_INTEGER_STRING" if "int" in type_str.lower() else {"invalid_dict": True}

        type_lower = type_str.lower()
        if "int" in type_lower:
            return 1
        elif "bool" in type_lower:
            return True
        elif "float" in type_lower:
            return 1.5
        elif "dict" in type_lower or "model" in type_lower or "schema" in type_lower:
            return {"sample_key": "sample_val"}
        else:
            if "email" in name.lower():
                return "test@astra.local"
            elif "id" in name.lower():
                return "1"
            return "sample_string"
