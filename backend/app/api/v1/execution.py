import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.execution import (
    TestSuiteGenerateRequest,
    TestSuiteResponse,
    TestSuiteListResponse,
    TestRunCreateRequest,
    TestRunResponse,
    TestRunListResponse,
    TestResultResponse,
    TestResultListResponse
)
from app.services import execution_service
from app.core.security import get_current_user
from app.core.rbac import require_roles
from app.models.domain import User, UserRole

router = APIRouter(prefix="", tags=["Test Execution Engine"])


@router.post("/projects/{project_id}/test-suites/generate", response_model=TestSuiteResponse, status_code=status.HTTP_201_CREATED)
async def generate_synthetic_test_suite(
    project_id: uuid.UUID,
    payload: Optional[TestSuiteGenerateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """Generate a synthetic test suite from AST static analysis endpoints."""
    custom_name = payload.name if payload else None
    suite = await execution_service.generate_synthetic_suite(db, project_id, custom_name, current_user)
    return suite


@router.get("/projects/{project_id}/test-suites", response_model=TestSuiteListResponse)
async def list_project_test_suites(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all generated test suites for a project."""
    items, total = await execution_service.get_project_test_suites(db, project_id, current_user, page=page, page_size=page_size)
    return TestSuiteListResponse(
        items=[TestSuiteResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/projects/{project_id}/test-runs", response_model=TestRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def dispatch_test_run(
    project_id: uuid.UUID,
    payload: TestRunCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """Dispatch an asynchronous test suite execution run."""
    test_run = await execution_service.trigger_test_run(
        db=db,
        project_id=project_id,
        suite_id=payload.suite_id,
        target_base_url=payload.target_base_url or "http://localhost:8000",
        environment_type=payload.environment_type or "LOCAL_SANDBOX",
        health_check_path=payload.health_check_path or "/health",
        current_user=current_user
    )
    return test_run


@router.get("/projects/{project_id}/test-runs", response_model=TestRunListResponse)
async def list_project_test_runs(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List test run execution history for a project."""
    items, total = await execution_service.get_project_test_runs(db, project_id, current_user, page=page, page_size=page_size)
    return TestRunListResponse(
        items=[TestRunResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/test-runs/{test_run_id}", response_model=TestRunResponse)
async def get_test_run_status(
    test_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details and real-time status of a specific test run."""
    run = await execution_service.get_test_run_by_id(db, test_run_id, current_user)
    return run


@router.get("/test-runs/{test_run_id}/results", response_model=TestResultListResponse)
async def get_test_run_step_results(
    test_run_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve detailed step-by-step test result items for a test run."""
    items, total = await execution_service.get_test_run_results(db, test_run_id, current_user, page=page, page_size=page_size)
    return TestResultListResponse(
        items=[TestResultResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/test-runs/{test_run_id}/cancel", response_model=TestRunResponse)
async def cancel_active_test_run(
    test_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """Trigger cooperative cancellation for a running test execution."""
    run = await execution_service.cancel_test_run(db, test_run_id, current_user)
    return run
