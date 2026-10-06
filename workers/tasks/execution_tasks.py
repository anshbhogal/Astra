import time
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from app.core.celery_app import celery_app
from app.db.session import async_session_factory
from app.models.domain import (
    TestRun, TestSuite, TestCase, TestResult, TestRunStatus, TestOutcome, TestType
)
from sqlalchemy import select

from engine.models.test_spec import TestSpecification
from engine.models.target_env import TargetEnvironmentConfig
from engine.executor.health_checker import HealthChecker
from engine.executor.httpx_runner import HTTPXTestRunner


def utc_now():
    return datetime.now(timezone.utc)


async def execute_test_run_pipeline(test_run_id_str: str) -> None:
    test_run_id = uuid.UUID(test_run_id_str)

    async with async_session_factory() as db:
        stmt = select(TestRun).where(TestRun.id == test_run_id)
        result = await db.execute(stmt)
        run = result.scalar_one_or_none()

        if not run:
            return

        try:
            # Stage 1: STARTING
            run.status = TestRunStatus.STARTING
            run.started_at = utc_now()
            await db.commit()

            env_config = TargetEnvironmentConfig.from_dict(run.target_environment or {})

            # Stage 2: Pre-flight Liveness Health Check
            is_healthy, health_msg = await HealthChecker.check_health(env_config)
            if not is_healthy:
                run.status = TestRunStatus.ENVIRONMENT_ERROR
                run.error_message = f"Pre-flight Health Check Failed: {health_msg}"
                run.completed_at = utc_now()
                await db.commit()
                return

            # Stage 3: Fetch TestCases for Suite
            stmt_cases = (
                select(TestCase)
                .where(TestCase.suite_id == run.suite_id)
                .order_by(TestCase.execution_order.asc())
            )
            cases = (await db.execute(stmt_cases)).scalars().all()

            run.status = TestRunStatus.RUNNING
            run.total_tests = len(cases)
            await db.commit()

            start_time = time.perf_counter()
            passed_count = 0
            failed_count = 0
            error_count = 0

            # Import redis client for cooperative cancellation check
            import redis.asyncio as aioredis
            from app.core.config import settings
            r = aioredis.from_url(settings.REDIS_URL)

            for tc in cases:
                # Cooperative Cancellation Check
                is_cancelled = await r.get(f"cancel_test_run:{run.id}")
                if is_cancelled:
                    run.status = TestRunStatus.CANCELLED
                    run.error_message = "Test run cancelled by user."
                    run.completed_at = utc_now()
                    await db.commit()
                    await r.aclose()
                    return

                spec_dict = tc.specification or {}
                spec = TestSpecification.from_dict(spec_dict)

                # Execute HTTP Spec
                res_dict = await HTTPXTestRunner.run_spec(spec, env_config)

                outcome_str = res_dict["outcome"]
                if outcome_str == TestOutcome.PASS.value:
                    passed_count += 1
                elif outcome_str == TestOutcome.FAIL.value:
                    failed_count += 1
                else:
                    error_count += 1

                t_type = tc.test_type if isinstance(tc.test_type, TestType) else TestType(tc.test_type)
                t_outcome = TestOutcome(outcome_str) if isinstance(outcome_str, str) else outcome_str

                # Create TestResult DB entity
                db_result = TestResult(
                    test_run_id=run.id,
                    test_case_id=tc.id,
                    endpoint=spec.path,
                    method=spec.method,
                    test_type=t_type,
                    outcome=t_outcome,
                    status_code=res_dict.get("status_code"),
                    request_data=res_dict.get("request_data", {}),
                    response_data=res_dict.get("response_data"),
                    response_body_truncated=res_dict.get("response_body_truncated", False),
                    execution_time_ms=res_dict.get("execution_time_ms", 0.0),
                    assertion_failures=res_dict.get("assertion_failures", []),
                    error_message=res_dict.get("error_message")
                )
                db.add(db_result)

                # Update running counters
                run.passed_tests = passed_count
                run.failed_tests = failed_count
                run.error_tests = error_count
                run.duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                await db.commit()

            await r.aclose()

            # Finish Test Run
            run.duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            run.completed_at = utc_now()
            if failed_count > 0 or error_count > 0:
                run.status = TestRunStatus.FAILED
            else:
                run.status = TestRunStatus.COMPLETED
            await db.commit()

        except Exception as e:
            run.status = TestRunStatus.FAILED
            run.error_message = str(e)
            run.completed_at = utc_now()
            await db.commit()


@celery_app.task(name="tasks.run_test_suite_execution_task")
def run_test_suite_execution_task(test_run_id_str: str) -> Dict[str, Any]:
    asyncio.run(execute_test_run_pipeline(test_run_id_str))
    return {"test_run_id": test_run_id_str, "status": "FINISHED"}
