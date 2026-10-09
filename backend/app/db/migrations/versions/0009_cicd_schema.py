"""Alembic Migration 0009: Webhook Events, CI Pipeline Runs & Notification Channels.

Revision ID: 0009_cicd_schema
Revises: 0008_regression_schema
Create Date: 2026-10-09 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_cicd_schema"
down_revision = "0008_regression_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. webhook_events
    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("provider", sa.String(20), nullable=False, server_default="GITHUB"),
        sa.Column("delivery_id", sa.String(100), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("signature_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sender", sa.String(100), nullable=True),
        sa.Column("payload_redacted", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("processing_status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "delivery_id", name="uq_provider_delivery_id"),
    )

    # 2. ci_pipeline_runs
    op.create_table(
        "ci_pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("regression_analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regression_analyses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("webhook_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("webhook_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("git_provider", sa.String(20), nullable=False, server_default="GITHUB"),
        sa.Column("repository_full_name", sa.String(255), nullable=False, index=True),
        sa.Column("pr_number", sa.Integer(), nullable=True, index=True),
        sa.Column("base_commit", sa.String(64), nullable=False),
        sa.Column("target_commit", sa.String(64), nullable=False),
        sa.Column("branch", sa.String(100), nullable=True),
        sa.Column("pipeline_status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("quality_gate_status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("github_check_run_id", sa.String(100), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. notification_channels
    op.create_table(
        "notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("channel_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("encrypted_target_url", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("events_filter", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. notification_deliveries
    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ci_pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_type", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("notification_deliveries")
    op.drop_table("notification_channels")
    op.drop_table("ci_pipeline_runs")
    op.drop_table("webhook_events")
