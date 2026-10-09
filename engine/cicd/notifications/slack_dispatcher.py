"""Slack Block Kit Notification Dispatcher with SSRF Validation."""

import logging
from typing import Dict, Any, Optional
import httpx
from engine.cicd.notifications.base_dispatcher import BaseNotificationDispatcher
from engine.security.ssrf_protector import SSRFProtector, SSRFValidationError
from engine.models.target_env import TargetEnvironmentConfig, EnvironmentType

logger = logging.getLogger("astra.slack_dispatcher")


class SlackNotificationDispatcher(BaseNotificationDispatcher):
    """Formats and posts Block Kit notifications to Slack incoming webhooks."""

    async def send_notification(
        self,
        target_url: str,
        title: str,
        payload: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        # 1. SSRF Validation
        env_config = TargetEnvironmentConfig(
            base_url=target_url,
            environment_type=EnvironmentType.EXTERNAL,
        )
        try:
            SSRFProtector.validate_url(target_url, env_config)
        except SSRFValidationError as exc:
            logger.error(f"SSRF validation blocked Slack webhook target '{target_url}': {exc}")
            return False

        # 2. Build Slack Block Kit Payload
        status = payload.get("status", "PASS")
        total_tests = payload.get("total_tests", 0)
        passed_tests = payload.get("passed_tests", 0)
        failed_tests = payload.get("failed_tests", 0)
        reduction_pct = payload.get("reduction_percent", 0.0)

        color = "#10B981" if status == "PASS" else ("#F43F5E" if status == "FAIL" else "#F59E0B")

        slack_body = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": f"ASTRA Quality Gate: {title}"},
                        },
                        {
                            "type": "section",
                            "fields": [
                                {"type": "mrkdwn", "text": f"*Status:*\n`{status}`"},
                                {"type": "mrkdwn", "text": f"*Reduction:*\n`-{reduction_pct:.1f}%`"},
                                {"type": "mrkdwn", "text": f"*Passed:*\n`{passed_tests}/{total_tests}`"},
                                {"type": "mrkdwn", "text": f"*Failed:*\n`{failed_tests}`"},
                            ],
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"ASTRA Engine | Commit `{payload.get('commit_sha', 'HEAD')[:7]}` | PR #{payload.get('pr_number', 'N/A')}",
                                }
                            ],
                        },
                    ],
                }
            ]
        }

        # 3. Post to Slack Webhook
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(target_url, json=slack_body)
                return resp.status_code in [200, 201, 204]
        except Exception as exc:
            logger.error(f"Failed to dispatch Slack notification: {exc}")
            return False
