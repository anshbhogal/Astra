from engine.models.test_spec import TestSpecification, AssertionRule, AssertionType, TestType
from engine.assertions.evaluator import AssertionEvaluator


def test_status_code_assertion_success():
    spec = TestSpecification(
        id="test-1",
        name="Test 1",
        endpoint_id="ep-1",
        test_type=TestType.HAPPY_PATH,
        method="GET",
        path="/health",
        expected_status=[200, 201]
    )
    failures = AssertionEvaluator.evaluate(spec, status_code=200, response_body={"status": "ok"}, response_headers={}, duration_ms=50.0)
    assert len(failures) == 0


def test_status_code_assertion_failure():
    spec = TestSpecification(
        id="test-1",
        name="Test 1",
        endpoint_id="ep-1",
        test_type=TestType.HAPPY_PATH,
        method="GET",
        path="/health",
        expected_status=[200]
    )
    failures = AssertionEvaluator.evaluate(spec, status_code=500, response_body={"error": "Internal Error"}, response_headers={}, duration_ms=50.0)
    assert len(failures) == 1
    assert failures[0]["type"] == "STATUS_CODE_MISMATCH"


def test_json_schema_assertion():
    schema = {
        "type": "object",
        "properties": {"status": {"type": "string"}},
        "required": ["status"]
    }
    spec = TestSpecification(
        id="test-2",
        name="Test 2",
        endpoint_id="ep-2",
        test_type=TestType.HAPPY_PATH,
        method="GET",
        path="/health",
        expected_status=[200],
        expected_schema=schema
    )
    failures = AssertionEvaluator.evaluate(spec, status_code=200, response_body={"status": 123}, response_headers={}, duration_ms=50.0)
    assert len(failures) == 1
    assert failures[0]["type"] == "SCHEMA_VALIDATION_ERROR"


def test_latency_sla_assertion():
    spec = TestSpecification(
        id="test-3",
        name="Test 3",
        endpoint_id="ep-3",
        test_type=TestType.HAPPY_PATH,
        method="GET",
        path="/slow",
        expected_status=[200],
        assertions=[AssertionRule(type=AssertionType.LATENCY_SLA, expected=100.0)]
    )
    failures = AssertionEvaluator.evaluate(spec, status_code=200, response_body={}, response_headers={}, duration_ms=250.0)
    assert len(failures) == 1
    assert failures[0]["type"] == "LATENCY_SLA_EXCEEDED"
