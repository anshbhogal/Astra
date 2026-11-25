"""Security tests for Phase P0: Automated Program Repair (APR) PR-Merged Webhook HMAC & Idempotency Validation."""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.domain import User, UserRole, Project, LanguageFramework
from app.models.canonical import G2Defect, G2RepairJob, G2RepairCandidate, G2RepairPullRequest, G2DefectHistory
from app.core.security import get_password_hash


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _compute_signature(payload_bytes: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256).hexdigest()


async def _seed_repair_pr_fixture(db_session: AsyncSession, pr_number: int = 9001):
    """Seed project, defect, and repair PR record for closed-loop verification."""
    # 1. Admin & Project
    admin = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@astra.local",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_approved=True,
    )
    db_session.add(admin)
    await db_session.flush()

    project = Project(
        name=f"Project Webhook {uuid.uuid4().hex[:6]}",
        repository_url="https://github.com/example/webhook-repo",
        default_branch="main",
        language_framework=LanguageFramework.PYTHON_FASTAPI,
        owner_id=admin.id
    )
    db_session.add(project)
    await db_session.flush()

    # 2. Defect
    defect = G2Defect(
        id=uuid.uuid4(),
        project_id=project.id,
        defect_key=f"DEF-{uuid.uuid4().hex[:4].upper()}",
        title="Null pointer exception in auth service",
        description="Location: app/service.py",
        severity="HIGH",
        status="PR_OPEN",
        source="AUTOMATED_TEST",
        created_at=utc_now()
    )
    db_session.add(defect)
    await db_session.flush()

    # 3. Repair Job
    repair_job = G2RepairJob(
        id=uuid.uuid4(),
        defect_id=defect.id,
        project_id=project.id,
        source_commit_sha="a" * 40,
        base_branch="main",
        status="COMPLETED",
        engine_version="v2.0.0",
        config_hash="b" * 64,
        request_hash="c" * 64,
        created_at=utc_now()
    )
    db_session.add(repair_job)
    await db_session.flush()

    # 4. Repair Candidate
    candidate = G2RepairCandidate(
        id=uuid.uuid4(),
        repair_job_id=repair_job.id,
        defect_id=defect.id,
        candidate_rank=1,
        generation_method="DETERMINISTIC_MUTATION",
        mutator_type="NULL_SAFETY_GUARD",
        base_commit_sha="a" * 40,
        target_file="app/service.py",
        target_ast_hash="d" * 64,
        target_node_type="FunctionDef",
        patch_diff="+if x is not None: pass",
        patch_sha256="e" * 64,
        candidate_hash="f" * 64,
        status="VALIDATED",
        created_at=utc_now()
    )
    db_session.add(candidate)
    await db_session.flush()

    # 5. Repair Pull Request record
    repair_pr = G2RepairPullRequest(
        id=uuid.uuid4(),
        repair_job_id=repair_job.id,
        repair_candidate_id=candidate.id,
        defect_id=defect.id,
        github_pr_number=pr_number,
        github_pr_url=f"https://github.com/example/webhook-repo/pull/{pr_number}",
        branch_name=f"astra/repair-pr-{pr_number}",
        base_branch="main",
        commit_sha="1" * 40,
        pr_status="OPEN",
        post_merge_verified=False,
        created_at=utc_now()
    )
    db_session.add(repair_pr)
    await db_session.commit()
    await db_session.refresh(defect)
    await db_session.refresh(repair_pr)
    return project, defect, repair_pr


@pytest.mark.asyncio
async def test_repair_webhook_missing_signature_rejected(client: AsyncClient):
    """Webhook call with missing X-Hub-Signature-256 header must be rejected with 403 Forbidden."""
    payload = {"pull_request": {"number": 9001, "merged": True}}
    resp = await client.post(
        "/api/v1/repair/webhooks/github/pr-merged",
        json=payload
    )
    assert resp.status_code == 403, f"Expected 403 Forbidden for missing signature, got {resp.status_code}"
    assert "Invalid or missing X-Hub-Signature-256" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_repair_webhook_invalid_signature_rejected(client: AsyncClient):
    """Webhook call with forged or invalid signature header must be rejected with 403 Forbidden."""
    payload = {"pull_request": {"number": 9001, "merged": True}}
    raw_body = json.dumps(payload).encode("utf-8")
    headers = {
        "X-Hub-Signature-256": "sha256=" + "0" * 64,
        "Content-Type": "application/json"
    }
    resp = await client.post(
        "/api/v1/repair/webhooks/github/pr-merged",
        content=raw_body,
        headers=headers
    )
    assert resp.status_code == 403, f"Expected 403 Forbidden for invalid signature, got {resp.status_code}"
    assert "Invalid or missing X-Hub-Signature-256" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_repair_webhook_tampered_payload_rejected(client: AsyncClient):
    """Webhook call where payload was tampered in transit must be rejected with 403 Forbidden."""
    original_payload = {"pull_request": {"number": 9001, "merged": True}}
    original_bytes = json.dumps(original_payload).encode("utf-8")
    valid_signature_for_original = _compute_signature(original_bytes, settings.GITHUB_WEBHOOK_SECRET)

    # Attacker alters the payload to a different PR number but sends original signature
    tampered_payload = {"pull_request": {"number": 9999, "merged": True}}
    tampered_bytes = json.dumps(tampered_payload).encode("utf-8")

    headers = {
        "X-Hub-Signature-256": valid_signature_for_original,
        "Content-Type": "application/json"
    }
    resp = await client.post(
        "/api/v1/repair/webhooks/github/pr-merged",
        content=tampered_bytes,
        headers=headers
    )
    assert resp.status_code == 403, f"Expected 403 for tampered payload, got {resp.status_code}"


