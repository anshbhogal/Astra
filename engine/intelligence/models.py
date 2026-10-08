"""
Data Models for Phase 5 Requirement Intelligence, Evidence Traceability, and AI Candidates.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from engine.generator.models import ParameterMutation, TestType


class RequirementType(str, Enum):
    FUNCTIONAL = "FUNCTIONAL"
    BUSINESS_RULE = "BUSINESS_RULE"
    SECURITY = "SECURITY"
    VALIDATION = "VALIDATION"
    STATE_TRANSITION = "STATE_TRANSITION"
    AUTHORIZATION = "AUTHORIZATION"


class RequirementSource(str, Enum):
    PRD_MARKDOWN = "PRD_MARKDOWN"
    USER_STORY = "USER_STORY"
    GHERKIN_FEATURE = "GHERKIN_FEATURE"
    OPENAPI_SPEC = "OPENAPI_SPEC"
    CODE_DOCSTRING = "CODE_DOCSTRING"
    MANUAL_INPUT = "MANUAL_INPUT"


class RequirementStatus(str, Enum):
    EXTRACTED = "EXTRACTED"
    MAPPED = "MAPPED"
    AMBIGUOUS = "AMBIGUOUS"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MappingStatus(str, Enum):
    MAPPED = "MAPPED"
    MULTIPLE_MATCHES = "MULTIPLE_MATCHES"
    UNMAPPED = "UNMAPPED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass
class SourceLocation:
    page: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section: Optional[str] = None


@dataclass
class RequirementEvidence:
    source_document_id: str
    source_type: RequirementSource
    location: SourceLocation
    excerpt_hash: str
    extraction_method: str
    confidence: float


@dataclass
class BusinessRule:
    rule_id: str
    description: str
    preconditions: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    affected_fields: List[str] = field(default_factory=list)
    affected_endpoints: List[str] = field(default_factory=list)
    affected_states: List[str] = field(default_factory=list)
    priority: int = 1
    confidence: float = 1.0
    evidence: List[RequirementEvidence] = field(default_factory=list)


@dataclass
class RequirementSpec:
    id: str
    project_id: str
    document_id: str
    source: RequirementSource
    source_location: SourceLocation
    title: str
    description: str
    requirement_type: RequirementType
    priority: int = 1
    confidence: float = 1.0
    status: RequirementStatus = RequirementStatus.EXTRACTED
    mapping_status: MappingStatus = MappingStatus.UNMAPPED
    target_endpoints: List[str] = field(default_factory=list)
    business_rules: List[BusinessRule] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    states: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    ambiguity_flags: List[str] = field(default_factory=list)
    extraction_method: str = "DETERMINISTIC_PARSER"
    parser_version: str = "5.0.0"
    content_hash: str = ""


@dataclass
class GherkinScenarioStep:
    keyword: str  # "Given", "When", "Then", "And", "But"
    text: str
    step_type: str  # "PRECONDITION", "ACTION", "EXPECTED"
    target_endpoint: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GherkinScenario:
    feature_title: str
    scenario_title: str
    steps: List[GherkinScenarioStep] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LLMScenarioCandidate:
    candidate_id: str
    requirement_ids: List[str]
    endpoint_id: Optional[str]
    scenario_description: str
    test_type: TestType
    mutations: List[ParameterMutation]
    rationale: str
    assumptions: List[str]
    confidence: float
    provider: str
    model: str
    prompt_version: str
    validation_status: str = "PENDING"  # PENDING, VALIDATED, REJECTED
    rejection_reason: Optional[str] = None
