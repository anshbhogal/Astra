"""Alembic Migration 0006: Failure Analysis & Defect Cluster Tables.

Revision ID: 0006_failure_analysis_schema
Revises: 0005_requirement_intelligence
Create Date: 2026-10-08 23:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_failure_analysis_schema"
down_revision = "0005_requirement_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. failure_analyses
    op.create_table(
        "failure_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("test_result_id", sa.String(255), nullable=False, index=True),
        sa.Column("test_case_id", sa.String(255), nullable=False, index=True),
        sa.Column("endpoint_id", sa.String(255), nullable=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("exception_type", sa.String(255), nullable=True),
        sa.Column("failing_file", sa.String(500), nullable=True),
        sa.Column("failing_line", sa.Integer(), nullable=True),
        sa.Column("failing_function", sa.String(255), nullable=True),
        sa.Column("commit_sha", sa.String(64), nullable=True),
        sa.Column("source_mismatch", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("evidence", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("fault_locations", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("root_cause_candidates", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("diff_items", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("parsed_exception", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, index=True),
        sa.Column("classification_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("attribution_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("root_cause_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. defect_clusters
    op.create_table(
        "defect_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, index=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("representative_failure_id", sa.String(255), nullable=False),
        sa.Column("member_failure_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("match_precision", sa.String(50), nullable=False, server_default="EXACT_MATCH"),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_run_id", sa.String(255), nullable=True),
        sa.Column("last_seen_run_id", sa.String(255), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_intermittent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("defect_clusters")
    op.drop_table("failure_analyses")
