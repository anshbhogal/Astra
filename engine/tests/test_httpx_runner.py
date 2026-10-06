import pytest
from engine.models.test_spec import TestSpecification, TestType
from engine.models.target_env import TargetEnvironmentConfig, EnvironmentType
from engine.executor.httpx_runner import HTTPXTestRunner


@pytest.mark.asyncio
async def test_httpx_runner_unreachable_target():
    spec = TestSpecification(
        id="test-1",
        name="Test Unreachable",
        endpoint_id="ep-1",
        test_type=TestType.HAPPY_PATH,
        method="GET",
        path="/nonexistent"
    )
    config = TargetEnvironmentConfig(
        base_url="http://127.0.0.1:59999",  # Port where nothing is listening
        environment_type=EnvironmentType.LOCAL_SANDBOX,
        timeout_seconds=1.0
    )
    res = await HTTPXTestRunner.run_spec(spec, config)
    assert res["outcome"] in ["ERROR", "TIMEOUT"]
    assert res["status_code"] is None
