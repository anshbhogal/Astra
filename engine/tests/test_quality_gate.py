import pytest
from engine.cicd.quality_gate import QualityGateEvaluator


def test_quality_gate_evaluator_outcomes():
    evaluator = QualityGateEvaluator(block_on_non_critical=True)

    # 1. All Pass
    res_pass = evaluator.evaluate(total_tests=5, passed_tests=5, failed_tests=0)
    assert res_pass.status == "PASS"
    assert res_pass.blocking is False

    # 2. Critical Failure
    res_fail = evaluator.evaluate(total_tests=5, passed_tests=4, failed_tests=1, critical_failures=1)
    assert res_fail.status == "FAIL"
    assert res_fail.blocking is True

    # 3. Environment Error
    res_err = evaluator.evaluate(total_tests=5, passed_tests=0, failed_tests=0, environment_error=True)
    assert res_err.status == "ERROR"
    assert res_err.blocking is True
