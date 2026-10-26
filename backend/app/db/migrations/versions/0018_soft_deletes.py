"""Add is_deleted and deleted_at soft delete columns to users and projects.

Revision ID: 0018_soft_deletes
Revises: 0017_composite_perf_indexes
Create Date: 2026-10-26 11:10:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0018_soft_deletes"
down_revision: Union[str, None] = "0017_composite_perf_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "projects",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "deleted_at")
    op.drop_column("projects", "is_deleted")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "is_deleted")
