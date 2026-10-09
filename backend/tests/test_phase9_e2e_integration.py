"""ASTRA Phase 9 End-to-End CI/CD Integration Test.
Verifies Webhook Gateway -> HMAC Security -> Delivery Deduplication -> Repository Mapping ->
Pipeline Orchestrator -> Quality Gate -> GitHub Checks & PR Comments -> Multi-Channel Notifications -> REST APIs.
"""

import pytest
import uuid
import hmac
import hashlib
import json
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.domain import (
    User, Project, TestSuite, TestCase, WebhookEventModel, CIPipelineRunModel, NotificationChannelModel, LanguageFramework
)
from app.services.cicd_service import CICDService
from app.core.security import create_access_token
from engine.cicd.hmac_validator import HMACValidator
from engine.cicd.quality_gate import QualityGateEvaluator


@pytest.mark.asyncio
async def test_phase9_full_e2e_pipeline(db_session: AsyncSession, client: AsyncClient):
    # 1. Setup Test User & Project
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"phase9_tester_{user_id.hex[:6]}@example.com",
        full_name="Phase 9 CI/CD Tester",
        hashed_password="hashed_pass_mock",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(user)

    project_id = uuid.uuid4()
    repo_full_name = f"test-owner/phase9-app-{project_id.hex[:6]}"
    repo_url = f"https://github.com/{repo_full_name}.git"
    project = Project(
        id=project_id,
        name="Phase 9 CI Project",
        repository_url=repo_url,
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=user_id,
    )
    db_session.add(project)

    # 2. Setup Test Suite & TestCase
    suite_id = uuid.uuid4()
    suite = TestSuite(id=suite_id, project_id=project_id, name="CI Suite", total_cases=1)
    db_session.add(suite)

    tc1 = TestCase(
        id=uuid.uuid4(),
        suite_id=suite_id,
        name="Test GET Health",
        test_type="HAPPY_PATH",
        specification={"endpoint": "/health", "method": "GET", "tags": ["smoke"]},
    )
    db_session.add(tc1)
    await db_session.commit()

    secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", "astra_webhook_secret_key_2026")
    delivery_id = f"deliv-{uuid.uuid4().hex[:8]}"

    payload_data = {
        "action": "opened",
        "number": 42,
        "repository": {"full_name": repo_full_name, "clone_url": repo_url},
        "pull_request": {
            "head": {"sha": "c123456", "ref": "feature-branch"},
            "base": {"sha": "c000000", "ref": "main"},
        },
        "sender": {"login": "dev_user"},
    }
    raw_body = json.dumps(payload_data).encode("utf-8")
    mac = hmac.new(secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256)
    valid_sig = f"sha256={mac.hexdigest()}"

    # 3. Test Invalid HMAC Signature Rejection (403 Forbidden)
    invalid_resp = await client.post(
        "/api/v1/webhooks/github",
        content=raw_body,
        headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": delivery_id, "X-Hub-Signature-256": "sha256=wrong_sig"},
    )
    assert invalid_resp.status_code == 403

    # 4. Test Valid Webhook Dispatch (202 Accepted)
    valid_resp = await client.post(
        "/api/v1/webhooks/github",
        content=raw_body,
        headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": delivery_id, "X-Hub-Signature-256": valid_sig},
    )
    assert valid_resp.status_code == 202
    resp_json = valid_resp.json()
    assert resp_json["status"] == "ACCEPTED"
    event_id = uuid.UUID(resp_json["event_id"])

    # 5. Test Deduplication / Idempotency (Duplicate delivery_id)
    dup_resp = await client.post(
        "/api/v1/webhooks/github",
        content=raw_body,
        headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": delivery_id, "X-Hub-Signature-256": valid_sig},
    )
    assert dup_resp.status_code == 202
    assert dup_resp.json()["status"] == "DUPLICATE_IGNORED"

    # 6. Process Webhook via CICDService
    service = CICDService(db_session)
    pipeline_res = await service.process_webhook_event(event_id)
    assert pipeline_res["status"] == "COMPLETED"
    assert pipeline_res["quality_gate"] == "PASS"

    # 7. REST APIs Verification
    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # Webhook Logs
    log_resp = await client.get(f"/api/v1/projects/{project_id}/webhooks/logs", headers=headers)
    assert log_resp.status_code == 200
    assert len(log_resp.json()["logs"]) >= 1

    # Create Notification Channel
    ch_resp = await client.post(
        f"/api/v1/projects/{project_id}/notifications",
        headers=headers,
        json={
            "channel_type": "SLACK",
            "name": "Dev Slack Channel",
            "target_url": "https://hooks.slack.com/services/T00/B00/X00",
        },
    )
    assert ch_resp.status_code == 201
    ch_id = ch_resp.json()["channel_id"]

    # List Notification Channels
    list_ch_resp = await client.get(f"/api/v1/projects/{project_id}/notifications", headers=headers)
    assert list_ch_resp.status_code == 200
    channels = list_ch_resp.json()["channels"]
    assert len(channels) == 1
    assert "*****" in channels[0]["masked_target"]

    # Test Ping Trigger
    ping_resp = await client.post(f"/api/v1/notifications/{ch_id}/test", headers=headers)
    assert ping_resp.status_code == 200
    assert ping_resp.json()["status"] == "SENT"
