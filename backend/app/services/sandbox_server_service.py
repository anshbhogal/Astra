import asyncio
import os
import sys
import uuid
import socket
import subprocess
import signal
import json
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Project, DiscoveredEndpoint, ProjectAnalysis


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_pid_alive(pid: int) -> bool:
    """Check if process is running by PID."""
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def terminate_pid(pid: int) -> None:
    """Gracefully terminate and then kill process by PID."""
    if not is_pid_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    # Quick grace period check
    try:
        for _ in range(5):
            if not is_pid_alive(pid):
                return
            import time
            time.sleep(0.05)
        os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def is_port_in_use(port: int) -> bool:
    """Check whether a port is currently listening or bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
            return False
        except OSError:
            return True


def find_available_port(start_port: int = 5000, end_port: int = 9000) -> int:
    """Dynamically scan sockets to find the lowest available free port."""
    for port in range(start_port, end_port):
        # Skip standard reserved infrastructure ports
        if port in [5432, 6379, 8000, 3000]:
            continue
        if not is_port_in_use(port):
            return port

    # Fallback to ephemeral allocation
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class SandboxServerInstance:
    def __init__(
        self,
        project_id: str,
        port: int,
        mode: str,
        pid: int,
        process: Optional[subprocess.Popen] = None,
        script_path: Optional[str] = None,
        custom_command: Optional[str] = None,
        started_at: Optional[datetime] = None
    ):
        self.project_id = project_id
        self.port = port
        self.mode = mode
        self.pid = pid
        self.process = process
        self.script_path = script_path
        self.custom_command = custom_command
        self.started_at = started_at or utc_now()

    def is_alive(self) -> bool:
        if self.process:
            return self.process.poll() is None
        return is_pid_alive(self.pid)

    def terminate(self) -> None:
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        if is_pid_alive(self.pid):
            terminate_pid(self.pid)

        if self.script_path and os.path.exists(self.script_path):
            try:
                os.remove(self.script_path)
            except Exception:
                pass


# Process registry keyed by project_id
ACTIVE_SANDBOX_SERVERS: Dict[str, SandboxServerInstance] = {}


class SandboxServerService:
    @classmethod
    def _get_storage_dir(cls) -> str:
        """Store scripts and persistent state in OS temp directory outside backend reload watcher."""
        path = os.path.join(tempfile.gettempdir(), "astra_sandboxes")
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def _get_registry_file(cls) -> str:
        return os.path.join(cls._get_storage_dir(), "registry.json")

    @classmethod
    def _load_disk_registry(cls) -> Dict[str, Any]:
        reg_file = cls._get_registry_file()
        if not os.path.exists(reg_file):
            return {}
        try:
            with open(reg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def _save_disk_registry(cls, data: Dict[str, Any]) -> None:
        reg_file = cls._get_registry_file()
        try:
            with open(reg_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def get_suggested_port(cls) -> int:
        cls._cleanup_stale_servers()
        return find_available_port(5000, 9000)

    @classmethod
    def _cleanup_stale_servers(cls) -> None:
        """Prune dead processes from memory and disk registry."""
        disk_data = cls._load_disk_registry()
        modified = False
        for pid_str, item in list(disk_data.items()):
            pid = item.get("pid")
            if not is_pid_alive(pid):
                script_path = item.get("script_path")
                if script_path and os.path.exists(script_path):
                    try:
                        os.remove(script_path)
                    except Exception:
                        pass
                disk_data.pop(pid_str, None)
                ACTIVE_SANDBOX_SERVERS.pop(pid_str, None)
                modified = True
        if modified:
            cls._save_disk_registry(disk_data)

    @classmethod
    def get_server_status(cls, project_id: str) -> Dict[str, Any]:
        # 1. Check in-memory first
        inst = ACTIVE_SANDBOX_SERVERS.get(project_id)
        if inst and inst.is_alive():
            uptime = (utc_now() - inst.started_at).total_seconds()
            return {
                "project_id": project_id,
                "status": "RUNNING",
                "port": inst.port,
                "base_url": f"http://localhost:{inst.port}",
                "mode": inst.mode,
                "custom_command": inst.custom_command,
                "started_at": inst.started_at.isoformat(),
                "uptime_seconds": round(uptime, 1)
            }

        # 2. Check disk registry if in-memory was cleared by backend reload
        disk_data = cls._load_disk_registry()
        entry = disk_data.get(project_id)
        if entry:
            pid = entry.get("pid")
            if is_pid_alive(pid):
                started_dt = utc_now()
                try:
                    if entry.get("started_at"):
                        started_dt = datetime.fromisoformat(entry["started_at"])
                except Exception:
                    pass

                # Restore into memory
                inst = SandboxServerInstance(
                    project_id=project_id,
                    port=entry.get("port"),
                    mode=entry.get("mode", "HYBRID"),
                    pid=pid,
                    script_path=entry.get("script_path"),
                    custom_command=entry.get("custom_command"),
                    started_at=started_dt
                )
                ACTIVE_SANDBOX_SERVERS[project_id] = inst
                uptime = (utc_now() - started_dt).total_seconds()
                return {
                    "project_id": project_id,
                    "status": "RUNNING",
                    "port": inst.port,
                    "base_url": f"http://localhost:{inst.port}",
                    "mode": inst.mode,
                    "custom_command": inst.custom_command,
                    "started_at": started_dt.isoformat(),
                    "uptime_seconds": round(uptime, 1)
                }
            else:
                # Clean dead record
                disk_data.pop(project_id, None)
                cls._save_disk_registry(disk_data)

        return {
            "project_id": project_id,
            "status": "STOPPED",
            "port": None,
            "base_url": None,
            "mode": None,
            "uptime_seconds": 0
        }

    @classmethod
    async def stop_server(cls, project_id: str) -> Dict[str, Any]:
        pid_str = str(project_id)
        inst = ACTIVE_SANDBOX_SERVERS.pop(pid_str, None)
        port = None
        if inst:
            port = inst.port
            inst.terminate()

        disk_data = cls._load_disk_registry()
        entry = disk_data.pop(pid_str, None)
        if entry:
            if not port:
                port = entry.get("port")
            pid = entry.get("pid")
            if pid:
                terminate_pid(pid)
            script_path = entry.get("script_path")
            if script_path and os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except Exception:
                    pass
            cls._save_disk_registry(disk_data)

        if port:
            return {"status": "STOPPED", "message": f"Sandbox server on port {port} shut down."}
        return {"status": "STOPPED", "message": "No active sandbox server was running."}

    @classmethod
    async def start_server(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        port: Optional[int] = None,
        mode: str = "HYBRID",
        custom_command: Optional[str] = None
    ) -> Dict[str, Any]:
        pid_str = str(project_id)

        # 1. Terminate existing server for this project if any
        await cls.stop_server(pid_str)

        target_port = port if port else find_available_port(5000, 9000)

        # 2. If target_port is currently held by any rogue or previous process, kill it
        disk_data = cls._load_disk_registry()
        for k, v in list(disk_data.items()):
            if v.get("port") == target_port:
                terminate_pid(v.get("pid"))
                disk_data.pop(k, None)
        cls._save_disk_registry(disk_data)

        # 3. Retrieve project and discovered endpoints from DB
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
        chosen_mode = mode_upper
        storage_dir = cls._get_storage_dir()
        script_file_name = f"sandbox_{pid_str.replace('-', '_')}.py"
        script_path = os.path.join(storage_dir, script_file_name)

        # 4. Launch Native Command mode if selected
        if mode_upper == "NATIVE_COMMAND" and custom_command:
            proc = subprocess.Popen(
                custom_command,
                shell=True,
                env={**os.environ, "PORT": str(target_port)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            inst = SandboxServerInstance(
                project_id=pid_str,
                port=target_port,
                mode="NATIVE_COMMAND",
                pid=proc.pid,
                process=proc,
                custom_command=custom_command
            )
            ACTIVE_SANDBOX_SERVERS[pid_str] = inst
            disk_data[pid_str] = {
                "pid": proc.pid,
                "port": target_port,
                "mode": "NATIVE_COMMAND",
                "custom_command": custom_command,
                "started_at": utc_now().isoformat()
            }
            cls._save_disk_registry(disk_data)
            await cls._wait_for_server_ready(target_port, timeout_s=4.0)
            return cls.get_server_status(pid_str)

        # 5. Hybrid or Endpoint Sandbox: Write script to external storage_dir (outside /app)
        endpoints_data = [
            {
                "path": ep.path,
                "method": ep.method,
                "function_name": ep.function_name,
                "parameters": ep.parameters,
                "summary": f"{ep.method} {ep.path}"
            }
            for ep in endpoints
        ]

        server_code = cls._generate_mock_server_code(project.name, endpoints_data)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(server_code)

        # Launch standalone Python process running uvicorn internally
        proc = subprocess.Popen(
            [sys.executable, script_path, str(target_port)],
            cwd=storage_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        inst = SandboxServerInstance(
            project_id=pid_str,
            port=target_port,
            mode=chosen_mode,
            pid=proc.pid,
            process=proc,
            script_path=script_path
        )
        ACTIVE_SANDBOX_SERVERS[pid_str] = inst

        disk_data[pid_str] = {
            "pid": proc.pid,
            "port": target_port,
            "mode": chosen_mode,
            "script_path": script_path,
            "started_at": utc_now().isoformat()
        }
        cls._save_disk_registry(disk_data)

        # Poll health until responsive
        await cls._wait_for_server_ready(target_port, timeout_s=5.0)
        return cls.get_server_status(pid_str)

    @classmethod
    async def _wait_for_server_ready(cls, port: int, timeout_s: float = 4.0) -> bool:
        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) < timeout_s:
            try:
                async with httpx.AsyncClient(timeout=0.3) as client:
                    res = await client.get(f"http://localhost:{port}/health")
                    if res.status_code in [200, 204, 301, 302]:
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.15)
        return False

    @staticmethod
    def _generate_mock_server_code(project_name: str, endpoints: List[Dict[str, Any]]) -> str:
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
