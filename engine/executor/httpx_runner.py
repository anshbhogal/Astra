import time
import httpx
from typing import Dict, Any, Optional
from engine.models.test_spec import TestSpecification, TestOutcome
from engine.models.target_env import TargetEnvironmentConfig
from engine.security.ssrf_protector import SSRFProtector, SSRFValidationError
from engine.security.redactor import TelemetryRedactor
from engine.assertions.evaluator import AssertionEvaluator


class HTTPXTestRunner:
    """Async HTTP test runner executing TestSpecification instances against target environments."""

    @classmethod
    async def run_spec(cls, spec: TestSpecification, config: TargetEnvironmentConfig) -> Dict[str, Any]:
        # Substitute path parameters in endpoint path
        target_path = spec.path
        for k, v in spec.path_params.items():
            target_path = target_path.replace(f"{{{k}}}", str(v))

        url = f"{config.base_url.rstrip('/')}{target_path}"

        # 1. SSRF Security Check
        try:
            SSRFProtector.validate_url(url, config)
        except SSRFValidationError as err:
            return {
                "outcome": TestOutcome.ERROR.value,
                "status_code": None,
                "request_data": cls._build_redacted_request_telemetry(url, spec),
                "response_data": None,
                "response_body_truncated": False,
                "execution_time_ms": 0.0,
                "assertion_failures": [],
                "error_message": f"SSRF Security Violation: {err}"
            }

        # Combine Headers
        req_headers = dict(config.custom_headers)
        req_headers.update(spec.headers)

        if spec.auth_ref and isinstance(spec.auth_ref, dict):
            auth_type = spec.auth_ref.get("type", "").lower()
            if auth_type == "bearer":
                req_headers["Authorization"] = "Bearer default-test-token"

        start_time = time.perf_counter()

        async with httpx.AsyncClient(verify=config.verify_ssl) as client:
            try:
                res = await client.request(
                    method=spec.method,
                    url=url,
                    headers=req_headers,
                    params=spec.query_params,
                    json=spec.body if spec.body and spec.method in ["POST", "PUT", "PATCH"] else None,
                    timeout=float(spec.timeout_ms) / 1000.0
                )
                duration_ms = (time.perf_counter() - start_time) * 1000.0

                try:
                    res_body = res.json()
                except Exception:
                    res_body = {"raw_text": res.text}

                # Evaluate Assertions
                res_headers = dict(res.headers)
                failures = AssertionEvaluator.evaluate(
                    spec=spec,
                    status_code=res.status_code,
                    response_body=res_body,
                    response_headers=res_headers,
                    duration_ms=duration_ms
                )

                outcome = TestOutcome.PASS.value if len(failures) == 0 else TestOutcome.FAIL.value

                # Sanitize Telemetry
                redacted_req = cls._build_redacted_request_telemetry(url, spec, req_headers)
                redacted_res, is_truncated = TelemetryRedactor.redact_and_truncate_response(res_body)

                return {
                    "outcome": outcome,
                    "status_code": res.status_code,
                    "request_data": redacted_req,
                    "response_data": redacted_res,
                    "response_body_truncated": is_truncated,
                    "execution_time_ms": round(duration_ms, 2),
                    "assertion_failures": failures,
                    "error_message": None
                }

            except httpx.TimeoutException:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return {
                    "outcome": TestOutcome.TIMEOUT.value,
                    "status_code": None,
                    "request_data": cls._build_redacted_request_telemetry(url, spec, req_headers),
                    "response_data": None,
                    "response_body_truncated": False,
                    "execution_time_ms": round(duration_ms, 2),
                    "assertion_failures": [],
                    "error_message": f"Execution timed out after {spec.timeout_ms}ms."
                }

            except httpx.RequestError as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return {
                    "outcome": TestOutcome.ERROR.value,
                    "status_code": None,
                    "request_data": cls._build_redacted_request_telemetry(url, spec, req_headers),
                    "response_data": None,
                    "response_body_truncated": False,
                    "execution_time_ms": round(duration_ms, 2),
                    "assertion_failures": [],
                    "error_message": f"Network/HTTP Execution Error: {str(exc)}"
                }

    @classmethod
    def _build_redacted_request_telemetry(cls, url: str, spec: TestSpecification, raw_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        headers = raw_headers or spec.headers
        return {
            "url": url,
            "method": spec.method,
            "headers": TelemetryRedactor.redact_headers(headers),
            "query_params": spec.query_params,
            "body": TelemetryRedactor.redact_json_payload(spec.body) if spec.body else None
        }
