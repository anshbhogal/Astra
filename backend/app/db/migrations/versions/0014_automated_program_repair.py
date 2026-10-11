"""Gen 2 Phase 2 (Phase 12) — Automated Program Repair (APR) Schema

Creates canonical tables for repair jobs, candidate patches, isolated
verification runs, and autonomous pull requests.

Revision ID: 0014_automated_program_repair
Revises: 0013_canonical_constraints
Create Date: 2026-10-11 20:45:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014_automated_program_repair"
down_revision: Union[str, None] = "0013_canonical_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. G2_REPAIR_JOBS
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_repair_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "defect_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_defects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "source_build_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_builds.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_commit_sha", sa.String(64), nullable=False),
        sa.Column("base_branch", sa.String(100), server_default="main", nullable=False),
        sa.Column("status", sa.String(30), server_default="QUEUED", nullable=False),
        sa.Column("trigger_type", sa.String(20), server_default="AUTOMATIC", nullable=False),
        sa.Column("requested_by", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("engine_version", sa.String(30), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("selected_candidate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
    )
    op.create_index("idx_g2_repair_jobs_defect", "g2_repair_jobs", ["defect_id"])
    op.create_index("idx_g2_repair_jobs_project", "g2_repair_jobs", ["project_id"])
    op.create_index("idx_g2_repair_jobs_status", "g2_repair_jobs", ["status"])

    # -------------------------------------------------------------------------
    # 2. G2_REPAIR_CANDIDATES
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_repair_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repair_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_repair_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "defect_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_defects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("candidate_rank", sa.Integer(), server_default="1", nullable=False),
        sa.Column("generation_method", sa.String(30), nullable=False),
        sa.Column("mutator_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("prompt_hash", sa.String(64), nullable=True),
        sa.Column("response_hash", sa.String(64), nullable=True),
        sa.Column("base_commit_sha", sa.String(64), nullable=False),
        sa.Column("target_file", sa.String(500), nullable=False),
        sa.Column("target_ast_hash", sa.String(64), nullable=False),
        sa.Column("target_node_type", sa.String(50), nullable=False),
        sa.Column("patch_diff", sa.Text(), nullable=False),
        sa.Column("patch_sha256", sa.String(64), nullable=False),
        sa.Column("candidate_hash", sa.String(64), nullable=False),
        sa.Column("patch_scope", sa.String(20), server_default="SCOPE_2", nullable=False),
        sa.Column("changed_files_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("lines_added", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lines_removed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("complexity_delta", sa.Integer(), server_default="0", nullable=False),
        sa.Column("syntax_valid", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("policy_valid", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("ranking_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("status", sa.String(30), server_default="GENERATED", nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_g2_repair_candidates_job", "g2_repair_candidates", ["repair_job_id"])
    op.create_index("idx_g2_repair_candidates_defect", "g2_repair_candidates", ["defect_id"])
    op.create_index("idx_g2_repair_candidates_hash", "g2_repair_candidates", ["candidate_hash"])
    op.create_index("idx_g2_repair_candidates_status", "g2_repair_candidates", ["status"])

    # -------------------------------------------------------------------------
    # 3. G2_REPAIR_VERIFICATIONS
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_repair_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_repair_candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("verification_type", sa.String(30), nullable=False),
        sa.Column(
            "execution_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_execution_attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "build_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_builds.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(30), server_default="RUNNING", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tests_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tests_passed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tests_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tests_error", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tests_timeout", sa.Integer(), server_default="0", nullable=False),
        sa.Column("environment_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("log_artifact_path", sa.String(500), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
    )
    op.create_index("idx_g2_repair_verifications_candidate", "g2_repair_verifications", ["candidate_id"])
    op.create_index("idx_g2_repair_verifications_status", "g2_repair_verifications", ["status"])

    # -------------------------------------------------------------------------
    # 4. G2_REPAIR_PULL_REQUESTS
    # -------------------------------------------------------------------------
    op.create_table(
        "g2_repair_pull_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repair_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_repair_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "repair_candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_repair_candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "defect_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("g2_defects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("github_pr_number", sa.Integer(), nullable=False),
        sa.Column("github_pr_url", sa.String(500), nullable=False),
        sa.Column("branch_name", sa.String(255), nullable=False),
        sa.Column("base_branch", sa.String(100), server_default="main", nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.Column("signing_key_id", sa.String(64), nullable=True),
        sa.Column("pr_status", sa.String(30), server_default="OPEN", nullable=False),
        sa.Column("post_merge_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
    )
    op.create_index("idx_g2_repair_pr_defect", "g2_repair_pull_requests", ["defect_id"])
    op.create_index("idx_g2_repair_pr_job", "g2_repair_pull_requests", ["repair_job_id"])
    op.create_index("idx_g2_repair_pr_candidate", "g2_repair_pull_requests", ["repair_candidate_id"])


def downgrade() -> None:
    op.drop_table("g2_repair_pull_requests")
    op.drop_table("g2_repair_verifications")
    op.drop_table("g2_repair_candidates")
    op.drop_table("g2_repair_jobs")
