"""Initial database schema for Users, Projects, and AuditLogs

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-03 15:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    user_role_enum = postgresql.ENUM('ADMIN', 'DEVELOPER', 'TESTER', 'VIEWER', name='userrole')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    framework_enum = postgresql.ENUM('PYTHON_FASTAPI', 'PYTHON_FLASK', 'NODE_EXPRESS', 'JAVA_SPRING', 'OTHER', name='languageframework')
    framework_enum.create(op.get_bind(), checkfirst=True)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'DEVELOPER', 'TESTER', 'VIEWER', name='userrole'), nullable=False, server_default='DEVELOPER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('repository_url', sa.String(500), nullable=False),
        sa.Column('default_branch', sa.String(100), nullable=False, server_default='main'),
        sa.Column('language_framework', sa.Enum('PYTHON_FASTAPI', 'PYTHON_FLASK', 'NODE_EXPRESS', 'JAVA_SPRING', 'OTHER', name='languageframework'), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=False)

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('projects')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS languageframework')
    op.execute('DROP TYPE IF EXISTS userrole')
