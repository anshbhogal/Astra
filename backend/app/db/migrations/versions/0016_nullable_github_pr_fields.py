"""Make github_pr_number and github_pr_url nullable for local commits without remote PR.

Revision ID: 0016_nullable_github_pr_fields
Revises: 0015_user_token_version
Create Date: 2026-10-24 22:05:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0016_nullable_github_pr_fields"
down_revision: Union[str, None] = "0015_user_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "g2_repair_pull_requests",
        "github_pr_number",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "g2_repair_pull_requests",
        "github_pr_url",
        existing_type=sa.String(500),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "g2_repair_pull_requests",
        "github_pr_url",
        existing_type=sa.String(500),
        nullable=False,
    )
    op.alter_column(
        "g2_repair_pull_requests",
        "github_pr_number",
        existing_type=sa.Integer(),
        nullable=False,
    )
