"""
Pydantic Validation Schemas for Requirement Intelligence APIs.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class RequirementUploadRequest(BaseModel):
    filename: str
    source_type: str = Field(..., description="PRD_MARKDOWN, GHERKIN_FEATURE, OPENAPI_SPEC")
    content: str


class RequirementSpecResponse(BaseModel):
    id: str
    project_id: str
    document_id: Optional[str] = None
    req_code: str
    title: str
    description: str
    req_type: str
    status: str
    mapping_status: str
    target_endpoints: List[str] = []
    confidence: float
    business_rules: List[Dict[str, Any]] = []
    created_at: datetime

    class Config:
        from_attributes = True


class RequirementReviewRequest(BaseModel):
    status: str = Field(..., description="APPROVED, REJECTED, NEEDS_REVIEW")
    target_endpoints: Optional[List[str]] = None


class TraceabilityMatrixItem(BaseModel):
    requirement_id: str
    req_code: str
    title: str
    status: str
    mapping_status: str
    target_endpoints: List[str]
    rule_tests_count: int = 0
    ai_tests_count: int = 0
    coverage_status: str = "NOT_COVERED"  # NOT_COVERED, GENERATED, VERIFIED


class LLMConfigPayload(BaseModel):
    provider: str = Field("gemini", description="gemini, ollama, openai, anthropic")
    model: Optional[str] = None
    api_key_ref: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 100000
