"""Provider-Neutral CI Pipeline Event Abstraction & Adapters.
Normalizes GitHub, GitLab, Bitbucket, and CLI webhook payloads into a unified CIPipelineEvent format.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class CIPipelineEvent:
    provider: str  # GITHUB, GITLAB, BITBUCKET, MANUAL_CLI
    event_type: str  # PULL_REQUEST, PUSH, CHECK_RUN
    repository_full_name: str
    clone_url: str
    base_sha: str
    target_sha: str
    branch: Optional[str]
    pr_number: Optional[int]
    sender: str
    delivery_id: str
    raw_payload: Dict[str, Any] = field(default_factory=dict)


class GitHubEventAdapter:
    """Adapts raw GitHub webhook headers and JSON payload into a CIPipelineEvent."""

    @staticmethod
    def adapt(payload: Dict[str, Any], headers: Dict[str, str]) -> Optional[CIPipelineEvent]:
        event_name = headers.get("x-github-event") or headers.get("X-GitHub-Event") or "unknown"
        delivery_id = headers.get("x-github-delivery") or headers.get("X-GitHub-Delivery") or "unknown_delivery"

        repo_info = payload.get("repository", {})
        repo_full_name = repo_info.get("full_name", "unknown/repository")
        clone_url = repo_info.get("clone_url") or f"https://github.com/{repo_full_name}.git"
        sender_info = payload.get("sender", {})
        sender = sender_info.get("login", "unknown_user")

        if event_name == "pull_request":
            pr = payload.get("pull_request", {})
            head = pr.get("head", {})
            base = pr.get("base", {})

            return CIPipelineEvent(
                provider="GITHUB",
                event_type="PULL_REQUEST",
                repository_full_name=repo_full_name,
                clone_url=clone_url,
                base_sha=base.get("sha", "HEAD~1"),
                target_sha=head.get("sha", "HEAD"),
                branch=head.get("ref") or base.get("ref"),
                pr_number=payload.get("number"),
                sender=sender,
                delivery_id=delivery_id,
                raw_payload=payload,
            )

        elif event_name == "push":
            ref = payload.get("ref", "")
            branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

            return CIPipelineEvent(
                provider="GITHUB",
                event_type="PUSH",
                repository_full_name=repo_full_name,
                clone_url=clone_url,
                base_sha=payload.get("before", "HEAD~1"),
                target_sha=payload.get("after", "HEAD"),
                branch=branch,
                pr_number=None,
                sender=sender,
                delivery_id=delivery_id,
                raw_payload=payload,
            )

        elif event_name == "check_run":
            check_run = payload.get("check_run", {})

            return CIPipelineEvent(
                provider="GITHUB",
                event_type="CHECK_RUN",
                repository_full_name=repo_full_name,
                clone_url=clone_url,
                base_sha="HEAD~1",
                target_sha=check_run.get("head_sha", "HEAD"),
                branch=None,
                pr_number=None,
                sender=sender,
                delivery_id=delivery_id,
                raw_payload=payload,
            )

        return None
