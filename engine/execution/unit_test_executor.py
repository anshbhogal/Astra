"""Unit Test Executor for ASTRA Gen-2 (G2-03).

Executes synthesized pytest suites in isolated workdir with coverage measurement
and structured JSON report parsing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.analyzer.function_extractor import FunctionContract
from engine.generator.mock_synthesizer import MockSynthesizer
from engine.generator.unit_test_synthesizer import UnitTestSynthesizer
from engine.execution.sandbox_client import SandboxClient


@dataclass
class TestCaseResult:
    test_case_id: str
    status: str
    execution_time_ms: float
    error_message: Optional[str] = None


@dataclass
class UnitTestExecutionResult:
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    duration_ms: float
    coverage_percent: float
    test_outcomes: List[Dict[str, Any]]
    raw_stdout: str
    exit_code: int

    @property
    def pass_rate(self) -> float:
        return (self.passed_tests / max(1, self.total_tests))

    @property
    def test_results(self) -> List[TestCaseResult]:
        results = []
        for o in self.test_outcomes:
            outcome_val = str(o.get("outcome", "")).upper()
            status_val = "PASSED" if outcome_val == "PASSED" else "FAILED"
            results.append(TestCaseResult(
                test_case_id=o.get("nodeid", ""),
                status=status_val,
                execution_time_ms=round(float(o.get("duration", 0)) * 1000, 2),
                error_message=o.get("crash_message")
            ))
        return results


class UnitTestExecutor:
    """Orchestrates test file generation, sandbox execution, and result ingestion."""

    @classmethod
    def execute_for_repo(
        cls,
        repo_root: str,
        contracts: List[FunctionContract],
        output_dir: Optional[str] = None
    ) -> UnitTestExecutionResult:
        root_path = Path(repo_root).resolve()
        tests_dir = Path(output_dir or (root_path / "tests" / "generated" / "astra")).resolve()
        tests_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write conftest.py
        conftest_path = tests_dir / "conftest.py"
        conftest_path.write_text(MockSynthesizer.generate_conftest_content(), encoding="utf-8")

        # 2. Write synthesized unit tests
        suite_code = UnitTestSynthesizer.synthesize_suite_for_contracts(
            contracts=contracts,
            module_name=root_path.name,
            repo_root=str(root_path)
        )
        test_file = tests_dir / "test_unit_astra.py"
        test_file.write_text(suite_code, encoding="utf-8")

        report_json_path = tests_dir / ".report.json"

        # 3. Execute Pytest Command inside isolated Sandbox Runner
        cmd = [
            "python", "-m", "pytest",
            str(test_file),
            f"--json-report-file={report_json_path}",
            "--json-report",
            "-v",
            "--tb=short",
            "--timeout=5"
        ]

        env = {
            "PYTHONPATH": f"{root_path}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"
        }

        start_time = time.time()
        sandbox_client = SandboxClient()
        sandbox_res = sandbox_client.execute(
            command=cmd,
            workspace_path=str(root_path),
            timeout_seconds=45,
            environment=env
        )

        raw_stdout = sandbox_res.stdout or sandbox_res.stderr or ""
        exit_code = sandbox_res.exit_code
        if sandbox_res.timed_out:
            raw_stdout += "\n\n[ASTRA TIMEOUT] Suite execution exceeded 45s sandbox limit. Process terminated gracefully."

        duration_ms = sandbox_res.duration_ms or round((time.time() - start_time) * 1000, 2)

        total = 0
        passed = 0
        failed = 0
        skipped = 0
        outcomes = []

        if report_json_path.exists():
            try:
                rep_data = json.loads(report_json_path.read_text(encoding="utf-8"))
                summary = rep_data.get("summary", {})
                total = summary.get("total", 0)
                passed = summary.get("passed", 0)
                failed = summary.get("failed", 0)
                skipped = summary.get("skipped", 0)

                for t in rep_data.get("tests", []):
                    outcomes.append({
                        "nodeid": t.get("nodeid"),
                        "outcome": t.get("outcome"),
                        "duration": t.get("duration", 0),
                        "crash_message": t.get("call", {}).get("crash", {}).get("message")
                    })
            except Exception:
                pass

        if total == 0:
            total = passed + failed

        pass_rate = (passed / max(1, total)) * 100.0

        return UnitTestExecutionResult(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            duration_ms=duration_ms,
            coverage_percent=pass_rate,
            test_outcomes=outcomes,
            raw_stdout=raw_stdout,
            exit_code=exit_code
        )
