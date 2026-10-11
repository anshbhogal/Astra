"""Gen 2 Canonical Schema — Phase 1 DDL

Pure DDL migration. Creates all Gen 2 canonical tables.
No data is moved or altered in this migration.

Revision ID: 0011_canonical_schema
Revises: 0010_analytics_and_benchmarks
Create Date: 2026-10-11 18:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011_canonical_schema"
down_revision: Union[str, None] = "0010_analytics_and_benchmarks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. WORKSPACES
    # -------------------------------------------------------------------------
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column(
            "plan_tier",
            sa.String(50),
            nullable=False,
            server_default="ENTERPRISE",
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint("slug", name="uq_workspaces_slug"),
    )

    # Attach projects to workspaces (additive; existing rows get NULL → DEFAULT ws)
    op.add_column(
        "projects",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,  # nullable until backfill assigns default workspace
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
    )
    op.create_index("idx_projects_workspace_id", "projects", ["workspace_id"])

    # -------------------------------------------------------------------------
    # 2. REQUIREMENTS (header) + REQUIREMENT_VERSIONS (immutable snapshots)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("req_code", sa.String(50), nullable=False),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "current_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,  # Set after first version created; FK added below
        ),
        sa.Column(
            "source_type",
            sa.String(30),
            nullable=False,
            server_default="MANUAL",
        ),
        sa.Column("source_reference", sa.String(255), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint("project_id", "req_code", name="uq_project_req_code"),
    )
    op.create_index("idx_g2_requirements_project", "g2_requirements", ["project_id"])

    op.create_table(
        "g2_requirement_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "requirement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_requirements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "acceptance_criteria",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("change_reason", sa.String(255), nullable=True),
        sa.Column(
            "is_approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "changed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint(
            "requirement_id", "version_number", name="uq_req_version"
        ),
    )
    op.create_index(
        "idx_g2_req_versions_req",
        "g2_requirement_versions",
        ["requirement_id"],
    )

    # Deferred FK from g2_requirements.current_version_id → g2_requirement_versions.id
    op.create_foreign_key(
        "fk_req_current_version",
        "g2_requirements",
        "g2_requirement_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -------------------------------------------------------------------------
    # 3. BUILDS (immutable CI/release snapshots)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_builds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_name", sa.String(100), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.Column(
            "branch",
            sa.String(100),
            nullable=False,
            server_default="main",
        ),
        sa.Column("pipeline_provider", sa.String(50), nullable=True),
        sa.Column("pipeline_id", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="REGISTERED",
        ),
        sa.Column(
            "build_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
    )
    op.create_index(
        "idx_builds_project_version",
        "g2_builds",
        ["project_id", "version_name"],
        unique=True,
    )
    op.create_index(
        "idx_builds_project_commit",
        "g2_builds",
        ["project_id", "commit_sha"],
    )

    # -------------------------------------------------------------------------
    # 4. ENVIRONMENTS (SSRF-safe, credential-referenced)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_environments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("env_type", sa.String(50), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("credential_reference", sa.String(255), nullable=True),
        sa.Column(
            "health_check_endpoint",
            sa.String(255),
            nullable=True,
            server_default="/health",
        ),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint(
            "project_id", "name", name="uq_project_env_name"
        ),
    )
    op.create_index(
        "idx_g2_environments_project", "g2_environments", ["project_id"]
    )

    # -------------------------------------------------------------------------
    # 5. HIERARCHICAL TEST SUITES (Gen 2 canonical — replaces flat Gen 1 suites)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_test_suites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_suite_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_suites.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "suite_type",
            sa.String(30),
            nullable=False,
            server_default="STANDARD",
        ),
        sa.Column(
            "order_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
    )
    op.create_index(
        "idx_g2_suites_project", "g2_test_suites", ["project_id"]
    )
    op.create_index(
        "idx_g2_suites_parent", "g2_test_suites", ["parent_suite_id"]
    )

    # -------------------------------------------------------------------------
    # 6. TEST DEFINITIONS + IMMUTABLE VERSIONED SPECIFICATIONS
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_test_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "suite_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_suites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("test_code", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("execution_type", sa.String(20), nullable=False),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Provenance
        sa.Column(
            "source_type",
            sa.String(30),
            nullable=False,
            server_default="MANUAL",
        ),
        sa.Column("source_reference", sa.String(255), nullable=True),
        sa.Column("generator_version", sa.String(50), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        # Legacy traceability
        sa.Column("legacy_test_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Authorship
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint(
            "project_id", "test_code", name="uq_project_test_code"
        ),
    )
    op.create_index(
        "idx_g2_test_defs_suite", "g2_test_definitions", ["suite_id"]
    )
    op.create_index(
        "idx_g2_test_defs_project", "g2_test_definitions", ["project_id"]
    )
    op.create_index(
        "idx_g2_test_defs_legacy",
        "g2_test_definitions",
        ["legacy_test_case_id"],
        postgresql_where=sa.text("legacy_test_case_id IS NOT NULL"),
    )

    op.create_table(
        "g2_test_definition_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "test_definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preconditions", sa.Text(), nullable=True),
        sa.Column("postconditions", sa.Text(), nullable=True),
        sa.Column(
            "estimated_duration_s",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
        sa.Column("adapter_type", sa.String(50), nullable=False),
        sa.Column(
            "specification",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("change_reason", sa.String(255), nullable=True),
        sa.Column(
            "is_approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        # Migration provenance columns
        sa.Column("migration_status", sa.String(30), nullable=True),
        sa.Column("migration_notes", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "test_definition_id",
            "version_number",
            name="uq_test_def_version",
        ),
    )
    op.create_index(
        "idx_g2_def_versions_def",
        "g2_test_definition_versions",
        ["test_definition_id"],
    )

    # Deferred FK: g2_test_definitions.current_version_id → g2_test_definition_versions.id
    op.create_foreign_key(
        "fk_test_def_current_version",
        "g2_test_definitions",
        "g2_test_definition_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "g2_test_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "definition_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_definition_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("test_data", sa.Text(), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=False),
        sa.Column(
            "is_shared_step",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.UniqueConstraint(
            "definition_version_id",
            "step_number",
            name="uq_version_step",
        ),
    )
    op.create_index(
        "idx_g2_steps_version", "g2_test_steps", ["definition_version_id"]
    )

    # -------------------------------------------------------------------------
    # 7. REQUIREMENT LINKS (version-level traceability — Fix #1 from contract)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_requirement_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # Current-state identifiers (fast lookup)
        sa.Column(
            "requirement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_requirements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Version-level identifiers (authoritative historical anchor)
        sa.Column(
            "requirement_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_requirement_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "definition_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_definition_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "coverage_type",
            sa.String(30),
            nullable=False,
            server_default="DIRECT_VERIFICATION",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint(
            "requirement_id",
            "test_definition_id",
            name="uq_req_test_link",
        ),
    )
    op.create_index(
        "idx_g2_req_links_req", "g2_requirement_links", ["requirement_id"]
    )
    op.create_index(
        "idx_g2_req_links_def",
        "g2_requirement_links",
        ["test_definition_id"],
    )

    # -------------------------------------------------------------------------
    # 8. TEST PLANS + MEMBERSHIP TABLES (Fix #3 from contract)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_test_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("entry_criteria", sa.Text(), nullable=True),
        sa.Column("exit_criteria", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("target_release", sa.String(100), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
    )
    op.create_index(
        "idx_g2_test_plans_project", "g2_test_plans", ["project_id"]
    )

    op.create_table(
        "g2_test_plan_suites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "test_plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "suite_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_suites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "include_children",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "order_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.UniqueConstraint("test_plan_id", "suite_id", name="uq_plan_suite"),
    )

    op.create_table(
        "g2_test_cycles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "test_plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "environment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_environments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "build_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_builds.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="PLANNED",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
    )
    op.create_index(
        "idx_g2_test_cycles_plan", "g2_test_cycles", ["test_plan_id"]
    )

    op.create_table(
        "g2_test_cycle_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cycle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_cycles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "definition_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_definition_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "selection_source",
            sa.String(30),
            nullable=False,
            server_default="MANUAL",
        ),
        sa.Column(
            "order_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.UniqueConstraint(
            "cycle_id",
            "test_definition_id",
            name="uq_cycle_definition",
        ),
    )
    op.create_index(
        "idx_g2_cycle_defs_cycle", "g2_test_cycle_definitions", ["cycle_id"]
    )

    # -------------------------------------------------------------------------
    # 9. EXECUTION JOBS (fenced, idempotent, with lease token)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_execution_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_cycle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_cycles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
        # Distributed fencing columns (prevents dual-execution)
        sa.Column("worker_id", sa.String(100), nullable=True),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "lease_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "max_retries",
            sa.Integer(),
            nullable=False,
            server_default="2",
        ),
        # Statistics
        sa.Column(
            "total_tests",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "passed_tests",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "failed_tests",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "error_tests",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "blocked_tests",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "skipped_tests",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        # Selection context snapshot (records WHY these tests ran — Fix #20)
        sa.Column(
            "execution_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default="3600",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        # Manual session extensions
        sa.Column(
            "session_state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resume_token", sa.String(128), nullable=True),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_project_idempotency",
        ),
    )
    op.create_index(
        "idx_g2_jobs_status_lease",
        "g2_execution_jobs",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "idx_g2_jobs_cycle", "g2_execution_jobs", ["test_cycle_id"]
    )
    op.create_index(
        "idx_g2_jobs_project", "g2_execution_jobs", ["project_id"]
    )

    # -------------------------------------------------------------------------
    # 10. EXECUTION ATTEMPTS (Build + Environment FKs — Fix #7 from contract)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_execution_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_execution_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "definition_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "g2_test_definition_versions.id", ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        sa.Column(
            "environment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_environments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "build_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_builds.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="RUNNING",
        ),
        # Full execution provenance
        sa.Column("engine_version", sa.String(50), nullable=True),
        sa.Column("adapter_version", sa.String(50), nullable=True),
        sa.Column("execution_config_hash", sa.String(64), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "duration_ms",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.UniqueConstraint(
            "job_id",
            "definition_version_id",
            "attempt_number",
            name="uq_job_version_attempt",
        ),
    )
    op.create_index(
        "idx_g2_attempts_job", "g2_execution_attempts", ["job_id"]
    )
    op.create_index(
        "idx_g2_attempts_def_version",
        "g2_execution_attempts",
        ["definition_version_id"],
    )

    # -------------------------------------------------------------------------
    # 11. CANONICAL TEST RESULTS (rich normalized — preserves Gen 1 telemetry)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_test_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_execution_attempts.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("outcome", sa.String(30), nullable=False),
        # Structured normalized data
        sa.Column(
            "step_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "assertion_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        # Gen 1 HTTP telemetry preserved
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("http_method", sa.String(20), nullable=True),
        sa.Column("http_path", sa.String(500), nullable=True),
        sa.Column(
            "response_body_truncated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        # Diagnostics
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column(
            "execution_time_ms",
            sa.Float(),
            nullable=False,
        ),
        # Gen 1 fingerprint + SBFL attribution preserved
        sa.Column("deterministic_fingerprint", sa.String(64), nullable=True),
        sa.Column(
            "is_flaky",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        # Adapter-specific raw output
        sa.Column(
            "adapter_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        # Full provenance snapshot
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
    )
    op.create_index(
        "idx_g2_results_fingerprint",
        "g2_test_results",
        ["deterministic_fingerprint"],
        postgresql_where=sa.text("deterministic_fingerprint IS NOT NULL"),
    )
    op.create_index(
        "idx_g2_results_outcome", "g2_test_results", ["outcome"]
    )
    op.create_index(
        "idx_g2_results_attempt", "g2_test_results", ["attempt_id"]
    )

    # -------------------------------------------------------------------------
    # 12. ARTIFACTS (object-storage backed)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "test_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column(
            "storage_backend",
            sa.String(50),
            nullable=False,
            server_default="LOCAL",
        ),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column(
            "retention_class",
            sa.String(30),
            nullable=False,
            server_default="STANDARD",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
    )
    op.create_index(
        "idx_g2_artifacts_result", "g2_artifacts", ["test_result_id"]
    )

    # -------------------------------------------------------------------------
    # 13. DEFECTS + DEFECT OCCURRENCES + DEFECT HISTORY (Fix #15 from contract)
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_defects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("defect_key", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            server_default="MAJOR",
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default="P2",
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="NEW",
        ),
        sa.Column("fingerprint", sa.String(64), nullable=True),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source",
            sa.String(30),
            nullable=False,
            server_default="MANUAL",
        ),
        sa.Column("external_issue_tracker", sa.String(50), nullable=True),
        sa.Column("external_issue_id", sa.String(100), nullable=True),
        sa.Column("external_issue_url", sa.String(500), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint(
            "project_id", "defect_key", name="uq_project_defect_key"
        ),
    )
    op.create_index(
        "idx_g2_defects_project", "g2_defects", ["project_id"]
    )
    op.create_index(
        "idx_g2_defects_fingerprint",
        "g2_defects",
        ["fingerprint"],
        postgresql_where=sa.text("fingerprint IS NOT NULL"),
    )

    op.create_table(
        "g2_defect_occurrences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "defect_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_defects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_test_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.UniqueConstraint(
            "defect_id", "test_result_id", name="uq_defect_test_result"
        ),
    )

    # Append-only audit trail for defect status transitions
    op.create_table(
        "g2_defect_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "defect_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_defects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(30), nullable=False),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column(
            "changed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
    )
    op.create_index(
        "idx_g2_defect_history_defect", "g2_defect_history", ["defect_id"]
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("g2_defect_history")
    op.drop_table("g2_defect_occurrences")
    op.drop_table("g2_defects")
    op.drop_table("g2_artifacts")
    op.drop_index("idx_g2_results_attempt", table_name="g2_test_results")
    op.drop_index("idx_g2_results_outcome", table_name="g2_test_results")
    op.drop_index(
        "idx_g2_results_fingerprint", table_name="g2_test_results"
    )
    op.drop_table("g2_test_results")
    op.drop_table("g2_execution_attempts")
    op.drop_index("idx_g2_jobs_project", table_name="g2_execution_jobs")
    op.drop_index("idx_g2_jobs_cycle", table_name="g2_execution_jobs")
    op.drop_index(
        "idx_g2_jobs_status_lease", table_name="g2_execution_jobs"
    )
    op.drop_table("g2_execution_jobs")
    op.drop_table("g2_test_cycle_definitions")
    op.drop_table("g2_test_cycles")
    op.drop_table("g2_test_plan_suites")
    op.drop_table("g2_test_plans")
    op.drop_table("g2_requirement_links")
    op.drop_table("g2_test_steps")
    op.drop_constraint(
        "fk_test_def_current_version",
        "g2_test_definitions",
        type_="foreignkey",
    )
    op.drop_table("g2_test_definition_versions")
    op.drop_index("idx_g2_test_defs_legacy", table_name="g2_test_definitions")
    op.drop_index(
        "idx_g2_test_defs_project", table_name="g2_test_definitions"
    )
    op.drop_index("idx_g2_test_defs_suite", table_name="g2_test_definitions")
    op.drop_table("g2_test_definitions")
    op.drop_table("g2_test_suites")
    op.drop_table("g2_environments")
    op.drop_index(
        "idx_builds_project_commit", table_name="g2_builds"
    )
    op.drop_index("idx_builds_project_version", table_name="g2_builds")
    op.drop_table("g2_builds")
    op.drop_constraint(
        "fk_req_current_version",
        "g2_requirements",
        type_="foreignkey",
    )
    op.drop_table("g2_requirement_versions")
    op.drop_table("g2_requirements")
    op.drop_index("idx_projects_workspace_id", table_name="projects")
    op.drop_column("projects", "actor_type")
    op.drop_column("projects", "workspace_id")
    op.drop_table("workspaces")
