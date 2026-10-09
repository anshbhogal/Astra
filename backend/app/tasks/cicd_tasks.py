"""Celery Background Worker Tasks for Phase 9 CI/CD Pipeline & Isolated Notifications."""

import asyncio
import uuid
from typing import Dict, Any, Optional

from app.core.celery_app import celery_app
from app.db.session import async_session_factory
from app.services.cicd_service import CICDService
from engine.cicd.notifications.slack_dispatcher import SlackNotificationDispatcher
from engine.cicd.notifications.teams_dispatcher import TeamsNotificationDispatcher
from engine.cicd.notifications.email_dispatcher import EmailNotificationDispatcher


def _run_async(coro):
    """Utility to execute async coroutine within Celery worker thread loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.cicd_tasks.process_github_webhook_task")
def process_github_webhook_task(event_id_str: str) -> Dict[str, Any]:
    """Celery worker task running end-to-end webhook processing."""
    event_id = uuid.UUID(event_id_str)

    async def _impl():
        async with async_session_factory() as db:
            service = CICDService(db)
            return await service.process_webhook_event(event_id)

    return _run_async(_impl())


@celery_app.task(name="app.tasks.cicd_tasks.send_slack_notification_task")
def send_slack_notification_task(target_url: str, title: str, payload: Dict[str, Any]) -> bool:
    """Isolated Celery task for Slack Block Kit notification dispatching."""
    dispatcher = SlackNotificationDispatcher()
    return _run_async(dispatcher.send_notification(target_url, title, payload))


@celery_app.task(name="app.tasks.cicd_tasks.send_teams_notification_task")
def send_teams_notification_task(target_url: str, title: str, payload: Dict[str, Any]) -> bool:
    """Isolated Celery task for Microsoft Teams Adaptive Card notification dispatching."""
    dispatcher = TeamsNotificationDispatcher()
    return _run_async(dispatcher.send_notification(target_url, title, payload))


@celery_app.task(name="app.tasks.cicd_tasks.send_email_notification_task")
def send_email_notification_task(target_email: str, title: str, payload: Dict[str, Any]) -> bool:
    """Isolated Celery task for SMTP HTML summary email dispatching."""
    dispatcher = EmailNotificationDispatcher()
    return _run_async(dispatcher.send_notification(target_email, title, payload))
