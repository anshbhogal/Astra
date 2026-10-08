"""
ASTRA Engine - Phase 6 Analysis Data Models

Defines failure evidence, parsed exceptions, structural JSON diffs, candidate fault locations,
root-cause candidates, failure analysis reports, and defect clusters.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime


class EvidenceType(str, Enum):
    STACK_TRACE = "STACK_TRACE"
    HTTP_STATUS = "HTTP_STATUS"
    RESPONSE_BODY = "RESPONSE_BODY"
    JSON_DIFF = "JSON_DIFF"
    ASSERTION_FAILURE = "ASSERTION_FAILURE"
    TIMEOUT = "TIMEOUT"
    LOG_MESSAGE = "LOG_MESSAGE"
    SOURCE_LOCATION = "SOURCE_LOCATION"
    KNOWLEDGE_GRAPH = "KNOWLEDGE_GRAPH"


class FailureCategory(str, Enum):
    SERVER_CRASH = "SERVER_CRASH"
    BUSINESS_LOGIC_DEFECT = "BUSINESS_LOGIC_DEFECT"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    REQUEST_VALIDATION_DEFECT = "REQUEST_VALIDATION_DEFECT"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    DATABASE_ERROR = "DATABASE_ERROR"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    TIMEOUT_PERFORMANCE = "TIMEOUT_PERFORMANCE"
    ENVIRONMENT_FLAKE = "ENVIRONMENT_FLAKE"
    NOT_FOUND_DEFECT = "NOT_FOUND_DEFECT"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    UNKNOWN = "UNKNOWN"


class DiffType(str, Enum):
    VALUE_MISMATCH = "VALUE_MISMATCH"
    MISSING_KEY = "MISSING_KEY"
    EXTRA_KEY = "EXTRA_KEY"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH"
    ARRAY_ITEM_MISMATCH = "ARRAY_ITEM_MISMATCH"


class ReasoningType(str, Enum):
    EXCEPTION_ORIGIN = "EXCEPTION_ORIGIN"
    CALLER_FRAME = "CALLER_FRAME"
    DOWNSTREAM_DEPENDENCY = "DOWNSTREAM_DEPENDENCY"
    JSON_CONTRACT_MISMATCH = "JSON_CONTRACT_MISMATCH"
    STATUS_MISMATCH = "STATUS_MISMATCH"
    DATABASE_CONSTRAINT = "DATABASE_CONSTRAINT"
    TIMEOUT = "TIMEOUT"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    CALL_CHAIN_INFERENCE = "CALL_CHAIN_INFERENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ClusterMatchPrecision(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    LIKELY_SAME = "LIKELY_SAME"
    POSSIBLY_SAME = "POSSIBLY_SAME"


@dataclass
class FailureEvidence:
    evidence_type: EvidenceType
    source: str
    description: str
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    location: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value if isinstance(self.evidence_type, Enum) else self.evidence_type,
            "source": self.source,
            "description": self.description,
            "location": self.location,
            "payload": self.payload,
            "confidence": self.confidence,
        }


@dataclass
class StackFrame:
    file_path: str
    line_number: int
    function_name: str
    code_snippet: Optional[str] = None
    is_in_project: bool = True
    variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParsedException:
    exception_type: str
    message: str
    frames: List[StackFrame] = field(default_factory=list)
    language: str = "python"
    raw_trace_hash: str = ""
    sql_state: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exception_type": self.exception_type,
            "message": self.message,
            "frames": [f.to_dict() for f in self.frames],
            "language": self.language,
            "raw_trace_hash": self.raw_trace_hash,
            "sql_state": self.sql_state,
        }


@dataclass
class JsonDiffItem:
    path: str  # e.g. "$.body.items[2].price"
    expected: Any
    actual: Any
    diff_type: DiffType
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "expected": self.expected,
            "actual": self.actual,
            "diff_type": self.diff_type.value if isinstance(self.diff_type, Enum) else self.diff_type,
            "message": self.message,
        }


@dataclass
class FaultLocation:
    file_path: str
    line_number: int
    function_name: Optional[str] = None
    confidence: float = 1.0
    reason: ReasoningType = ReasoningType.EXCEPTION_ORIGIN
    pkg_node_id: Optional[str] = None
    code_context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "function_name": self.function_name,
            "confidence": self.confidence,
            "reason": self.reason.value if isinstance(self.reason, Enum) else self.reason,
            "pkg_node_id": self.pkg_node_id,
            "code_context": self.code_context,
        }


@dataclass
class RootCauseCandidate:
    description: str
    reasoning_type: ReasoningType
    candidate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evidence_ids: List[str] = field(default_factory=list)
    fault_locations: List[FaultLocation] = field(default_factory=list)
    confidence: float = 1.0
    suggested_remediation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "description": self.description,
            "reasoning_type": self.reasoning_type.value if isinstance(self.reasoning_type, Enum) else self.reasoning_type,
            "evidence_ids": self.evidence_ids,
            "fault_locations": [loc.to_dict() for loc in self.fault_locations],
            "confidence": self.confidence,
            "suggested_remediation": self.suggested_remediation,
        }


@dataclass
class FailureAnalysis:
    test_result_id: str
    test_case_id: str
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    endpoint_id: Optional[str] = None
    category: FailureCategory = FailureCategory.UNKNOWN
    summary: str = ""
    error_message: str = ""
    exception_type: Optional[str] = None
    failing_file: Optional[str] = None
    failing_line: Optional[int] = None
    failing_function: Optional[str] = None
    commit_sha: Optional[str] = None
    source_mismatch: bool = False
    evidence: List[FailureEvidence] = field(default_factory=list)
    fault_locations: List[FaultLocation] = field(default_factory=list)
    root_cause_candidates: List[RootCauseCandidate] = field(default_factory=list)
    diff_items: List[JsonDiffItem] = field(default_factory=list)
    parsed_exception: Optional[ParsedException] = None
    fingerprint: str = ""
    classification_confidence: float = 1.0
    attribution_confidence: float = 1.0
    root_cause_confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "test_result_id": self.test_result_id,
            "test_case_id": self.test_case_id,
            "endpoint_id": self.endpoint_id,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "summary": self.summary,
            "error_message": self.error_message,
            "exception_type": self.exception_type,
            "failing_file": self.failing_file,
            "failing_line": self.failing_line,
            "failing_function": self.failing_function,
            "commit_sha": self.commit_sha,
            "source_mismatch": self.source_mismatch,
            "evidence": [e.to_dict() for e in self.evidence],
            "fault_locations": [f.to_dict() for f in self.fault_locations],
            "root_cause_candidates": [c.to_dict() for c in self.root_cause_candidates],
            "diff_items": [d.to_dict() for d in self.diff_items],
            "parsed_exception": self.parsed_exception.to_dict() if self.parsed_exception else None,
            "fingerprint": self.fingerprint,
            "classification_confidence": self.classification_confidence,
            "attribution_confidence": self.attribution_confidence,
            "root_cause_confidence": self.root_cause_confidence,
            "created_at": self.created_at,
        }


@dataclass
class DefectCluster:
    cluster_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    fingerprint: str = ""
    category: FailureCategory = FailureCategory.UNKNOWN
    summary: str = ""
    representative_failure_id: str = ""
    member_failure_ids: List[str] = field(default_factory=list)
    member_count: int = 1
    similarity_score: float = 1.0
    confidence: float = 1.0
    match_precision: ClusterMatchPrecision = ClusterMatchPrecision.EXACT_MATCH
    occurrence_count: int = 1
    first_seen_run_id: Optional[str] = None
    last_seen_run_id: Optional[str] = None
    last_seen_at: Optional[str] = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_intermittent: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "fingerprint": self.fingerprint,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "summary": self.summary,
            "representative_failure_id": self.representative_failure_id,
            "member_failure_ids": self.member_failure_ids,
            "member_count": self.member_count,
            "similarity_score": self.similarity_score,
            "confidence": self.confidence,
            "match_precision": self.match_precision.value if isinstance(self.match_precision, Enum) else self.match_precision,
            "occurrence_count": self.occurrence_count,
            "first_seen_run_id": self.first_seen_run_id,
            "last_seen_run_id": self.last_seen_run_id,
            "last_seen_at": self.last_seen_at,
            "is_intermittent": self.is_intermittent,
        }
