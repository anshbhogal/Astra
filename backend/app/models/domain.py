import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
    VIEWER = "VIEWER"


class LanguageFramework(str, Enum):
    PYTHON_FASTAPI = "PYTHON_FASTAPI"
    PYTHON_FLASK = "PYTHON_FLASK"
    NODE_EXPRESS = "NODE_EXPRESS"
    JAVA_SPRING = "JAVA_SPRING"
    OTHER = "OTHER"


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), default=UserRole.DEVELOPER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="actor"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repository_url: Mapped[str] = mapped_column(String(500), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    language_framework: Mapped[LanguageFramework] = mapped_column(
        SQLEnum(LanguageFramework), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    analyses: Mapped[List["ProjectAnalysis"]] = relationship(
        "ProjectAnalysis", back_populates="project", cascade="all, delete-orphan"
    )
    test_suites: Mapped[List["TestSuite"]] = relationship(
        "TestSuite", back_populates="project", cascade="all, delete-orphan"
    )
    test_runs: Mapped[List["TestRun"]] = relationship(
        "TestRun", back_populates="project", cascade="all, delete-orphan"
    )


class AnalysisStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AnalysisStage(str, Enum):
    CLONING = "CLONING"
    SCANNING = "SCANNING"
    AST_PARSING = "AST_PARSING"
    GRAPH_BUILDING = "GRAPH_BUILDING"
    PERSISTING = "PERSISTING"
    FINISHED = "FINISHED"


class ProjectAnalysis(Base):
    __tablename__ = "project_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        SQLEnum(AnalysisStatus), default=AnalysisStatus.QUEUED, nullable=False
    )
    current_stage: Mapped[AnalysisStage] = mapped_column(
        SQLEnum(AnalysisStage), default=AnalysisStage.CLONING, nullable=False
    )
    progress_percent: Mapped[int] = mapped_column(default=0, nullable=False)
    repository_url: Mapped[str] = mapped_column(String(500), nullable=False)
    branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    detected_language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    detected_framework: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    framework_confidence: Mapped[float] = mapped_column(default=0.0, nullable=False)
    scanned_files_count: Mapped[int] = mapped_column(default=0, nullable=False)
    parsed_files_count: Mapped[int] = mapped_column(default=0, nullable=False)
    endpoint_count: Mapped[int] = mapped_column(default=0, nullable=False)
    graph_node_count: Mapped[int] = mapped_column(default=0, nullable=False)
    graph_edge_count: Mapped[int] = mapped_column(default=0, nullable=False)
    knowledge_graph: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    analyzer_version: Mapped[str] = mapped_column(String(50), default="2.0.0", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="analyses")
    endpoints: Mapped[List["DiscoveredEndpoint"]] = relationship(
        "DiscoveredEndpoint", back_populates="analysis", cascade="all, delete-orphan"
    )


class DiscoveredEndpoint(Base):
    __tablename__ = "discovered_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    function_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    request_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    response_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    framework: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    line_number: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    analysis: Mapped["ProjectAnalysis"] = relationship("ProjectAnalysis", back_populates="endpoints")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    actor: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


class TestRunStatus(str, Enum):
    PENDING = "PENDING"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"


class TestOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    SKIP = "SKIP"


class TestType(str, Enum):
    HAPPY_PATH = "HAPPY_PATH"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    INVALID_TYPE = "INVALID_TYPE"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_FORMAT = "INVALID_FORMAT"
    EMPTY_VALUE = "EMPTY_VALUE"
    NULL_VALUE = "NULL_VALUE"
    BOUNDARY = "BOUNDARY"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    NOT_FOUND = "NOT_FOUND"


class TestSuite(Base):
    __tablename__ = "test_suites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_analyses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_cases: Mapped[int] = mapped_column(default=0, nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="test_suites")
    analysis: Mapped[Optional["ProjectAnalysis"]] = relationship("ProjectAnalysis")
    test_cases: Mapped[List["TestCase"]] = relationship("TestCase", back_populates="test_suite", cascade="all, delete-orphan")
    test_runs: Mapped[List["TestRun"]] = relationship("TestRun", back_populates="test_suite", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovered_endpoints.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    test_type: Mapped[TestType] = mapped_column(
        SQLEnum(TestType), default=TestType.HAPPY_PATH, nullable=False
    )
    execution_order: Mapped[int] = mapped_column(default=1, nullable=False)
    specification: Mapped[dict] = mapped_column(JSON, nullable=False)
    depends_on: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    test_suite: Mapped["TestSuite"] = relationship("TestSuite", back_populates="test_cases")
    endpoint: Mapped[Optional["DiscoveredEndpoint"]] = relationship("DiscoveredEndpoint")


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[TestRunStatus] = mapped_column(
        SQLEnum(TestRunStatus), default=TestRunStatus.PENDING, nullable=False
    )
    total_tests: Mapped[int] = mapped_column(default=0, nullable=False)
    passed_tests: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_tests: Mapped[int] = mapped_column(default=0, nullable=False)
    error_tests: Mapped[int] = mapped_column(default=0, nullable=False)
    duration_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    target_environment: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="test_runs")
    test_suite: Mapped["TestSuite"] = relationship("TestSuite", back_populates="test_runs")
    results: Mapped[List["TestResult"]] = relationship("TestResult", back_populates="test_run", cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    test_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    test_type: Mapped[TestType] = mapped_column(
        SQLEnum(TestType), default=TestType.HAPPY_PATH, nullable=False
    )
    outcome: Mapped[TestOutcome] = mapped_column(
        SQLEnum(TestOutcome), nullable=False
    )
    status_code: Mapped[Optional[int]] = mapped_column(nullable=True)
    request_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    response_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    response_body_truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    assertion_failures: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="results")
    test_case: Mapped["TestCase"] = relationship("TestCase")


class GenerationJobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_analyses.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[GenerationJobStatus] = mapped_column(
        SQLEnum(GenerationJobStatus), default=GenerationJobStatus.PENDING, nullable=False
    )
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    seed: Mapped[int] = mapped_column(default=42, nullable=False)
    total_candidates: Mapped[int] = mapped_column(default=0, nullable=False)
    total_generated: Mapped[int] = mapped_column(default=0, nullable=False)
    total_deduplicated: Mapped[int] = mapped_column(default=0, nullable=False)
    total_truncated: Mapped[int] = mapped_column(default=0, nullable=False)
    generation_report: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship("Project")
    analysis: Mapped[Optional["ProjectAnalysis"]] = relationship("ProjectAnalysis")


class RequirementDocument(Base):
    __tablename__ = "requirement_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class RequirementSpecModel(Base):
    __tablename__ = "requirement_specs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirement_documents.id", ondelete="CASCADE"), nullable=True
    )
    req_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    req_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="EXTRACTED", nullable=False)
    mapping_status: Mapped[str] = mapped_column(String(50), default="UNMAPPED", nullable=False)
    target_endpoints: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    business_rules: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class LLMExecutionRecord(Base):
    __tablename__ = "llm_execution_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    generation_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_input: Mapped[int] = mapped_column(default=0, nullable=False)
    tokens_output: Mapped[int] = mapped_column(default=0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class FailureAnalysisModel(Base):
    __tablename__ = "failure_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    test_result_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    test_case_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    endpoint_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    exception_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failing_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    failing_line: Mapped[Optional[int]] = mapped_column(nullable=True)
    failing_function: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_mismatch: Mapped[bool] = mapped_column(default=False, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    fault_locations: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    root_cause_candidates: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    diff_items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    parsed_exception: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    classification_confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    attribution_confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    root_cause_confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class DefectClusterModel(Base):
    __tablename__ = "defect_clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    representative_failure_id: Mapped[str] = mapped_column(String(255), nullable=False)
    member_failure_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    member_count: Mapped[int] = mapped_column(default=1, nullable=False)
    similarity_score: Mapped[float] = mapped_column(default=1.0, nullable=False)
    confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    match_precision: Mapped[str] = mapped_column(String(50), default="EXACT_MATCH", nullable=False)
    occurrence_count: Mapped[int] = mapped_column(default=1, nullable=False)
    first_seen_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_seen_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    is_intermittent: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class MLJobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class FlakyTestStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RECOMMENDED_QUARANTINE = "RECOMMENDED_QUARANTINE"
    QUARANTINED = "QUARANTINED"
    RESOLVED = "RESOLVED"


class HealingCandidateStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class MLModelArtifactModel(Base):
    __tablename__ = "ml_model_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0")
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default="XGBClassifier")
    hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    training_commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class FlakyTestRecordModel(Base):
    __tablename__ = "flaky_test_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    flakiness_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    observation_window: Mapped[int] = mapped_column(default=10, nullable=False)
    transition_count: Mapped[int] = mapped_column(default=0, nullable=False)
    pass_count: Mapped[int] = mapped_column(default=0, nullable=False)
    fail_count: Mapped[int] = mapped_column(default=0, nullable=False)
    latency_mean_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    latency_std_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    status: Mapped[FlakyTestStatus] = mapped_column(
        SQLEnum(FlakyTestStatus), default=FlakyTestStatus.ACTIVE, nullable=False
    )
    last_evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class TestPriorityRankingModel(Base):
    __tablename__ = "test_priority_rankings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    failure_probability: Mapped[float] = mapped_column(nullable=False)
    execution_cost_ms: Mapped[float] = mapped_column(nullable=False)
    severity_weight: Mapped[float] = mapped_column(nullable=False)
    priority_score: Mapped[float] = mapped_column(nullable=False)
    rank_order: Mapped[int] = mapped_column(nullable=False)
    strategy: Mapped[str] = mapped_column(String(50), default="BALANCED", nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class HealingCandidateModel(Base):
    __tablename__ = "healing_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    failure_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("failure_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False
    )
    original_specification: Mapped[dict] = mapped_column(JSON, nullable=False)
    proposed_specification: Mapped[dict] = mapped_column(JSON, nullable=False)
    patch_operations: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(default=0.8, nullable=False)
    status: Mapped[HealingCandidateStatus] = mapped_column(
        SQLEnum(HealingCandidateStatus), default=HealingCandidateStatus.PENDING, nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resulting_spec_version: Mapped[int] = mapped_column(default=1, nullable=False)
    rollback_available: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class MLActionAuditLogModel(Base):
    __tablename__ = "ml_action_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class ExecutionTier(str, Enum):
    TIER1_TARGETED = "TIER1_TARGETED"
    TIER2_DEFERRED_FULL = "TIER2_DEFERRED_FULL"


class RegressionAnalysisStatus(str, Enum):
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RegressionAnalysisModel(Base):
    __tablename__ = "regression_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    base_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    target_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    target_branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pkg_snapshot_version: Mapped[str] = mapped_column(String(50), default="v1.0", nullable=False)
    total_modified_files: Mapped[int] = mapped_column(default=0, nullable=False)
    total_modified_symbols: Mapped[int] = mapped_column(default=0, nullable=False)
    total_impacted_endpoints: Mapped[int] = mapped_column(default=0, nullable=False)
    total_suite_tests: Mapped[int] = mapped_column(default=0, nullable=False)
    selected_tier1_count: Mapped[int] = mapped_column(default=0, nullable=False)
    deferred_tier2_count: Mapped[int] = mapped_column(default=0, nullable=False)
    test_reduction_percent: Mapped[float] = mapped_column(default=0.0, nullable=False)
    estimated_time_avoided_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    impact_confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    safety_expansion_triggered: Mapped[bool] = mapped_column(default=False, nullable=False)
    status: Mapped[RegressionAnalysisStatus] = mapped_column(
        SQLEnum(RegressionAnalysisStatus), default=RegressionAnalysisStatus.QUEUED, nullable=False
    )
    analysis_warnings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class CodeChangeManifestModel(Base):
    __tablename__ = "code_change_manifests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    regression_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regression_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    new_path: Mapped[str] = mapped_column(String(500), nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rename_similarity: Mapped[float] = mapped_column(default=1.0, nullable=False)
    modified_lines: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    modified_symbols: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    change_category: Mapped[str] = mapped_column(String(50), default="FUNCTION_MODIFIED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class EndpointImpactRecordModel(Base):
    __tablename__ = "endpoint_impact_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    regression_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regression_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint_id: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    impact_distance: Mapped[int] = mapped_column(default=0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(default=1.0, nullable=False)
    impact_type: Mapped[str] = mapped_column(String(30), default="DIRECT", nullable=False)
    impact_path_trace: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    dependency_edge_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class SelectiveExecutionRunModel(Base):
    __tablename__ = "selective_execution_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    regression_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regression_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    execution_tier: Mapped[ExecutionTier] = mapped_column(
        SQLEnum(ExecutionTier), default=ExecutionTier.TIER1_TARGETED, nullable=False
    )
    selected_test_details: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    deferred_test_details: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    selection_recall: Mapped[float] = mapped_column(default=1.0, nullable=False)
    selection_precision: Mapped[float] = mapped_column(default=1.0, nullable=False)
    tier1_actual_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    tier2_actual_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class CIPipelineStatus(str, Enum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    ANALYZING = "ANALYZING"
    SELECTING = "SELECTING"
    EXECUTING = "EXECUTING"
    EVALUATING = "EVALUATING"
    REPORTING = "REPORTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"
    STALE = "STALE"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"


class WebhookEventModel(Base):
    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(20), default="GITHUB", nullable=False)
    delivery_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    signature_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    sender: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payload_redacted: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("provider", "delivery_id", name="uq_provider_delivery_id"),
    )


class CIPipelineRunModel(Base):
    __tablename__ = "ci_pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    regression_analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regression_analyses.id", ondelete="SET NULL"), nullable=True
    )
    test_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="SET NULL"), nullable=True
    )
    webhook_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("webhook_events.id", ondelete="SET NULL"), nullable=True
    )
    git_provider: Mapped[str] = mapped_column(String(20), default="GITHUB", nullable=False)
    repository_full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    pr_number: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    base_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    target_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pipeline_status: Mapped[CIPipelineStatus] = mapped_column(
        SQLEnum(CIPipelineStatus), default=CIPipelineStatus.QUEUED, nullable=False
    )
    quality_gate_status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    github_check_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class NotificationChannelModel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False)  # SLACK, MS_TEAMS, EMAIL, WEBHOOK
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_target_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    events_filter: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class NotificationDeliveryModel(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ci_pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False
    )
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)  # SENT, FAILED, RETRYING
    attempt_count: Mapped[int] = mapped_column(default=1, nullable=False)
    response_code: Mapped[Optional[int]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )






