"""
Phase 3.5 Hardening Test Suite for ASTRA Engine & Execution Infrastructure.
Validates:
1. Real E2E execution against dedicated FastAPI fixture target.
2. Complete negative path matrix (ENVIRONMENT_ERROR, TIMEOUT, FAIL on 500, FAIL on schema, BLOCKED on SSRF).
3. Security boundary & telemetry redaction persistence safety.
4. Execution outcome reproducibility across repeated runs.
5. Canonical execution format (TestSpecification -> HTTPXTestRunner).
"""

import pytest
import json
from httpx import ASGITransport, AsyncClient

from engine.models.test_spec import (
    TestSpecification,
    AssertionRule,
    TestType,
    TestOutcome,
    AssertionType,
)
from engine.models.target_env import TargetEnvironmentConfig, EnvironmentType
from engine.executor.httpx_runner import HTTPXTestRunner
from engine.executor.health_checker import TargetHealthChecker
from engine.security.ssrf_protector import SSRFProtector, SSRFValidationError
from engine.security.redactor import TelemetryRedactor
from tests.fixtures.sample_target_app import app as target_fastapi_app


@pytest.fixture
def target_transport():
    return ASGITransport(app=target_fastapi_app)


@pytest.fixture
def target_env_config():
    return TargetEnvironmentConfig(
        target_base_url="http://testserver",
        environment_type=EnvironmentType.LOCAL_SANDBOX,
        timeout_seconds=5.0,
        custom_headers={"X-Test-Suite": "Astra-Hardening"},
        is_local_sandbox=True,
    )


@pytest.mark.asyncio
async def test_e2e_execution_against_fastapi_fixture(target_transport, target_env_config):
    """
    Test end-to-end execution of synthetic test specifications directly against
    the dedicated FastAPI fixture application.
    """
    async with AsyncClient(transport=target_transport, base_url="http://testserver") as client:
        # 1. Test GET /health (Happy Path -> PASS)
        spec_health = TestSpecification(
            id="spec-health-001",
            name="GET /health Happy Path",
            endpoint_id="ep-health",
            path="/health",
            method="GET",
            test_type=TestType.HAPPY_PATH,
            assertions=[
                AssertionRule(type=AssertionType.STATUS_CODE, expected=200),
                AssertionRule(type=AssertionType.LATENCY_SLA, expected=3000.0),
            ],
        )

        res_health = await HTTPXTestRunner.run_spec(spec_health, target_env_config, custom_client=client)
        assert res_health["outcome"] == TestOutcome.PASS.value
        assert res_health["status_code"] == 200
        assert res_health["response_data"]["status"] == "ok"

        # 2. Test POST /items (Happy Path -> PASS)
        spec_create_item = TestSpecification(
            id="spec-item-001",
            name="POST /items Happy Path",
            endpoint_id="ep-items",
            path="/items",
            method="POST",
            test_type=TestType.HAPPY_PATH,
            body={"name": "Hardened Gadget"},
            assertions=[
                AssertionRule(type=AssertionType.STATUS_CODE, expected=201),
                AssertionRule(type=AssertionType.JSON_PATH, path="$.name", expected="Hardened Gadget"),
            ],
        )

        res_item = await HTTPXTestRunner.run_spec(spec_create_item, target_env_config, custom_client=client)
        assert res_item["outcome"] == TestOutcome.PASS.value
        assert res_item["status_code"] == 201
        assert res_item["response_data"]["id"] == 100

        # 3. Test POST /items with missing payload (Negative Path -> 422 FAIL vs expected 201)
        spec_invalid_item = TestSpecification(
            id="spec-item-002",
            name="POST /items Missing Required Field",
            endpoint_id="ep-items",
            path="/items",
            method="POST",
            test_type=TestType.MISSING_REQUIRED,
            body={},  # missing 'name'
            assertions=[
                AssertionRule(type=AssertionType.STATUS_CODE, expected=201),
            ],
        )

        res_invalid = await HTTPXTestRunner.run_spec(spec_invalid_item, target_env_config, custom_client=client)
        assert res_invalid["outcome"] == TestOutcome.FAIL.value
        assert res_invalid["status_code"] == 422


