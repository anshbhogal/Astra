import pytest
from engine.cicd.notifications.slack_dispatcher import SlackNotificationDispatcher
from engine.cicd.notifications.teams_dispatcher import TeamsNotificationDispatcher
from engine.cicd.notifications.email_dispatcher import EmailNotificationDispatcher


@pytest.mark.asyncio
async def test_slack_ssrf_blocking():
    dispatcher = SlackNotificationDispatcher()
    # Malicious cloud metadata IP target
    blocked_url = "http://169.254.169.254/latest/meta-data/"
    res = await dispatcher.send_notification(blocked_url, "Test", {"status": "PASS"})
    assert res is False


@pytest.mark.asyncio
async def test_email_dispatcher_mock():
    dispatcher = EmailNotificationDispatcher()
    res = await dispatcher.send_notification("dev@example.com", "Test Title", {"status": "PASS", "total_tests": 5})
    assert res is True
