import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON, Boolean
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
        DateTime(timezone=True), default_utc_now, nullable=False
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
