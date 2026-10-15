"""Add token_version to users table for session invalidation and JWT revocation.

Revision ID: 0015_user_token_version
Revises: 0014_automated_program_repair
Create Date: 2026-10-15 23:55:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0015_user_token_version"
down_revision: Union[str, None] = "0014_automated_program_repair"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1")
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
