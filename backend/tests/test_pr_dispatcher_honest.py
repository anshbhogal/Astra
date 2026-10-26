"""
Tests for Task P2-4: Honest Git Commits & Non-Simulated Pull Requests.
Verifies removal of fabricated 'c0ffee' commit SHAs and fake PR calculations.
"""

import os
import subprocess
import tempfile
import pytest
from unittest.mock import AsyncMock, patch
from engine.repair.pr_dispatcher import AutonomousPRDispatcher, PullRequestDispatchResult, create_git_commit
from engine.repair.regression_gate import CandidateVerificationReport


@pytest.fixture
def temp_git_repo():
    """Creates a temporary local git repository for realistic git testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmpdir, check=True, capture_output=True)

        # Create an initial file and commit
        sample_file = os.path.join(tmpdir, "service.py")
        with open(sample_file, "w") as f:
            f.write("def calculate(x):\n    return x * 2\n")

        subprocess.run(["git", "add", "service.py"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmpdir, check=True, capture_output=True)

        yield tmpdir


def test_create_git_commit_produces_real_sha(temp_git_repo):
    """Verifies that create_git_commit generates an authentic 40-character Git SHA."""
    target_file = "service.py"
    patch_diff = (
        "--- a/service.py\n"
        "+++ b/service.py\n"
        "@@ -1,2 +1,4 @@\n"
        " def calculate(x):\n"
        "+    if x is None:\n"
        "+        return 0\n"
        "     return x * 2\n"
    )

    commit_sha = create_git_commit(
        repo_path=temp_git_repo,
        branch_name="astra/fix-def-001-test",
        target_file=target_file,
        patch_diff=patch_diff,
        commit_message="fix(calc): handle None input [ASTRA DEF-001]",
        base_branch="main",
    )

    # Must be authentic 40-char SHA and NOT start with fake 'c0ffee'
    assert len(commit_sha) == 40
    assert not commit_sha.startswith("c0ffee")

    # Verify commit exists in git
    res = subprocess.run(
        ["git", "rev-parse", "astra/fix-def-001-test"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert res.stdout.strip() == commit_sha


def test_create_git_commit_fallback_produces_honest_hash():
    """Verifies that when repo_path is not a git repo, an authentic SHA is derived without c0ffee."""
    commit_sha = create_git_commit(
        repo_path=None,
        branch_name="astra/fix-def-002",
        target_file="app/calc.py",
        patch_diff="--- a/calc.py\n+++ b/calc.py\n@@ -1 +1 @@\n-a\n+b\n",
        commit_message="test message",
    )
    assert len(commit_sha) == 40
    assert not commit_sha.startswith("c0ffee")


@pytest.mark.asyncio
async def test_dispatch_pr_offline_returns_none_for_pr_without_fabrication(temp_git_repo):
    """Verifies offline/local mode returns None for PR number and URL rather than faking them."""
    dispatcher = AutonomousPRDispatcher(github_token=None, github_repo=None)

    report = CandidateVerificationReport(
        candidate_hash="abc123def456",
        plausible=True,
        defect_test_duration_ms=10.0,
        static_analysis_passed=True,
        regression_passed=True,
        regressions_count=0,
        regression_tests_total=5,
        regression_tests_passed=5,
        regression_tests_failed=0,
        regression_tests_error=0,
        regression_tests_timeout=0,
        complexity_delta=1,
        ranking_score=0.95,
        verified=True,
    )

    result = await dispatcher.dispatch_pr(
        defect_key="DEF-101",
        title="Fix division by zero",
        target_file="service.py",
        target_line=2,
        diff_text="--- a/service.py\n+++ b/service.py\n@@ -1 +1 @@\n",
        rationale="Guard division",
        report=report,
        repo_path=temp_git_repo,
    )

    assert result.pr_number is None
    assert result.pr_url is None
    assert not result.commit_sha.startswith("c0ffee")
    assert len(result.commit_sha) == 40
    assert "GitHub token" in (result.error_message or "")


@pytest.mark.asyncio
async def test_dispatch_pr_online_uses_real_github_api_response(temp_git_repo):
    """Verifies live GitHub mode uses exact PR number and URL returned by GitHub API."""
    dispatcher = AutonomousPRDispatcher(
        github_token="ghp_mocktoken1234567890abcdef",
        github_repo="astra-ai/astra-test-repo",
    )

    report = CandidateVerificationReport(
        candidate_hash="feedbeef123456",
        plausible=True,
        defect_test_duration_ms=12.0,
        static_analysis_passed=True,
        regression_passed=True,
        regressions_count=0,
        regression_tests_total=10,
        regression_tests_passed=10,
        regression_tests_failed=0,
        regression_tests_error=0,
        regression_tests_timeout=0,
        complexity_delta=2,
        ranking_score=0.98,
        verified=True,
    )

    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "number": 789,
        "html_url": "https://github.com/astra-ai/astra-test-repo/pull/789",
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp), \
         patch("subprocess.run") as mock_sub:
        mock_sub.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="fake_sha\n")

        result = await dispatcher.dispatch_pr(
            defect_key="DEF-202",
            title="Real GitHub PR",
            target_file="service.py",
            target_line=5,
            diff_text="--- a\n+++ b\n",
            rationale="Fix defect",
            report=report,
            repo_path=temp_git_repo,
        )

        assert result.success is True
        assert result.pr_number == 789
        assert result.pr_url == "https://github.com/astra-ai/astra-test-repo/pull/789"
