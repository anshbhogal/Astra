"""Git fixture setup helper for Phase 8 selective regression evaluation."""

import os
import subprocess
from pathlib import Path
from typing import Optional


def init_git_benchmark_fixture(target_dir: Optional[Path] = None) -> Path:
    """Initializes a real git repository with 4 commits demonstrating AST and reachability diffs."""
    if target_dir is None:
        target_dir = Path(__file__).parent / "repo"

    target_dir.mkdir(parents=True, exist_ok=True)

    def run_cmd(cmd: str):
        subprocess.run(cmd, shell=True, cwd=str(target_dir), check=True, capture_output=True, text=True)

    # Initialize git repo if not already a git repo
    if not (target_dir / ".git").exists():
        run_cmd("git init")
        run_cmd('git config user.name "Astra Benchmark"')
        run_cmd('git config user.email "benchmark@astra.local"')

        # Commit 0: Base clean code
        (target_dir / "validator.py").write_text("""
def validate_token(token: str) -> bool:
    return len(token) > 10

def helper_auth():
    return True
""", encoding="utf-8")

        (target_dir / "currency.py").write_text("""
def convert_usd_to_eur(amount: float) -> float:
    return amount * 0.92
""", encoding="utf-8")

        (target_dir / "README.md").write_text("# Benchmark Microservice\nVersion 1.0.0", encoding="utf-8")

        run_cmd("git add .")
        run_cmd('git commit -m "Commit 0: Initial clean benchmark microservice"')

        # Commit 1: Modify validator function signature & body
        (target_dir / "validator.py").write_text("""
def validate_token(token: str, strict: bool = True) -> bool:
    if strict:
        return len(token) > 16
    return len(token) > 10

def helper_auth():
    return True
""", encoding="utf-8")
        run_cmd("git add validator.py")
        run_cmd('git commit -m "Commit 1: Modify validate_token signature and body"')

        # Commit 2: Modify shared utility currency.py
        (target_dir / "currency.py").write_text("""
def convert_usd_to_eur(amount: float) -> float:
    # Update conversion rate
    return amount * 0.95
""", encoding="utf-8")
        run_cmd("git add currency.py")
        run_cmd('git commit -m "Commit 2: Modify shared currency utility"')

        # Commit 3: Documentation only update
        (target_dir / "README.md").write_text("# Benchmark Microservice\nVersion 1.0.1 - Updated documentation notes", encoding="utf-8")
        run_cmd("git add README.md")
        run_cmd('git commit -m "Commit 3: Documentation update only"')

    return target_dir
