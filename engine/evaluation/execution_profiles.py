"""Execution Profiles for Empirical Benchmark Evaluation.

Implements dual execution profiles:
1. IN_PROCESS_DETERMINISTIC: Fast, deterministic execution via ASGITransport and isolated in-memory SQLite.
2. CONCURRENT_TRANSACTIONAL: Concurrent requests via asyncio.gather to reproduce true race conditions.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import httpx
from fastapi import FastAPI

from benchmark_apps.catalog import BenchmarkExecutionProfile


@dataclass
class ProfileExecutionResult:
    status_code: int
    response_data: Any
    execution_time_ms: float
    headers: Dict[str, str] = field(default_factory=dict)
    was_concurrent: bool = False
    concurrency_responses: List[Dict[str, Any]] = field(default_factory=list)


class ExecutionProfileRunner:
    """Dispatches test requests under deterministic or concurrent execution profiles."""

    @staticmethod
    async def execute_request(
        app: FastAPI,
        method: str,
        path: str,
        profile: BenchmarkExecutionProfile = BenchmarkExecutionProfile.IN_PROCESS_DETERMINISTIC,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        concurrency_count: int = 2
    ) -> ProfileExecutionResult:
        transport = httpx.ASGITransport(app=app)
        start_time = time.perf_counter()

        if profile == BenchmarkExecutionProfile.CONCURRENT_TRANSACTIONAL:
            # Execute multiple simultaneous concurrent requests to reproduce race conditions
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                async def single_call():
                    try:
                        resp = await client.request(method, path, json=json_data, params=params, headers=headers)
                        try:
                            data = resp.json()
                        except Exception:
                            data = resp.text
                        return {"status_code": resp.status_code, "data": data, "headers": dict(resp.headers)}
                    except Exception as exc:
                        return {"status_code": 500, "data": {"error": str(exc)}, "headers": {}}

                tasks = [single_call() for _ in range(concurrency_count)]
                responses = await asyncio.gather(*tasks)

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            primary = responses[0]
            return ProfileExecutionResult(
                status_code=primary["status_code"],
                response_data=primary["data"],
                execution_time_ms=duration_ms,
                headers=primary["headers"],
                was_concurrent=True,
                concurrency_responses=responses
            )

        # Standard deterministic profile
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            try:
                resp = await client.request(method, path, json=json_data, params=params, headers=headers)
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return ProfileExecutionResult(
                    status_code=resp.status_code,
                    response_data=data,
                    execution_time_ms=duration_ms,
                    headers=dict(resp.headers),
                    was_concurrent=False
                )
            except Exception as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return ProfileExecutionResult(
                    status_code=500,
                    response_data={"error": str(exc)},
                    execution_time_ms=duration_ms,
                    headers={},
                    was_concurrent=False
                )
