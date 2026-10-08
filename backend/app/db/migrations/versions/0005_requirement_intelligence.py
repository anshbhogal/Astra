"""Alembic Migration 0005: Requirement Intelligence & AI Telemetry Tables.

Revision ID: 0005_requirement_intelligence
Revises: 0004_generation_job_schema
Create Date: 2026-10-08 19:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_requirement_intelligence"
down_revision = "0004_generation_job_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. requirement_documents
    op.create_table(
        "requirement_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)
    )

    # 2. requirement_specs
    op.create_table(
        "requirement_specs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requirement_documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("req_code", sa.String(100), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("req_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="EXTRACTED"),
        sa.Column("mapping_status", sa.String(50), nullable=False, server_default="UNMAPPED"),
        sa.Column("target_endpoints", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("business_rules", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)
    )

    # 3. llm_execution_records
    op.create_table(
        "llm_execution_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("generation_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("validation_status", sa.String(50), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)
    )


def downgrade() -> None:
    op.drop_table("llm_execution_records")
    op.drop_table("requirement_specs")
    op.drop_table("requirement_documents")
