from fastapi import APIRouter, Depends, HTTPException, status
from celery.result import AsyncResult

from app.core.celery_app import celery_app, health_check_task
from app.core.security import get_current_user
from app.core.rbac import require_roles
from app.models.domain import User, UserRole

router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


@router.post("/test", status_code=status.HTTP_202_ACCEPTED)
async def dispatch_sample_task(
    payload: dict = None,
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """Dispatch a sample background task to Celery."""
    task = health_check_task.delay(payload or {"triggered_by": current_user.email})
    return {
        "task_id": task.id,
        "status": "QUEUED",
        "message": "Sample health check task dispatched to Celery background worker."
    }


@router.get("/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Retrieve status and result of a background Celery task."""
    res = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "state": res.state,
    }
    
    if res.state == "SUCCESS":
        response["result"] = res.result
    elif res.state == "FAILURE":
        response["error"] = str(res.result)
        
    return response
