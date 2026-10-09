"""Microsoft Teams Adaptive Card Notification Dispatcher."""

import logging
from typing import Dict, Any, Optional
import httpx
from engine.cicd.notifications.base_dispatcher import BaseNotificationDispatcher
from engine.security.ssrf_protector import SSRFProtector, SSRFValidationError
from engine.models.target_env import TargetEnvironmentConfig, EnvironmentType

logger = logging.getLogger("astra.teams_dispatcher")


class TeamsNotificationDispatcher(BaseNotificationDispatcher):
    """Formats and posts Adaptive Card v1.4 payloads to Microsoft Teams webhooks."""

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
            logger.error(f"SSRF validation blocked Teams webhook target '{target_url}': {exc}")
            return False

        # 2. Build Teams Adaptive Card
        status = payload.get("status", "PASS")
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Medium",
                                "weight": "Bolder",
                                "text": f"ASTRA Quality Gate: {title}",
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Status", "value": status},
                                    {"title": "Total Tests", "value": str(payload.get("total_tests", 0))},
                                    {"title": "Passed", "value": str(payload.get("passed_tests", 0))},
                                    {"title": "Failed", "value": str(payload.get("failed_tests", 0))},
                                ],
                            },
                        ],
                    },
                }
            ],
        }

        # 3. Post to Teams Webhook
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(target_url, json=card)
                return resp.status_code in [200, 201, 204]
        except Exception as exc:
            logger.error(f"Failed to dispatch Teams notification: {exc}")
            return False
