"""
ASTRA Sandbox Runner Service.
Provides isolated, ephemeral containerized execution of untrusted user/repository code.
Runs on an internal isolated Docker network; communicates with Docker daemon via mounted socket.
"""

import hmac
import os
import time
from typing import Dict, List, Optional
import docker
from docker.errors import DockerException, NotFound, APIError
from fastapi import FastAPI, Header, HTTPException, status, Depends
from pydantic import BaseModel, Field


app = FastAPI(
    title="ASTRA Sandbox Runner",
    version="1.0.0",
    description="Internal isolated execution service for untrusted test and repository execution"
)

SERVICE_TOKEN = os.environ.get("SANDBOX_SERVICE_TOKEN", "astra_sandbox_runner_internal_token_2026")


def verify_service_token(x_sandbox_token: Optional[str] = Header(None, alias="X-Sandbox-Token")):
    if not x_sandbox_token or not hmac.compare_digest(x_sandbox_token, SERVICE_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Sandbox-Token"
        )


class SandboxExecutionRequest(BaseModel):
    command: List[str] = Field(..., description="Structured argv list, never shell string")
    workspace_path: Optional[str] = Field(None, description="Host workspace directory to mount read-only")
    timeout_seconds: int = Field(30, ge=1, le=120, description="Hard timeout in seconds")
    environment: Optional[Dict[str, str]] = Field(None, description="Container environment variables")
    image: str = Field("python:3.11-slim", description="Base container execution image")
    memory_limit_mb: int = Field(512, ge=64, le=1024, description="Memory limit in megabytes")
    pids_limit: int = Field(128, ge=16, le=256, description="Maximum processes/threads (prevents fork-bombs)")
    cpu_quota: float = Field(1.0, ge=0.1, le=2.0, description="CPU allocation quota")


class SandboxExecutionResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool
    oom_killed: bool


@app.get("/health")
def health():
    return {"status": "healthy", "service": "astra_sandbox_runner"}


@app.post("/execute", response_model=SandboxExecutionResponse, dependencies=[Depends(verify_service_token)])
def execute_sandbox(payload: SandboxExecutionRequest):
    """
    Spawns an ephemeral, resource-constrained container to execute the provided command.
    Enforces non-root, network isolation, PID limits, memory limits, and hard execution timeouts.
    """
    try:
        client = docker.from_env()
    except DockerException as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Docker daemon connection failed: {exc}"
        )

    volumes = {}
    working_dir = "/workspace_work"

    if payload.workspace_path and os.path.exists(payload.workspace_path):
        volumes[payload.workspace_path] = {"bind": "/workspace", "mode": "ro"}
        working_dir = "/workspace"

    container_env = payload.environment.copy() if payload.environment else {}
    container_env["PYTHONUNBUFFERED"] = "1"

    start_time = time.time()
    container = None
    timed_out = False
    oom_killed = False

    try:
        try:
            client.images.get(payload.image)
        except NotFound:
            client.images.pull(payload.image)

        container = client.containers.create(
            image=payload.image,
            command=payload.command,
            network_mode="none",  # Complete network isolation
            mem_limit=f"{payload.memory_limit_mb}m",
            memswap_limit=f"{payload.memory_limit_mb}m",
            nano_cpus=int(payload.cpu_quota * 1_000_000_000),
            pids_limit=payload.pids_limit,
            user="1000:1000",  # Non-root user
            read_only=True,    # Read-only root filesystem
            security_opt=["no-new-privileges:true"],
            cap_drop=["ALL"],
            tmpfs={
                "/tmp": "rw,noexec,nosuid,size=64m",
                "/workspace_work": "rw,size=128m"
            },
            volumes=volumes,
            working_dir=working_dir,
            environment=container_env,
            detach=True
        )

        container.start()

        # Poll status until finished or timeout
        deadline = start_time + payload.timeout_seconds
        while time.time() < deadline:
            container.reload()
            if container.status != "running":
                break
            time.sleep(0.2)
        else:
            # Exceeded timeout: kill container
            timed_out = True
            try:
                container.kill()
            except Exception:
                pass

        container.reload()
        state = container.attrs.get("State", {})
        oom_killed = bool(state.get("OOMKilled", False))
        exit_code = state.get("ExitCode", 124 if timed_out else 1)

        raw_logs = container.logs(stdout=True, stderr=True)
        output_str = raw_logs.decode("utf-8", errors="replace")

        duration_ms = round((time.time() - start_time) * 1000, 2)

        return SandboxExecutionResponse(
            exit_code=exit_code,
            stdout=output_str,
            stderr="[ASTRA CONTAINER TIMEOUT] Execution exceeded maximum allocated time limit." if timed_out else "",
            duration_ms=duration_ms,
            timed_out=timed_out,
            oom_killed=oom_killed
        )

    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return SandboxExecutionResponse(
            exit_code=1,
            stdout="",
            stderr=f"Sandbox runner error: {str(exc)}",
            duration_ms=duration_ms,
            timed_out=False,
            oom_killed=False
        )

    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass
