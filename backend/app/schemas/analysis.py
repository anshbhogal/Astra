"""
Pydantic v2 schemas for Phase 6 Failure Analysis & Defect Clusters
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
import uuid


class StackFrameSchema(BaseModel):
    file_path: str
    line_number: int
    function_name: str
    code_snippet: Optional[str] = None
    is_in_project: bool = True


class JsonDiffItemSchema(BaseModel):
    path: str
    expected: Any
    actual: Any
    diff_type: str
    message: str = ""


class FailureEvidenceSchema(BaseModel):
    evidence_id: str
    evidence_type: str
    source: str
    description: str
    location: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class FaultLocationSchema(BaseModel):
    file_path: str
    line_number: int
    function_name: Optional[str] = None
    confidence: float = 1.0
    reason: str
    pkg_node_id: Optional[str] = None
    code_context: Optional[str] = None


class RootCauseCandidateSchema(BaseModel):
    candidate_id: str
    description: str
    reasoning_type: str
    evidence_ids: List[str] = Field(default_factory=list)
    fault_locations: List[FaultLocationSchema] = Field(default_factory=list)
    confidence: float = 1.0
    suggested_remediation: Optional[str] = None


class FailureAnalysisResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    run_id: Optional[uuid.UUID] = None
    test_result_id: str
    test_case_id: str
    endpoint_id: Optional[str] = None
    category: str
    summary: str
    error_message: str
    exception_type: Optional[str] = None
    failing_file: Optional[str] = None
    failing_line: Optional[int] = None
    failing_function: Optional[str] = None
    commit_sha: Optional[str] = None
    source_mismatch: bool = False
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    fault_locations: List[Dict[str, Any]] = Field(default_factory=list)
    root_cause_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    diff_items: List[Dict[str, Any]] = Field(default_factory=list)
    parsed_exception: Optional[Dict[str, Any]] = None
    fingerprint: str
    classification_confidence: float
    attribution_confidence: float
    root_cause_confidence: float
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class DefectClusterResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    fingerprint: str
    category: str
    summary: str
    representative_failure_id: str
    member_failure_ids: List[str] = Field(default_factory=list)
    member_count: int
    similarity_score: float
    confidence: float
    match_precision: str
    occurrence_count: int
    first_seen_run_id: Optional[str] = None
    last_seen_run_id: Optional[str] = None
    last_seen_at: str
    is_intermittent: bool = False

    model_config = ConfigDict(from_attributes=True)
