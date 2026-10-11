"""Gen 2 Legacy Compatibility Layer

Creates legacy_execution_map mapping table and compatibility views.
No data is moved or altered in this migration.

Revision ID: 0012_legacy_compatibility
Revises: 0011_canonical_schema
Create Date: 2026-10-11 18:30:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0012_legacy_compatibility"
down_revision: Union[str, None] = "0011_canonical_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # LEGACY EXECUTION MAP (Bidirectional Traceability)
    # -------------------------------------------------------------------------
    op.create_table(
        "legacy_execution_map",
        sa.Column(
            "legacy_test_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "legacy_test_case_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "legacy_test_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "canonical_test_definition_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "canonical_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "canonical_execution_job_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "canonical_execution_attempt_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "canonical_test_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "migration_status",
            sa.String(30),
            nullable=False,
            server_default="MIGRATED",
        ),
        sa.Column(
            "migration_notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "migrated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.PrimaryKeyConstraint(
            "legacy_test_run_id",
            "legacy_test_case_id",
            "legacy_test_result_id",
            name="pk_legacy_execution_map",
        ),
    )

    op.create_index(
        "idx_legacy_map_run",
        "legacy_execution_map",
        ["legacy_test_run_id"],
    )
    op.create_index(
        "idx_legacy_map_case",
        "legacy_execution_map",
        ["legacy_test_case_id"],
    )
    op.create_index(
        "idx_legacy_map_result",
        "legacy_execution_map",
        ["legacy_test_result_id"],
    )
    op.create_index(
        "idx_legacy_map_canonical_result",
        "legacy_execution_map",
        ["canonical_test_result_id"],
    )
    op.create_index(
        "idx_legacy_map_canonical_job",
        "legacy_execution_map",
        ["canonical_execution_job_id"],
    )
    op.create_index(
        "idx_legacy_map_status",
        "legacy_execution_map",
        ["migration_status"],
    )

    # -------------------------------------------------------------------------
    # COMPATIBILITY PROJECTION VIEWS
    # -------------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE VIEW v_canonical_legacy_runs AS
        SELECT
            j.id AS canonical_job_id,
            m.legacy_test_run_id,
            j.project_id,
            j.status,
            j.total_tests,
            j.passed_tests,
            j.failed_tests,
            j.error_tests,
            j.started_at,
            j.completed_at
        FROM g2_execution_jobs j
        LEFT JOIN (
            SELECT DISTINCT canonical_execution_job_id, legacy_test_run_id
            FROM legacy_execution_map
        ) m ON j.id = m.canonical_execution_job_id;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_canonical_legacy_runs;")
    op.drop_index("idx_legacy_map_status", table_name="legacy_execution_map")
    op.drop_index("idx_legacy_map_canonical_job", table_name="legacy_execution_map")
    op.drop_index("idx_legacy_map_canonical_result", table_name="legacy_execution_map")
    op.drop_index("idx_legacy_map_result", table_name="legacy_execution_map")
    op.drop_index("idx_legacy_map_case", table_name="legacy_execution_map")
    op.drop_index("idx_legacy_map_run", table_name="legacy_execution_map")
    op.drop_table("legacy_execution_map")
