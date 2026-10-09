import pytest
from engine.cicd.event_abstraction import GitHubEventAdapter


def test_github_event_adapter_pull_request():
    payload = {
        "action": "opened",
        "number": 15,
        "repository": {
            "full_name": "owner/sample-repo",
            "clone_url": "https://github.com/owner/sample-repo.git",
        },
        "pull_request": {
            "head": {"sha": "target_sha_123", "ref": "feature-branch"},
            "base": {"sha": "base_sha_000", "ref": "main"},
        },
        "sender": {"login": "dev_user"},
    }
    headers = {
        "x-github-event": "pull_request",
        "x-github-delivery": "deliv-999",
    }

    event = GitHubEventAdapter.adapt(payload, headers)
    assert event is not None
    assert event.provider == "GITHUB"
    assert event.event_type == "PULL_REQUEST"
    assert event.repository_full_name == "owner/sample-repo"
    assert event.target_sha == "target_sha_123"
    assert event.pr_number == 15
    assert event.delivery_id == "deliv-999"
