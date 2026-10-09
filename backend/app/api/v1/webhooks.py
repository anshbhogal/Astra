"""Public Webhook Gateway Router for GitHub & CI/CD Events."""

import json
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.domain import Project, WebhookEventModel
from engine.cicd.hmac_validator import HMACValidator
from engine.cicd.event_abstraction import GitHubEventAdapter
from engine.analysis.redactor import EvidenceRedactor

router = APIRouter()


def _redact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        raw_str = json.dumps(payload)
        redacted_str = EvidenceRedactor.redact_text(raw_str)
        return json.loads(redacted_str)
    except Exception:
        return {"summary": "payload_redaction_failed"}


@router.post("/webhooks/github", status_code=status.HTTP_202_ACCEPTED)
async def handle_github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
):
    """Secure public webhook gateway receiving GitHub push, pull_request, and check_run events."""
    raw_body = await request.body()
    secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", "astra_webhook_secret_key_2026")

    # 1. HMAC Signature Verification BEFORE JSON Parsing
    if not HMACValidator.verify_github_signature(raw_body, x_hub_signature_256, secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Hub-Signature-256 header signature.",
        )

    # 2. JSON Payload Decoding
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload format.",
        )

    delivery_id = x_github_delivery or str(uuid.uuid4())
    event_type = x_github_event or payload.get("action") or "unknown"

    # 3. Idempotency Check: Check if delivery_id exists
    existing_stmt = select(WebhookEventModel).where(
        WebhookEventModel.provider == "GITHUB",
        WebhookEventModel.delivery_id == delivery_id,
    )
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        return {
            "status": "DUPLICATE_IGNORED",
            "message": f"Webhook delivery '{delivery_id}' has already been processed.",
            "delivery_id": delivery_id,
        }

    # 4. Map external repository to ASTRA Project
    repo_info = payload.get("repository", {})
    repo_full_name = repo_info.get("full_name", "")
    clone_url = repo_info.get("clone_url", "")
    sender = payload.get("sender", {}).get("login", "github_webhook")

    project_stmt = select(Project).where(
        (Project.repository_url.ilike(f"%{repo_full_name}%")) |
        (Project.repository_url == clone_url)
    )
    proj_res = await db.execute(project_stmt)
    project = proj_res.scalars().first()

    redacted_payload = _redact_payload(payload)

    # 5. Persist WebhookEventModel Record
    event_record = WebhookEventModel(
        project_id=project.id if project else None,
        provider="GITHUB",
        delivery_id=delivery_id,
        event_type=event_type,
        signature_verified=True,
        sender=sender,
        payload_redacted=redacted_payload,
        processing_status="PROCESSED" if project else "IGNORED_UNMAPPED_REPO",
    )
    db.add(event_record)
    await db.commit()

    if not project:
        return {
            "status": "ACCEPTED",
            "message": f"Webhook received, but no ASTRA project matched repository '{repo_full_name}'.",
            "delivery_id": delivery_id,
        }

    # 6. Dispatch Celery Task Asynchronously
    try:
        from app.tasks.cicd_tasks import process_github_webhook_task
        task = process_github_webhook_task.delay(str(event_record.id))
        task_id = task.id
    except Exception:
        task_id = None

    return {
        "status": "ACCEPTED",
        "message": "Webhook payload verified and queued for processing.",
        "delivery_id": delivery_id,
        "event_id": str(event_record.id),
        "project_id": str(project.id),
        "task_id": task_id,
    }
