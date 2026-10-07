"""0004_generation_job_schema

Revision ID: 0004_generation_job_schema
Revises: 0003_test_execution_schema
Create Date: 2026-10-07 18:22:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004_generation_job_schema'
down_revision: Union[str, None] = '0003_test_execution_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enum
    generation_job_status = postgresql.ENUM(
        'PENDING', 'RUNNING', 'CANCELLED', 'COMPLETED', 'FAILED',
        name='generationjobstatus'
    )
    generation_job_status.create(op.get_bind(), checkfirst=True)

    # 2. Create Table
    op.create_table(
        'generation_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', postgresql.ENUM('PENDING', 'RUNNING', 'CANCELLED', 'COMPLETED', 'FAILED', name='generationjobstatus', create_type=False), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('configuration_hash', sa.String(length=64), nullable=False),
        sa.Column('seed', sa.Integer(), nullable=False, server_default='42'),
        sa.Column('total_candidates', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_deduplicated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_truncated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('generation_report', sa.JSON(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['project_analyses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generation_jobs_project_id'), 'generation_jobs', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_generation_jobs_project_id'), table_name='generation_jobs')
    op.drop_table('generation_jobs')
    op.execute("DROP TYPE IF EXISTS generationjobstatus")
