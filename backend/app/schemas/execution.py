import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.domain import TestRunStatus, TestOutcome, TestType


class TestSuiteGenerateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Optional custom name for the synthetic test suite")
    analysis_id: Optional[uuid.UUID] = Field(None, description="Optional specific analysis snapshot ID")


class TestSuiteResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    analysis_id: Optional[uuid.UUID] = None
    name: str
    description: Optional[str] = None
    total_cases: int
    version: str
    is_immutable: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestSuiteListResponse(BaseModel):
    items: List[TestSuiteResponse]
    total: int
    page: int
    page_size: int


class TestRunCreateRequest(BaseModel):
    suite_id: uuid.UUID
    target_base_url: Optional[str] = Field("http://localhost:8000", description="Target application base URL")
    environment_type: Optional[str] = Field("LOCAL_SANDBOX", description="LOCAL_SANDBOX or EXTERNAL")
    health_check_path: Optional[str] = Field("/health", description="Pre-flight liveness check endpoint")


class TestResultResponse(BaseModel):
    id: uuid.UUID
    test_run_id: uuid.UUID
    test_case_id: uuid.UUID
    endpoint: str
    method: str
    test_type: TestType
    outcome: TestOutcome
    status_code: Optional[int] = None
    request_data: Dict[str, Any]
    response_data: Optional[Dict[str, Any]] = None
    response_body_truncated: bool
    execution_time_ms: float
    assertion_failures: List[Dict[str, Any]]
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TestResultListResponse(BaseModel):
    items: List[TestResultResponse]
    total: int
    page: int
    page_size: int


class TestRunResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    suite_id: uuid.UUID
    status: TestRunStatus
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    duration_ms: float
    target_environment: Dict[str, Any]
    triggered_by: Optional[uuid.UUID] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TestRunListResponse(BaseModel):
    items: List[TestRunResponse]
    total: int
    page: int
    page_size: int
