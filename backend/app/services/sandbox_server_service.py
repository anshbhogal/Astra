"""
ASTRA Sandbox Server Service (Containerized Lifecycle — P0.5).
Manages project mock-server containers through the authenticated sandbox_runner service.
Guarantees zero host-side execution of untrusted mock scripts.
"""

import asyncio
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Project, DiscoveredEndpoint, ProjectAnalysis
from engine.execution.sandbox_client import SandboxClient


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_port_in_use(port: int) -> bool:
    """Check whether a port is currently listening or bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
            return False
        except OSError:
            return True


def find_available_port(start_port: int = 5000, end_port: int = 9000, excluded_ports: Optional[set] = None) -> int:
    """Dynamically scan sockets to find the lowest available free port, avoiding excluded ports."""
    excluded = set(excluded_ports or [])
    for port in range(start_port, end_port):
        # Skip standard infrastructure ports and currently allocated ports
        if port in [5432, 5433, 6379, 8000, 8001, 3000] or port in excluded:
            continue
        if not is_port_in_use(port):
            return port

    # Fallback to OS ephemeral allocation
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class SandboxServerService:
    """
    Orchestrates the lifecycle of containerized mock servers.
    All execution, port binding, and process lifecycles are delegated to the
    isolated astra_sandbox_runner Docker service.
    """

    _client: Optional[SandboxClient] = None

    @classmethod
    def _get_client(cls) -> SandboxClient:
        if cls._client is None:
            runner_url = os.environ.get("SANDBOX_RUNNER_URL", "http://sandbox_runner:8001")
            token = os.environ.get("SANDBOX_SERVICE_TOKEN", "astra_sandbox_runner_internal_token_2026")
            cls._client = SandboxClient(runner_url=runner_url, service_token=token)
        return cls._client

    @classmethod
    def get_suggested_port(cls) -> int:
        """Finds an available free port after triggering cleanup of expired containers and avoiding active ports."""
        try:
            cls._get_client().cleanup_expired_servers()
        except Exception:
            pass
        excluded = set()
        try:
            excluded = set(cls._get_client().get_allocated_ports())
        except Exception:
            pass
        return find_available_port(5000, 9000, excluded_ports=excluded)

    @classmethod
    def get_server_status(cls, project_id: str) -> Dict[str, Any]:
        """Queries the sandbox runner for the container status of the project mock server."""
        return cls._get_client().get_mock_server_status(str(project_id))

    @classmethod
    async def stop_server(cls, project_id: str) -> Dict[str, Any]:
        """Instructs the sandbox runner to terminate and destroy the mock server container."""
        return cls._get_client().stop_mock_server(str(project_id))

    @classmethod
    async def start_server(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        port: Optional[int] = None,
        mode: str = "HYBRID"
    ) -> Dict[str, Any]:
        """
        Synthesizes mock server logic from discovered endpoints and dispatches a containerized
        server startup request to the sandbox runner service.
        """
        pid_str = str(project_id)

        # 1. Terminate existing container if any
        await cls.stop_server(pid_str)

        # 2. Allocate free port
        target_port = port if port else find_available_port(5000, 9000)

        # 3. Retrieve project and discovered endpoints
        stmt_proj = select(Project).where(Project.id == project_id)
        res_proj = await db.execute(stmt_proj)
        project = res_proj.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found.")

        stmt_analysis = (
            select(ProjectAnalysis)
            .where(ProjectAnalysis.project_id == project_id)
            .order_by(ProjectAnalysis.created_at.desc())
        )
        res_analysis = await db.execute(stmt_analysis)
        analysis = res_analysis.scalars().first()

        endpoints = []
        if analysis:
            stmt_ep = select(DiscoveredEndpoint).where(DiscoveredEndpoint.analysis_id == analysis.id)
            endpoints = (await db.execute(stmt_ep)).scalars().all()

        mode_upper = mode.upper().strip()
        if mode_upper not in ["HYBRID", "ENDPOINT_SANDBOX"]:
            mode_upper = "HYBRID"
        chosen_mode = mode_upper

        endpoints_data = [
            {
                "path": ep.path,
                "method": ep.method,
                "function_name": ep.function_name,
                "parameters": ep.parameters,
                "summary": f"{ep.method} {ep.path}",
            }
            for ep in endpoints
        ]

        # 4. Generate mock server code
        server_code = cls._generate_mock_server_code(project.name, endpoints_data)

        # 5. Dispatch container launch to isolated sandbox runner
        return cls._get_client().start_mock_server(
            project_id=pid_str,
            server_code=server_code,
            port=target_port,
            project_name=project.name,
            mode=chosen_mode,
            timeout_seconds=1800,  # 30-minute automated expiry
            memory_limit_mb=512,
            pids_limit=64,
            cpu_quota=1.0,
        )

    @staticmethod
    def _generate_mock_server_code(project_name: str, endpoints: List[Dict[str, Any]]) -> str:
        """Generates self-contained FastAPI mock server Python code."""
        code_lines = [
            "import json",
            "import sys",
            "import uvicorn",
            "from fastapi import FastAPI, Request, Response",
            "from fastapi.responses import JSONResponse",
            "from fastapi.middleware.cors import CORSMiddleware",
            "",
            "app = FastAPI(",
            f'    title="Astra Dynamic Sandbox - {project_name}",',
            '    version="1.0.0",',
            '    docs_url="/docs"',
            ")",
            "",
            "app.add_middleware(",
            "    CORSMiddleware,",
            "    allow_origins=['*'],",
            "    allow_credentials=True,",
            "    allow_methods=['*'],",
            "    allow_headers=['*'],",
            ")",
            "",
            f"REGISTERED_ENDPOINTS = {repr(endpoints)}",
            "",
            "@app.get('/health')",
            "async def health_check():",
            f"    return {{'status': 'healthy', 'service': '{project_name}', 'registered_routes': len(REGISTERED_ENDPOINTS)}}",
            "",
            "@app.get('/')",
            "async def root_index():",
            f"    return {{'message': 'Welcome to {project_name} Sandbox API', 'status': 'operational'}}",
            "",
            "@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])",
            "async def handle_dynamic_route(request: Request, path: str):",
            "    norm_path = '/' + path.strip('/')",
            "    method = request.method.upper()",
            "",
            "    # Special case: direct health",
            "    if norm_path == '/health':",
            "        return {'status': 'healthy', 'uptime': 'active'}",
            "",
            "    # Find matching endpoint",
            "    matched = None",
            "    for ep in REGISTERED_ENDPOINTS:",
            "        ep_path = ep['path'].strip('/')",
            "        if ep['method'].upper() == method and (norm_path == '/' + ep_path or path.startswith(ep_path)):",
            "            matched = ep",
            "            break",
            "",
            "    # Auth check simulation if endpoint requires authentication and request lacks Authorization",
            "    if matched and matched.get('auth_required'):",
            "        auth_hdr = request.headers.get('authorization')",
            "        if not auth_hdr:",
            "            return JSONResponse(",
            "                status_code=401,",
            "                content={'detail': 'Authentication credentials were not provided.'}",
            "            )",
            "",
            "    # Default realistic JSON response",
            "    return JSONResponse(",
            "        status_code=200,",
            "        content={",
            "            'status': 'success',",
            "            'endpoint': norm_path,",
            "            'method': method,",
            "            'data': {",
            "                'id': 'test_sandbox_123',",
            "                'simulated': True,",
            "                'project': '" + project_name + "'",
            "            }",
            "        }",
            "    )",
            "",
            "if __name__ == '__main__':",
            "    port_val = int(sys.argv[1]) if len(sys.argv) > 1 else 5000",
            "    uvicorn.run(app, host='0.0.0.0', port=port_val, log_level='warning')",
        ]
        return "\n".join(code_lines)
