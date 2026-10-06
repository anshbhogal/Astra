"""Test execution schema for test suites, cases, runs, and results

Revision ID: 0003_test_execution_schema
Revises: 0002_project_analysis_schema
Create Date: 2026-10-06 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0003_test_execution_schema'
down_revision: Union[str, None] = '0002_project_analysis_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    test_run_status_enum = postgresql.ENUM('PENDING', 'STARTING', 'RUNNING', 'COMPLETED', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'ENVIRONMENT_ERROR', name='testrunstatus')
    test_run_status_enum.create(op.get_bind(), checkfirst=True)

    test_outcome_enum = postgresql.ENUM('PASS', 'FAIL', 'ERROR', 'TIMEOUT', 'SKIP', name='testoutcome')
    test_outcome_enum.create(op.get_bind(), checkfirst=True)

    test_type_enum = postgresql.ENUM('HAPPY_PATH', 'MISSING_REQUIRED', 'INVALID_TYPE', 'UNAUTHORIZED', 'INVALID_FORMAT', 'EMPTY_VALUE', 'NULL_VALUE', 'BOUNDARY', 'METHOD_NOT_ALLOWED', 'NOT_FOUND', name='testtype')
    test_type_enum.create(op.get_bind(), checkfirst=True)

    # Create test_suites table
    op.create_table(
        'test_suites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_analyses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('total_cases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.String(50), nullable=False, server_default='1.0.0'),
        sa.Column('is_immutable', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index(op.f('ix_test_suites_project_id'), 'test_suites', ['project_id'], unique=False)
    op.create_index(op.f('ix_test_suites_analysis_id'), 'test_suites', ['analysis_id'], unique=False)

    # Create test_cases table
    op.create_table(
        'test_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('suite_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_suites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('endpoint_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('discovered_endpoints.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('test_type', postgresql.ENUM('HAPPY_PATH', 'MISSING_REQUIRED', 'INVALID_TYPE', 'UNAUTHORIZED', 'INVALID_FORMAT', 'EMPTY_VALUE', 'NULL_VALUE', 'BOUNDARY', 'METHOD_NOT_ALLOWED', 'NOT_FOUND', name='testtype', create_type=False), nullable=False, server_default='HAPPY_PATH'),
        sa.Column('execution_order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('specification', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('depends_on', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index(op.f('ix_test_cases_suite_id'), 'test_cases', ['suite_id'], unique=False)

    # Create test_runs table
    op.create_table(
        'test_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('suite_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_suites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'STARTING', 'RUNNING', 'COMPLETED', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'ENVIRONMENT_ERROR', name='testrunstatus', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('total_tests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed_tests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_tests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_tests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('target_environment', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index(op.f('ix_test_runs_project_id'), 'test_runs', ['project_id'], unique=False)
    op.create_index(op.f('ix_test_runs_suite_id'), 'test_runs', ['suite_id'], unique=False)

    # Create test_results table
    op.create_table(
        'test_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('test_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('test_case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('endpoint', sa.String(500), nullable=False),
        sa.Column('method', sa.String(20), nullable=False),
        sa.Column('test_type', postgresql.ENUM('HAPPY_PATH', 'MISSING_REQUIRED', 'INVALID_TYPE', 'UNAUTHORIZED', 'INVALID_FORMAT', 'EMPTY_VALUE', 'NULL_VALUE', 'BOUNDARY', 'METHOD_NOT_ALLOWED', 'NOT_FOUND', name='testtype', create_type=False), nullable=False, server_default='HAPPY_PATH'),
        sa.Column('outcome', postgresql.ENUM('PASS', 'FAIL', 'ERROR', 'TIMEOUT', 'SKIP', name='testoutcome', create_type=False), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('request_data', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('response_body_truncated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('execution_time_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('assertion_failures', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index(op.f('ix_test_results_test_run_id'), 'test_results', ['test_run_id'], unique=False)
    op.create_index(op.f('ix_test_results_test_case_id'), 'test_results', ['test_case_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_test_results_test_case_id'), table_name='test_results')
    op.drop_index(op.f('ix_test_results_test_run_id'), table_name='test_results')
    op.drop_table('test_results')
    op.drop_index(op.f('ix_test_runs_suite_id'), table_name='test_runs')
    op.drop_index(op.f('ix_test_runs_project_id'), table_name='test_runs')
    op.drop_table('test_runs')
    op.drop_index(op.f('ix_test_cases_suite_id'), table_name='test_cases')
    op.drop_table('test_cases')
    op.drop_index(op.f('ix_test_suites_analysis_id'), table_name='test_suites')
    op.drop_index(op.f('ix_test_suites_project_id'), table_name='test_suites')
    op.drop_table('test_suites')
    op.execute('DROP TYPE IF EXISTS testtype')
    op.execute('DROP TYPE IF EXISTS testoutcome')
    op.execute('DROP TYPE IF EXISTS testrunstatus')
