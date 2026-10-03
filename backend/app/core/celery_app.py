from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "astra_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
)


@celery_app.task(name="tasks.health_check_task")
def health_check_task(payload: dict = None) -> dict:
    """Sample infrastructure verification task."""
    return {
        "status": "SUCCESS",
        "message": "Celery worker operational",
        "payload": payload or {}
    }
