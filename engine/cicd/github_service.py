"""GitHub API Client Service.
Manages GitHub Checks API runs, commit status updates, in-place PR comments, and rate-limit tracking.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
import httpx
from engine.cicd.github_credentials import GitHubCredentialProvider, PATCredentialProvider

logger = logging.getLogger("astra.github_service")


class GitHubService:
    """Interacts with GitHub REST API v3 and Checks API."""

    def __init__(self, credential_provider: Optional[GitHubCredentialProvider] = None, token: Optional[str] = None):
        if credential_provider:
            self.cred_provider = credential_provider
        elif token:
            self.cred_provider = PATCredentialProvider(token)
        else:
            self.cred_provider = PATCredentialProvider("mock_token")

        self.base_url = "https://api.github.com"

    def _get_headers(self) -> Dict[str, str]:
        return self.cred_provider.get_auth_headers()

    async def create_check_run(
        self,
        repo_full_name: str,
        commit_sha: str,
        name: str = "ASTRA Quality Gate",
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Creates a GitHub Check Run on a commit."""
        url = f"{self.base_url}/repos/{repo_full_name}/check-runs"
        payload = {
            "name": name,
            "head_sha": commit_sha,
            "status": "in_progress",
            "started_at": httpx.USE_CLIENT_DEFAULT,
            "output": details or {
                "title": "ASTRA Selective Regression Pipeline",
                "summary": "ASTRA AST Reachability & Dynamic Risk Prioritization is analyzing commit changes.",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self._get_headers(), json=payload)
                self._track_rate_limit(resp.headers)

                if resp.status_code in [200, 201]:
                    data = resp.json()
                    return str(data.get("id"))
                logger.warning(f"Failed to create check run: {resp.status_code} {resp.text}")
        except Exception as exc:
            logger.error(f"Error creating GitHub check run: {exc}")

        return None

    async def update_check_run(
        self,
        repo_full_name: str,
        check_run_id: str,
        status: str = "completed",
        conclusion: str = "success",
        output: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Updates an existing GitHub Check Run status and conclusion."""
        url = f"{self.base_url}/repos/{repo_full_name}/check-runs/{check_run_id}"
        payload = {
            "status": status,
            "conclusion": conclusion,
            "output": output or {},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.patch(url, headers=self._get_headers(), json=payload)
                self._track_rate_limit(resp.headers)
                return resp.status_code in [200, 201]
        except Exception as exc:
            logger.error(f"Error updating GitHub check run: {exc}")
            return False

    async def update_commit_status(
        self,
        repo_full_name: str,
        commit_sha: str,
        state: str,  # pending, success, failure, error
        description: str,
        target_url: str = "https://astra.dev",
    ) -> bool:
        """Updates legacy GitHub Commit Status for branch protection compatibility."""
        url = f"{self.base_url}/repos/{repo_full_name}/statuses/{commit_sha}"
        payload = {
            "state": state,
            "target_url": target_url,
            "description": description[:140],
            "context": "ASTRA Quality Engine",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self._get_headers(), json=payload)
                self._track_rate_limit(resp.headers)
                return resp.status_code in [200, 201]
        except Exception as exc:
            logger.error(f"Error updating GitHub commit status: {exc}")
            return False

    async def post_or_update_pr_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        comment_markdown: str,
        marker: str = "<!-- ASTRA_REPORT -->",
    ) -> bool:
        """In-place idempotent PR comment updater using HTML marker comment."""
        full_comment_text = f"{marker}\n{comment_markdown}"

        try:
            # 1. Fetch existing PR comments
            comments_url = f"{self.base_url}/repos/{repo_full_name}/issues/{pr_number}/comments"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(comments_url, headers=self._get_headers())
                self._track_rate_limit(resp.headers)

                existing_comment_id = None
                if resp.status_code == 200:
                    comments = resp.json()
                    for c in comments:
                        if marker in c.get("body", ""):
                            existing_comment_id = c.get("id")
                            break

                # 2. Update existing comment or create new comment
                if existing_comment_id:
                    patch_url = f"{self.base_url}/repos/{repo_full_name}/issues/comments/{existing_comment_id}"
                    patch_resp = await client.patch(patch_url, headers=self._get_headers(), json={"body": full_comment_text})
                    return patch_resp.status_code in [200, 201]
                else:
                    post_resp = await client.post(comments_url, headers=self._get_headers(), json={"body": full_comment_text})
                    return post_resp.status_code in [200, 201]
        except Exception as exc:
            logger.error(f"Error posting/updating PR comment: {exc}")
            return False

    def _track_rate_limit(self, headers: httpx.Headers):
        remaining = headers.get("X-RateLimit-Remaining")
        if remaining and int(remaining) < 5:
            logger.warning(f"GitHub API Rate Limit critical: {remaining} remaining.")
