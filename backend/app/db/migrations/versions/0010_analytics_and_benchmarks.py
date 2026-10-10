"""Alembic Migration 0010: Benchmark Runs, Bug Results & Quality Reports.

Revision ID: 0010_analytics_and_benchmarks
Revises: 0009_cicd_schema
Create Date: 2026-10-10 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_analytics_and_benchmarks"
down_revision = "0009_cicd_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. benchmark_runs
    op.create_table(
        "benchmark_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mode", sa.String(30), nullable=False),
        sa.Column("benchmark_version", sa.String(30), nullable=False, server_default="1.0.0"),
        sa.Column("catalog_version", sa.String(30), nullable=False, server_default="50-bugs-v1"),
        sa.Column("oracle_version", sa.String(30), nullable=False, server_default="oracle-v1.0"),
        sa.Column("astra_commit_sha", sa.String(64), nullable=False, server_default="HEAD"),
        sa.Column("seed", sa.Integer(), nullable=False, server_default="42"),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("total_injected_bugs", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("true_positives", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("false_positives", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("true_negatives", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("false_negatives", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recall", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("precision", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("specificity", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("f1_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("false_positive_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("weighted_recall", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("category_coverage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tests_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tests_executed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detection_efficiency", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("time_efficiency", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("generation_time_s", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("execution_time_s", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("offline_resilient", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("repetition_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("summary_metrics", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. benchmark_bug_results
    op.create_table(
        "benchmark_bug_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("benchmark_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("bug_id", sa.String(50), nullable=False),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("is_triggered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_attributed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("attribution_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("test_case_name", sa.String(255), nullable=True),
        sa.Column("expected_status", sa.Integer(), nullable=True),
        sa.Column("actual_status", sa.Integer(), nullable=True),
        sa.Column("detection_method", sa.String(100), nullable=True),
        sa.Column("evidence", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("execution_time_ms", sa.Float(), nullable=False, server_default="0.0"),
    )

    # 3. quality_reports
    op.create_table(
        "quality_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False, server_default="EXECUTIVE_QUALITY_AUDIT"),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("summary_metrics", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("quality_reports")
    op.drop_table("benchmark_bug_results")
    op.drop_table("benchmark_runs")
