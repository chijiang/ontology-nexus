"""add_user_conversation_rules_tables

Revision ID: 8e8a5581c064
Revises: 872f0312eba0
Create Date: 2026-02-06 00:33:57.310751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8e8a5581c064'
down_revision: Union[str, Sequence[str], None] = '872f0312eba0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create user, conversation, LLM config, and rules tables."""

    # Use op.get_bind() to check if tables exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Helper to check if table exists
    def table_exists(name):
        return inspector.has_table(name)

    # Create users table
    if not table_exists('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('username', sa.String(length=50), nullable=False),
            sa.Column('password_hash', sa.String(length=255), nullable=False),
            sa.Column('email', sa.String(length=100), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('username')
        )

    # Create llm_configs table
    if not table_exists('llm_configs'):
        op.create_table(
            'llm_configs',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('api_key_encrypted', sa.String(length=500), nullable=False),
            sa.Column('base_url', sa.String(length=500), nullable=False),
            sa.Column('model', sa.String(length=100), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

    # Create conversations table
    if not table_exists('conversations'):
        op.create_table(
            'conversations',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=True, server_default='新对话'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])

    # Create messages table
    if not table_exists('messages'):
        op.create_table(
            'messages',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('conversation_id', sa.Integer(), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('extra_metadata', postgresql.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])

    # Create action_definitions table
    if not table_exists('action_definitions'):
        op.create_table(
            'action_definitions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('entity_type', sa.String(length=100), nullable=False),
            sa.Column('dsl_content', sa.Text(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_action_definitions_name', 'action_definitions', ['name'])
        op.create_index('ix_action_definitions_entity_type', 'action_definitions', ['entity_type'])

    # Create rules table
    if not table_exists('rules'):
        op.create_table(
            'rules',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('trigger_type', sa.String(length=20), nullable=False),
            sa.Column('trigger_entity', sa.String(length=100), nullable=False),
            sa.Column('trigger_property', sa.String(length=100), nullable=True),
            sa.Column('dsl_content', sa.Text(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index('ix_rules_name', 'rules', ['name'])
        op.create_index('ix_rules_trigger_entity', 'rules', ['trigger_entity'])


def downgrade() -> None:
    """Downgrade schema - Drop all user tables."""

    # Drop tables in reverse order due to foreign keys
    op.drop_index('ix_rules_trigger_entity', 'rules')
    op.drop_index('ix_rules_name', 'rules')
    op.drop_table('rules')

    op.drop_index('ix_action_definitions_entity_type', 'action_definitions')
    op.drop_index('ix_action_definitions_name', 'action_definitions')
    op.drop_table('action_definitions')

    op.drop_index('ix_messages_conversation_id', 'messages')
    op.drop_table('messages')

    op.drop_index('ix_conversations_user_id', 'conversations')
    op.drop_table('conversations')

    op.drop_table('llm_configs')
    op.drop_table('users')
