"""Security tests for Phase 0 Task P0-5: Webhook HMAC Secret and Validation."""

import hashlib
import hmac
import json
import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_webhook_old_default_secret_rejected(client: AsyncClient):
    """A webhook signed with the old hardcoded default secret must be rejected with 403 Forbidden."""
    payload = {
        "action": "push",
        "repository": {"full_name": "example/test-repo", "clone_url": "https://github.com/example/test-repo.git"}
    }
    raw_body = json.dumps(payload).encode("utf-8")

    # Old vulnerable default secret from audit
    old_secret = "astra_webhook_secret_key_2026"
    old_signature = "sha256=" + hmac.new(old_secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256).hexdigest()

    headers = {
        "X-GitHub-Event": "push",
        "X-GitHub-Delivery": "test-delivery-old-secret",
        "X-Hub-Signature-256": old_signature,
        "Content-Type": "application/json"
    }

    resp = await client.post("/api/v1/webhooks/github", content=raw_body, headers=headers)
    assert resp.status_code == 403, (
        f"Expected 403 Forbidden for webhook signed with old default secret, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_webhook_valid_secret_accepted(client: AsyncClient):
    """A webhook signed with the configured settings.GITHUB_WEBHOOK_SECRET must be accepted with 202."""
    payload = {
        "action": "push",
        "repository": {"full_name": "example/test-repo", "clone_url": "https://github.com/example/test-repo.git"}
    }
    raw_body = json.dumps(payload).encode("utf-8")

    current_secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", None)
    assert current_secret is not None and current_secret != "astra_webhook_secret_key_2026", (
        "GITHUB_WEBHOOK_SECRET must be set and must not equal the old default secret"
    )

    valid_signature = "sha256=" + hmac.new(current_secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256).hexdigest()

    headers = {
        "X-GitHub-Event": "push",
        "X-GitHub-Delivery": "test-delivery-valid-secret",
        "X-Hub-Signature-256": valid_signature,
        "Content-Type": "application/json"
    }

    resp = await client.post("/api/v1/webhooks/github", content=raw_body, headers=headers)
    assert resp.status_code == 202, (
        f"Expected 202 Accepted for valid webhook signature, got {resp.status_code}: {resp.text}"
    )
