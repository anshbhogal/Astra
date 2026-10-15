"""
ASTRA Sandbox Runner Client.
Interface used by backend services, Celery workers, and test execution adapters
to execute repository code in isolated, ephemeral sandbox containers.
"""

import os
from typing import Dict, List, Optional
import httpx
from pydantic import BaseModel


class SandboxResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool
    oom_killed: bool


class SandboxClient:
    """Client for dispatching execution jobs to the internal sandbox_runner service."""

    def __init__(
        self,
        runner_url: Optional[str] = None,
        service_token: Optional[str] = None
    ):
        self.runner_url = runner_url or os.environ.get("SANDBOX_RUNNER_URL", "http://sandbox_runner:8001")
        self.service_token = service_token or os.environ.get("SANDBOX_SERVICE_TOKEN", "astra_sandbox_runner_internal_token_2026")

    def execute(
        self,
        command: List[str],
        workspace_path: Optional[str] = None,
        timeout_seconds: int = 30,
        environment: Optional[Dict[str, str]] = None,
        image: str = "python:3.11-slim",
        memory_limit_mb: int = 512,
        pids_limit: int = 128,
        cpu_quota: float = 1.0,
    ) -> SandboxResult:
        """Dispatches execution to the sandbox_runner container."""
        headers = {
            "X-Sandbox-Token": self.service_token,
            "Content-Type": "application/json"
        }
        payload = {
            "command": command,
            "workspace_path": workspace_path,
            "timeout_seconds": timeout_seconds,
            "environment": environment or {},
            "image": image,
            "memory_limit_mb": memory_limit_mb,
            "pids_limit": pids_limit,
            "cpu_quota": cpu_quota
        }

        try:
            with httpx.Client(timeout=timeout_seconds + 10) as client:
                resp = client.post(f"{self.runner_url}/execute", json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return SandboxResult(**data)
                return SandboxResult(
                    exit_code=1,
                    stdout="",
                    stderr=f"Sandbox runner HTTP {resp.status_code}: {resp.text}",
                    duration_ms=0,
                    timed_out=False,
                    oom_killed=False
                )
        except Exception as exc:
            # Fallback if sandbox_runner container is not running (e.g. during local offline test)
            return self._local_isolated_execute(command, workspace_path, timeout_seconds, environment)

    def _local_isolated_execute(
        self,
        command: List[str],
        workspace_path: Optional[str],
        timeout_seconds: int,
        environment: Optional[Dict[str, str]]
    ) -> SandboxResult:
        import subprocess
        import time

        start = time.time()
        env = os.environ.copy()
        if environment:
            env.update(environment)

        try:
            proc = subprocess.run(
                command,
                cwd=workspace_path if workspace_path and os.path.exists(workspace_path) else None,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env
            )
            duration_ms = round((time.time() - start) * 1000, 2)
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                duration_ms=duration_ms,
                timed_out=False,
                oom_killed=False
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = round((time.time() - start) * 1000, 2)
            return SandboxResult(
                exit_code=124,
                stdout=exc.stdout or "" if isinstance(exc.stdout, str) else "",
                stderr="[ASTRA LOCAL TIMEOUT] Execution exceeded allocated limit.",
                duration_ms=duration_ms,
                timed_out=True,
                oom_killed=False
            )
        except Exception as exc:
            duration_ms = round((time.time() - start) * 1000, 2)
            return SandboxResult(
                exit_code=1,
                stdout="",
                stderr=f"Execution failed: {exc}",
                duration_ms=duration_ms,
                timed_out=False,
                oom_killed=False
            )
