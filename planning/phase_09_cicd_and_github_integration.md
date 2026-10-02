# Phase 9 — CI/CD Pipeline & GitHub Integration Implementation Guide

> **Module Focus:** GitHub Webhook Receiver, HMAC Verification, PR Commit Status Checks, Automated PR Commenter, GitHub Actions Custom Action, and Slack Alert Dispatcher.

---

## 1. Phase Overview & Objectives

Phase 9 integrates Astra directly into modern developer workflows. By providing a GitHub Webhook handler, GitHub Actions step, and status check reporter, Astra automatically triggers static analysis and targeted regression tests whenever a developer opens a Pull Request or pushes new code.

### Key Deliverables
1. **GitHub Webhook Listener & Security:** Secure REST endpoint receiving `push` and `pull_request` events verified with HMAC-SHA256 secret signatures.
2. **GitHub PR Status Check API Integration:** Automated status updater sending `pending`, `success`, or `failure` states back to GitHub Commit Statuses.
3. **Automated PR Comment Generator:** Bot engine formatting test results, critical bug alerts, and coverage metrics directly into GitHub PR review comments.
4. **GitHub Actions Custom Action (`astra-action`):** Reusable CI pipeline step configuration allowing developers to execute Astra testing directly inside GitHub workflow YAML files.
5. **Multi-Channel Notification Dispatcher:** Webhook notification manager sending alert cards to Slack, Microsoft Teams, or Email.

---

## 2. Technical Stack Specifications

- **GitHub API Integration:** `PyGithub` `2.2+` or async `httpx` with GitHub App JWT / OAuth tokens.
- **Security:** Built-in `hmac` and `hashlib` for payload signature verification.

---

## 3. Architecture & Webhook Flow

```text
Developer pushes code / opens Pull Request on GitHub
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ GitHub Webhook Dispatch (POST /webhooks/github)│
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│ HMAC Signature Verification (SHA-256)         │
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│ Celery Task: Astra CI Automation Worker       │
│ 1. Set GitHub Status -> PENDING               │
│ 2. Parse Commit Diff & Analyze Impact         │
│ 3. Execute Targeted Regression Suite          │
│ 4. Set GitHub Status -> SUCCESS / FAILURE     │
│ 5. Post Markdown Summary Comment on PR        │
└───────────────────────────────────────────────┘
```

---

## 4. GitHub Webhook Listener Router (`backend/app/api/v1/webhooks.py`)

```python
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
import hmac
import hashlib
import os
from app.core.celery_app import celery_app

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "astra_webhook_secret_key_2026")

def verify_github_signature(payload_body: bytes, signature_header: str):
    if not signature_header:
        raise HTTPException(status_code=403, detail="Missing X-Hub-Signature-256 header")
    sha_name, signature = signature_header.split("=")
    if sha_name != "sha256":
        raise HTTPException(status_code=500, detail="Invalid signature algorithm")
    
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload_body, digestmod=hashlib.sha256)
    if not hmac.compare_digest(mac.hexdigest(), signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

@router.post("/github")
async def handle_github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None)
):
    body = await request.body()
    verify_github_signature(body, x_hub_signature_256)
    
    payload = await request.json()
    
    if x_github_event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize"]:
            pr_number = payload["number"]
            repo_url = payload["repository"]["clone_url"]
            commit_sha = payload["pull_request"]["head"]["sha"]
            
            # Dispatch async Celery worker task to execute Astra CI pipeline
            celery_app.send_task(
                "tasks.process_github_pr",
                args=[repo_url, commit_sha, pr_number]
            )
            return {"status": "queued", "pr_number": pr_number}

    return {"status": "ignored_event", "event": x_github_event}
```

---

## 5. GitHub PR Comment & Status Check Integration (`engine/cicd/github_service.py`)

```python
import httpx
from typing import Dict, Any

class GitHubService:
    def __init__(self, github_token: str):
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def update_commit_status(self, repo_full_name: str, commit_sha: str, state: str, description: str, target_url: str):
        """State options: 'pending', 'success', 'failure', 'error'."""
        url = f"https://api.github.com/repos/{repo_full_name}/statuses/{commit_sha}"
        payload = {
            "state": state,
            "target_url": target_url,
            "description": description,
            "context": "ASTRA Software Quality Engine"
        }
        async with httpx.AsyncClient() as client:
            await client.post(url, headers=self.headers, json=payload)

    async def post_pr_comment(self, repo_full_name: str, pr_number: int, comment_markdown: str):
        url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
        payload = {"body": comment_markdown}
        async with httpx.AsyncClient() as client:
            await client.post(url, headers=self.headers, json=payload)
```

---

## 6. GitHub Actions Workflow Integration Spec (`.github/workflows/astra_ci.yml`)

Developers include this workflow file in their repository root to automatically run Astra on every push:

```yaml
name: ASTRA Automated Testing Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  astra-quality-gate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Trigger ASTRA Quality Analysis
        uses: Curious-Astra/astra-action@v1
        with:
          astra_server_url: "https://astra.yourdomain.com"
          api_key: ${{ secrets.ASTRA_API_KEY }}
          project_id: "e-commerce-api-id"
          fail_on_critical_bugs: true
```

---

## 7. Verification & Test Plan

1. **HMAC Signature Security Test:**
   - Send mock HTTP POST to `/webhooks/github` with an invalid `X-Hub-Signature-256`. Verify endpoint returns `HTTP 403 Forbidden`. Send valid HMAC signature and verify `HTTP 200 OK`.
2. **Pull Request Status Update Test:**
   - Execute mock `update_commit_status()`. Verify status correctly transitions `pending` -> `success` on mock GitHub API server.
3. **PR Comment Generation Verification:**
   - Generate test run with 10 passed tests and 1 critical bug. Verify markdown comment clearly highlights the critical bug and includes a direct link to the Astra Dashboard.