@pytest.mark.asyncio
async def test_negative_path_matrix(target_transport, target_env_config):
    """
    Validates complete negative path matrix:
    - Target unavailable (ENVIRONMENT_ERROR)
    - Timeout (TIMEOUT)
    - Target 500 error (FAIL)
    - Assertion failure (FAIL)
    """
    # Path A: Unreachable target host/port -> ENVIRONMENT_ERROR
    unreachable_checker = TargetHealthChecker()
    is_live, err_msg = await unreachable_checker.check_liveness("http://127.0.0.1:59999/health", timeout=1.0)
    assert not is_live
    assert "Unreachable" in err_msg or "refused" in err_msg.lower() or "connect" in err_msg.lower()

    # Path B: Timeout handling -> TIMEOUT
    async with AsyncClient(transport=target_transport, base_url="http://testserver") as client:
        spec_slow = TestSpecification(
            id="spec-slow-001",
            name="GET /slow Timeout Test",
            endpoint_id="ep-slow",
            path="/slow",
            method="GET",
            test_type=TestType.BOUNDARY,
            timeout_ms=200,  # Short timeout for endpoint that sleeps 2.0s
            assertions=[AssertionRule(type=AssertionType.STATUS_CODE, expected=200)],
        )

        res_slow = await HTTPXTestRunner.run_spec(spec_slow, target_env_config, custom_client=client)
        assert res_slow["outcome"] == TestOutcome.TIMEOUT.value
        assert "timed out" in res_slow["error_message"].lower()

    # Path C: Target 500 internal server error -> FAIL
    async with AsyncClient(transport=target_transport, base_url="http://testserver") as client:
        spec_500 = TestSpecification(
            id="spec-500-001",
            name="GET /error500 Server Error Test",
            endpoint_id="ep-500",
            path="/error500",
            method="GET",
            test_type=TestType.BOUNDARY,
            assertions=[AssertionRule(type=AssertionType.STATUS_CODE, expected=200)],
        )

        res_500 = await HTTPXTestRunner.run_spec(spec_500, target_env_config, custom_client=client)
        assert res_500["outcome"] == TestOutcome.FAIL.value
        assert res_500["status_code"] == 500


@pytest.mark.asyncio
async def test_ssrf_security_boundary_extended():
    """
    Validates strict security boundary for SSRF protection across schemes, loopbacks,
    private IPs, and metadata endpoints.
    """
    strict_config = TargetEnvironmentConfig(
        base_url="http://example.com",
        is_local_sandbox=False,
    )

    forbidden_urls = [
        "http://127.0.0.1/admin",
        "http://localhost:8000/api",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/internal",
        "http://172.16.0.1/status",
        "http://192.168.1.1/router",
        "file:///etc/passwd",
        "ftp://dl.example.com/file",
        "gopher://example.com/",
    ]

    for forbidden in forbidden_urls:
        with pytest.raises(SSRFValidationError):
            SSRFProtector.validate_url(forbidden, strict_config)

    # Mode 2: Local Sandbox Mode (is_local_sandbox=True)
    sandbox_config = TargetEnvironmentConfig(
        base_url="http://localhost:8000",
        is_local_sandbox=True,
    )

    # Local sandbox allows localhost/127.0.0.1 for local dev target apps
    SSRFProtector.validate_url("http://127.0.0.1:8000/health", sandbox_config)
    SSRFProtector.validate_url("http://localhost:3000/", sandbox_config)

    # But MUST STILL BLOCK non-HTTP schemes and cloud metadata IPs
    with pytest.raises(SSRFValidationError):
        SSRFProtector.validate_url("file:///etc/passwd", sandbox_config)

    with pytest.raises(SSRFValidationError):
        SSRFProtector.validate_url("http://169.254.169.254/latest/meta-data/", sandbox_config)


