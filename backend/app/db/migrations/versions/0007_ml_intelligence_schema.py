"""Alembic Migration 0007: ML Intelligence, Flakiness & Healing Tables.

Revision ID: 0007_ml_intelligence_schema
Revises: 0006_failure_analysis_schema
Create Date: 2026-10-09 09:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_ml_intelligence_schema"
down_revision = "0006_failure_analysis_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. ml_model_artifacts
    op.create_table(
        "ml_model_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("dataset_version", sa.String(50), nullable=False, server_default="v1.0"),
        sa.Column("algorithm", sa.String(50), nullable=False, server_default="XGBClassifier"),
        sa.Column("hyperparameters", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("training_commit_sha", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. flaky_test_records
    op.create_table(
        "flaky_test_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("flakiness_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("observation_window", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("transition_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pass_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_mean_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("latency_std_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. test_priority_rankings
    op.create_table(
        "test_priority_rankings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("failure_probability", sa.Float(), nullable=False),
        sa.Column("execution_cost_ms", sa.Float(), nullable=False),
        sa.Column("severity_weight", sa.Float(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("rank_order", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(50), nullable=False, server_default="BALANCED"),
        sa.Column("rationale", sa.String(500), nullable=True),
    )

    # 4. healing_candidates
    op.create_table(
        "healing_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("failure_analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("failure_analyses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_specification", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("proposed_specification", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("patch_operations", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resulting_spec_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rollback_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. ml_action_audit_logs
    op.create_table(
        "ml_action_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("details", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ml_action_audit_logs")
    op.drop_table("healing_candidates")
    op.drop_table("test_priority_rankings")
    op.drop_table("flaky_test_records")
    op.drop_table("ml_model_artifacts")
