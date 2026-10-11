"""Gen 2 Canonical Schema Constraints

Enforces NOT NULL constraints on projects and canonical tables
after successful backfill and invariant validation.

Revision ID: 0013_canonical_constraints
Revises: 0012_legacy_compatibility
Create Date: 2026-10-11 18:45:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0013_canonical_constraints"
down_revision: Union[str, None] = "0012_legacy_compatibility"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. ENFORCE PROJECTS WORKSPACE_ID NOT NULL
    # -------------------------------------------------------------------------
    op.alter_column(
        "projects",
        "workspace_id",
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # 2. ENFORCE TEST DEFINITIONS CURRENT_VERSION NOT NULL
    # -------------------------------------------------------------------------
    op.alter_column(
        "g2_test_definitions",
        "current_version_id",
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "g2_test_definitions",
        "current_version_id",
        nullable=True,
    )
    op.alter_column(
        "projects",
        "workspace_id",
        nullable=True,
    )
