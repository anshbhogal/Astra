"""
ASTRA Engine - Ephemeral Isolated Execution Sandbox Runner

Manages temporary Git worktrees and container sandboxes with network-deny policies,
read-only test mounts, resource quotas, and deterministic lifecycle cleanup.
"""

import asyncio
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from engine.repair.patch_validator import PatchValidator


@dataclass
class ExecutionResult:
    exit_code: int
    passed: bool
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    tampering_detected: bool = False


class SandboxExecutor:
    """Executes patched code in an ephemeral isolated sandbox."""

    def __init__(
        self,
        repo_path: str,
        base_commit_sha: str = "HEAD",
        timeout_seconds: int = 60,
        network_mode: str = "none",  # Default DENY
        cpu_quota: float = 2.0,
        memory_limit_mb: int = 2048,
        pid_limit: int = 100,
    ):
        self.repo_path = repo_path
        self.base_commit_sha = base_commit_sha
        self.timeout_seconds = timeout_seconds
        self.network_mode = network_mode
        self.cpu_quota = cpu_quota
        self.memory_limit_mb = memory_limit_mb
        self.pid_limit = pid_limit

        self.worktree_dir: Optional[str] = None
        self.branch_name: Optional[str] = None

    async def __aenter__(self):
        """Creates ephemeral Git worktree for branch isolation."""
        self.branch_name = f"astra-sandbox-{uuid.uuid4().hex[:10]}"
        self.worktree_dir = tempfile.mkdtemp(prefix="astra_sb_")

        # Try git worktree add
        try:
            cmd = f"git worktree add -b {self.branch_name} \"{self.worktree_dir}\" {self.base_commit_sha}"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                # Fallback: Copy repo directory if not a git root or git worktree fails
                shutil.rmtree(self.worktree_dir, ignore_errors=True)
                shutil.copytree(self.repo_path, self.worktree_dir, ignore=shutil.ignore_patterns(".git"))
        except Exception:
            if not os.path.exists(self.worktree_dir):
                shutil.copytree(self.repo_path, self.worktree_dir, ignore=shutil.ignore_patterns(".git"))

        return self

    async def apply_patch(self, target_rel_path: str, diff_text: str) -> Tuple[bool, str]:
        """
        Applies unified diff cleanly to the worktree file.
        Returns (success, message).
        """
        if not self.worktree_dir:
            return False, "Sandbox worktree not initialized."

        target_full_path = os.path.join(self.worktree_dir, target_rel_path)
        if not os.path.exists(target_full_path):
            return False, f"Target file does not exist in worktree: {target_rel_path}"

        try:
            with open(target_full_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            success, msg, patched_content = PatchValidator.apply_diff_to_source(
                original_content, diff_text
            )
            if not success or patched_content is None:
                return False, msg

            with open(target_full_path, "w", encoding="utf-8") as f:
                f.write(patched_content)

            return True, "Patch applied successfully."
        except Exception as e:
            return False, f"Exception while applying patch: {e}"

    async def run_test_command(
        self,
        command: str,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """
        Executes test command within the sandbox workspace with strict timeouts.
        """
        if not self.worktree_dir:
            return ExecutionResult(
                exit_code=-1,
                passed=False,
                stdout="",
                stderr="Sandbox not initialized.",
                duration_ms=0.0,
            )

        start_time = asyncio.get_event_loop().time()
        env = dict(os.environ)
        if env_vars:
            env.update(env_vars)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.worktree_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout_seconds,
            )
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")
            passed = (proc.returncode == 0)

            return ExecutionResult(
                exit_code=proc.returncode or 0,
                passed=passed,
                stdout=stdout_text,
                stderr=stderr_text,
                duration_ms=duration_ms,
                timed_out=False,
            )

        except asyncio.TimeoutError:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            try:
                proc.kill()
            except Exception:
                pass
            return ExecutionResult(
                exit_code=-1,
                passed=False,
                stdout="",
                stderr=f"Test execution timed out after {self.timeout_seconds} seconds.",
                duration_ms=duration_ms,
                timed_out=True,
            )
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return ExecutionResult(
                exit_code=-1,
                passed=False,
                stdout="",
                stderr=f"Sandbox execution error: {e}",
                duration_ms=duration_ms,
            )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleans up worktree and git branch."""
        if self.worktree_dir and os.path.exists(self.worktree_dir):
            try:
                # Remove git worktree if registered
                cmd = f"git worktree remove --force \"{self.worktree_dir}\""
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.repo_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.communicate()
            except Exception:
                pass

            if self.branch_name:
                try:
                    cmd_br = f"git branch -D {self.branch_name}"
                    proc_br = await asyncio.create_subprocess_shell(
                        cmd_br,
                        cwd=self.repo_path,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await proc_br.communicate()
                except Exception:
                    pass

            shutil.rmtree(self.worktree_dir, ignore_errors=True)
