"""add scheduled tasks tables

Revision ID: cb01d9ad81d9
Revises: d7edf8282b68
Create Date: 2026-03-06 22:00:01.005874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cb01d9ad81d9'
down_revision: Union[str, Sequence[str], None] = 'd7edf8282b68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create scheduled_tasks table
    op.create_table(
        'scheduled_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_type', sa.String(length=20), nullable=False),
        sa.Column('task_name', sa.String(length=255), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('cron_expression', sa.String(length=100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('retry_interval_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='scheduled_tasks_pkey')
    )

    # Create indexes for scheduled_tasks
    op.create_index('ix_scheduled_tasks_id', 'scheduled_tasks', ['id'])
    op.create_index('ix_scheduled_tasks_is_enabled', 'scheduled_tasks', ['is_enabled'])
    op.create_index('ix_scheduled_tasks_task_type', 'scheduled_tasks', ['task_type'])
    op.create_index('idx_scheduled_tasks_type_target', 'scheduled_tasks', ['task_type', 'target_id'])

    # Create task_executions table
    op.create_table(
        'task_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('result_data', postgresql.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_retry', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('triggered_by', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ['task_id'],
            ['scheduled_tasks.id'],
            name='task_executions_task_id_fkey',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name='task_executions_pkey')
    )

    # Create indexes for task_executions
    op.create_index('ix_task_executions_id', 'task_executions', ['id'])
    op.create_index('ix_task_executions_started_at', 'task_executions', ['started_at'])
    op.create_index('ix_task_executions_status', 'task_executions', ['status'])
    op.create_index('ix_task_executions_task_id', 'task_executions', ['task_id'])
    op.create_index('idx_task_executions_task_status', 'task_executions', ['task_id', 'status'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop task_executions table and its indexes
    op.drop_index('idx_task_executions_task_status', table_name='task_executions')
    op.drop_index('ix_task_executions_task_id', table_name='task_executions')
    op.drop_index('ix_task_executions_status', table_name='task_executions')
    op.drop_index('ix_task_executions_started_at', table_name='task_executions')
    op.drop_index('ix_task_executions_id', table_name='task_executions')
    op.drop_table('task_executions')

    # Drop scheduled_tasks table and its indexes
    op.drop_index('idx_scheduled_tasks_type_target', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_task_type', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_is_enabled', table_name='scheduled_tasks')
    op.drop_index('ix_scheduled_tasks_id', table_name='scheduled_tasks')
    op.drop_table('scheduled_tasks')
