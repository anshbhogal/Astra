"""Project analysis and discovered endpoints schema

Revision ID: 0002_project_analysis_schema
Revises: 0001_initial_schema
Create Date: 2026-10-05 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002_project_analysis_schema'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    analysis_status_enum = postgresql.ENUM('QUEUED', 'RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', 'FAILED', 'CANCELLED', name='analysisstatus')
    analysis_status_enum.create(op.get_bind(), checkfirst=True)

    analysis_stage_enum = postgresql.ENUM('CLONING', 'SCANNING', 'AST_PARSING', 'GRAPH_BUILDING', 'PERSISTING', 'FINISHED', name='analysisstage')
    analysis_stage_enum.create(op.get_bind(), checkfirst=True)

    # Create project_analyses table
    op.create_table(
        'project_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', 'FAILED', 'CANCELLED', name='analysisstatus', create_type=False), nullable=False, server_default='QUEUED'),
        sa.Column('current_stage', sa.Enum('CLONING', 'SCANNING', 'AST_PARSING', 'GRAPH_BUILDING', 'PERSISTING', 'FINISHED', name='analysisstage', create_type=False), nullable=False, server_default='CLONING'),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('repository_url', sa.String(500), nullable=False),
        sa.Column('branch', sa.String(100), nullable=False, server_default='main'),
        sa.Column('commit_sha', sa.String(100), nullable=True),
        sa.Column('detected_language', sa.String(50), nullable=True),
        sa.Column('detected_framework', sa.String(50), nullable=True),
        sa.Column('framework_confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('scanned_files_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parsed_files_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('endpoint_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('graph_node_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('graph_edge_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('knowledge_graph', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('analyzer_version', sa.String(50), nullable=False, server_default='2.0.0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index(op.f('ix_project_analyses_project_id'), 'project_analyses', ['project_id'], unique=False)

    # Create discovered_endpoints table
    op.create_table(
        'discovered_endpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('method', sa.String(20), nullable=False),
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('function_name', sa.String(255), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('request_model', sa.String(255), nullable=True),
        sa.Column('response_model', sa.String(255), nullable=True),
        sa.Column('framework', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index(op.f('ix_discovered_endpoints_analysis_id'), 'discovered_endpoints', ['analysis_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_discovered_endpoints_analysis_id'), table_name='discovered_endpoints')
    op.drop_table('discovered_endpoints')
    op.drop_index(op.f('ix_project_analyses_project_id'), table_name='project_analyses')
    op.drop_table('project_analyses')
    op.execute('DROP TYPE IF EXISTS analysisstage')
    op.execute('DROP TYPE IF EXISTS analysisstatus')