def test_telemetry_redaction_boundary():
    """
    Verifies that secrets, sensitive headers, and credentials are scrubbed
    prior to DB persistence.
    """
    sensitive_headers = {
        "Authorization": "Bearer secret_jwt_token_9999",
        "Cookie": "session_id=abc123secret",
        "X-API-Key": "sk-proj-secret-key-12345",
        "Content-Type": "application/json",
    }

    redacted_headers = TelemetryRedactor.redact_headers(sensitive_headers)
    assert redacted_headers["Authorization"] == "[REDACTED]"
    assert redacted_headers["Cookie"] == "[REDACTED]"
    assert redacted_headers["X-API-Key"] == "[REDACTED]"
    assert redacted_headers["Content-Type"] == "application/json"

    sensitive_payload = {
        "user_id": 42,
        "email": "user@example.com",
        "password": "SuperSecretPassword!",
        "access_token": "bearer-xyz-123",
        "api_key": "sk-secret-key",
        "nested": {
            "secret": "top-secret-val",
            "normal": "public-val",
        },
    }

    redacted_payload = TelemetryRedactor.redact_json_payload(sensitive_payload)
    assert redacted_payload["password"] == "[REDACTED]"
    assert redacted_payload["access_token"] == "[REDACTED]"
    assert redacted_payload["api_key"] == "[REDACTED]"
    assert redacted_payload["nested"]["secret"] == "[REDACTED]"
    assert redacted_payload["nested"]["normal"] == "public-val"
    assert redacted_payload["user_id"] == 42


@pytest.mark.asyncio
async def test_execution_reproducibility(target_transport, target_env_config):
    """
    Executes identical TestSuite twice against target app and verifies
    100% deterministic test outcomes across runs.
    """
    test_specs = [
        TestSpecification(
            id="rep-001",
            name="Health check",
            endpoint_id="ep-1",
            path="/health",
            method="GET",
            test_type=TestType.HAPPY_PATH,
            assertions=[AssertionRule(type=AssertionType.STATUS_CODE, expected=200)],
        ),
        TestSpecification(
            id="rep-002",
            name="Items list",
            endpoint_id="ep-2",
            path="/items",
            method="GET",
            test_type=TestType.HAPPY_PATH,
            assertions=[AssertionRule(type=AssertionType.STATUS_CODE, expected=200)],
        ),
        TestSpecification(
            id="rep-003",
            name="Error 500 endpoint",
            endpoint_id="ep-3",
            path="/error500",
            method="GET",
            test_type=TestType.BOUNDARY,
            assertions=[AssertionRule(type=AssertionType.STATUS_CODE, expected=200)],  # Will fail
        ),
    ]

    async with AsyncClient(transport=target_transport, base_url="http://testserver") as client:
        # Run #1
        outcomes_run_1 = []
        for spec in test_specs:
            res = await HTTPXTestRunner.run_spec(spec, target_env_config, custom_client=client)
            outcomes_run_1.append((spec.id, res["outcome"], res["status_code"]))

        # Run #2
        outcomes_run_2 = []
        for spec in test_specs:
            res = await HTTPXTestRunner.run_spec(spec, target_env_config, custom_client=client)
            outcomes_run_2.append((spec.id, res["outcome"], res["status_code"]))

    # Assert 100% functional outcome equality between runs
    assert outcomes_run_1 == outcomes_run_2
    assert outcomes_run_1[0] == ("rep-001", TestOutcome.PASS.value, 200)
    assert outcomes_run_1[1] == ("rep-002", TestOutcome.PASS.value, 200)
    assert outcomes_run_1[2] == ("rep-003", TestOutcome.FAIL.value, 500)


def test_canonical_execution_model_architecture():
    """
    Verifies that TestSpecification is the primary canonical execution input,
    proving that execution is decoupled from generated Python source code.
    """
    spec = TestSpecification(
        id="canonical-001",
        name="Canonical test",
        endpoint_id="ep-can",
        path="/health",
        method="GET",
        test_type=TestType.HAPPY_PATH,
        assertions=[AssertionRule(type=AssertionType.STATUS_CODE, expected=200)],
    )

    # Verify dict roundtrip without needing compiler
    spec_dict = spec.to_dict()
    reconstructed_spec = TestSpecification.from_dict(spec_dict)

    assert reconstructed_spec.id == spec.id
    assert reconstructed_spec.path == "/health"
    assert len(reconstructed_spec.assertions) == 1
    assert reconstructed_spec.assertions[0].expected == 200
