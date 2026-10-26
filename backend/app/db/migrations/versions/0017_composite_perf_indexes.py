"""Add composite indexes on high-frequency columns for query performance.

Revision ID: 0017_composite_perf_indexes
Revises: 0016_nullable_github_pr_fields
Create Date: 2026-10-26 10:55:00.000000
"""

from typing import Sequence, Union
from alembic import op


revision: str = "0017_composite_perf_indexes"
down_revision: Union[str, None] = "0016_nullable_github_pr_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_test_results_run_outcome",
        "test_results",
        ["test_run_id", "outcome"],
        unique=False,
    )
    op.create_index(
        "idx_test_runs_project_created",
        "test_runs",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_discovered_endpoints_analysis_method",
        "discovered_endpoints",
        ["analysis_id", "method"],
        unique=False,
    )
    op.create_index(
        "idx_audit_logs_action_created",
        "audit_logs",
        ["action", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_audit_logs_action_created", table_name="audit_logs")
    op.drop_index("idx_discovered_endpoints_analysis_method", table_name="discovered_endpoints")
    op.drop_index("idx_test_runs_project_created", table_name="test_runs")
    op.drop_index("idx_test_results_run_outcome", table_name="test_results")