@pytest.mark.asyncio
async def test_repair_webhook_malformed_json_rejected(client: AsyncClient):
    """Webhook call with valid HMAC signature but malformed JSON must return 400 Bad Request."""
    malformed_bytes = b"NOT_A_VALID_JSON{foo:bar"
    valid_sig = _compute_signature(malformed_bytes, settings.GITHUB_WEBHOOK_SECRET)

    headers = {
        "X-Hub-Signature-256": valid_sig,
        "Content-Type": "application/json"
    }
    resp = await client.post(
        "/api/v1/repair/webhooks/github/pr-merged",
        content=malformed_bytes,
        headers=headers
    )
    assert resp.status_code == 400, f"Expected 400 for malformed JSON, got {resp.status_code}"
    assert "Invalid JSON payload format" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_repair_webhook_missing_pr_number_rejected(client: AsyncClient):
    """Webhook call with valid HMAC signature but missing pull_request.number must return 400 Bad Request."""
    empty_payload = {"some_other_field": "test"}
    raw_body = json.dumps(empty_payload).encode("utf-8")
    valid_sig = _compute_signature(raw_body, settings.GITHUB_WEBHOOK_SECRET)

    headers = {
        "X-Hub-Signature-256": valid_sig,
        "Content-Type": "application/json"
    }
    resp = await client.post(
        "/api/v1/repair/webhooks/github/pr-merged",
        content=raw_body,
        headers=headers
    )
    assert resp.status_code == 400, f"Expected 400 for missing pr_number, got {resp.status_code}"
    assert "Payload missing pull_request.number" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_repair_webhook_valid_signature_processes_and_closes_defect(
    client: AsyncClient, db_session: AsyncSession
):
    """Valid signed webhook transitions repair PR to MERGED and defect to CLOSED."""
    pr_num = 7711
    project, defect, repair_pr = await _seed_repair_pr_fixture(db_session, pr_number=pr_num)

    payload = {
        "action": "closed",
        "pull_request": {
            "number": pr_num,
            "merged": True
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = _compute_signature(raw_body, settings.GITHUB_WEBHOOK_SECRET)

    headers = {
        "X-Hub-Signature-256": sig,
        "Content-Type": "application/json"
    }
    resp = await client.post(
        "/api/v1/repair/webhooks/github/pr-merged",
        content=raw_body,
        headers=headers
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "verified_and_closed"
    assert data["pr_number"] == pr_num

    # Verify database state
    db_pr = (await db_session.execute(
        select(G2RepairPullRequest).where(G2RepairPullRequest.id == repair_pr.id)
    )).scalar_one()
    assert db_pr.pr_status == "MERGED"
    assert db_pr.post_merge_verified is True

    db_defect = (await db_session.execute(
        select(G2Defect).where(G2Defect.id == defect.id)
    )).scalar_one()
    assert db_defect.status == "CLOSED"

    # Verify history entry created
    history_entries = (await db_session.execute(
        select(G2DefectHistory).where(G2DefectHistory.defect_id == defect.id)
    )).scalars().all()
    assert any(h.to_status == "CLOSED" and "PR #7711" in h.comment for h in history_entries)


@pytest.mark.asyncio
async def test_repair_webhook_replay_handling_idempotent(
    client: AsyncClient, db_session: AsyncSession
):
    """Replaying an already-merged webhook must return DUPLICATE_IGNORED and create zero duplicate history records."""
    pr_num = 8822
    project, defect, repair_pr = await _seed_repair_pr_fixture(db_session, pr_number=pr_num)

    payload = {"pull_request": {"number": pr_num, "merged": True}}
    raw_body = json.dumps(payload).encode("utf-8")
    sig = _compute_signature(raw_body, settings.GITHUB_WEBHOOK_SECRET)
    headers = {"X-Hub-Signature-256": sig, "Content-Type": "application/json"}

    # First delivery: processes successfully
    resp1 = await client.post("/api/v1/repair/webhooks/github/pr-merged", content=raw_body, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "verified_and_closed"

    # Second delivery (replay attack or network duplicate)
    resp2 = await client.post("/api/v1/repair/webhooks/github/pr-merged", content=raw_body, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "DUPLICATE_IGNORED"
    assert "already been verified" in data2["message"]

    # Verify history records count has not doubled
    history_entries = (await db_session.execute(
        select(G2DefectHistory).where(G2DefectHistory.defect_id == defect.id)
    )).scalars().all()
    closed_entries = [h for h in history_entries if h.to_status == "CLOSED"]
    assert len(closed_entries) == 1, f"Expected exactly 1 CLOSED history entry, found {len(closed_entries)}"
