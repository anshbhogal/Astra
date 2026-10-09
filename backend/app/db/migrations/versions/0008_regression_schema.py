"""Alembic Migration 0008: Regression Engine, Change Manifests & Impact Analysis Tables.

Revision ID: 0008_regression_schema
Revises: 0007_ml_intelligence_schema
Create Date: 2026-10-09 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_regression_schema"
down_revision = "0007_ml_intelligence_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. regression_analyses
    op.create_table(
        "regression_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("analysis_fingerprint", sa.String(64), nullable=False, index=True),
        sa.Column("base_commit", sa.String(64), nullable=False),
        sa.Column("target_commit", sa.String(64), nullable=False),
        sa.Column("target_branch", sa.String(100), nullable=True),
        sa.Column("pkg_snapshot_version", sa.String(50), nullable=False, server_default="v1.0"),
        sa.Column("total_modified_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_modified_symbols", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_impacted_endpoints", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_suite_tests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selected_tier1_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deferred_tier2_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("test_reduction_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("estimated_time_avoided_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("impact_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("safety_expansion_triggered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("analysis_warnings", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. code_change_manifests
    op.create_table(
        "code_change_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("regression_analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regression_analyses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("old_path", sa.String(500), nullable=True),
        sa.Column("new_path", sa.String(500), nullable=False),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("rename_similarity", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("modified_lines", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("modified_symbols", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("change_category", sa.String(50), nullable=False, server_default="FUNCTION_MODIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. endpoint_impact_records
    op.create_table(
        "endpoint_impact_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("regression_analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regression_analyses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("endpoint_id", sa.String(255), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("impact_distance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("impact_type", sa.String(30), nullable=False, server_default="DIRECT"),
        sa.Column("impact_path_trace", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("dependency_edge_types", postgresql.JSON(astext_type=sa.Text()), nullable=False),
    )

    # 4. selective_execution_runs
    op.create_table(
        "selective_execution_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("regression_analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regression_analyses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("execution_tier", sa.String(30), nullable=False, server_default="TIER1_TARGETED"),
        sa.Column("selected_test_details", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("deferred_test_details", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("selection_recall", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("selection_precision", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("tier1_actual_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tier2_actual_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("selective_execution_runs")
    op.drop_table("endpoint_impact_records")
    op.drop_table("code_change_manifests")
    op.drop_table("regression_analyses")
