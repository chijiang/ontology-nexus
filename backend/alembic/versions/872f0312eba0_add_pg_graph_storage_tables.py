"""add_pg_graph_storage_tables

Revision ID: 872f0312eba0
Revises: def036ff4583
Create Date: 2026-02-05 23:59:47.781288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '872f0312eba0'
down_revision: Union[str, Sequence[str], None] = 'def036ff4583'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create PostgreSQL graph storage tables."""

    # Create schema_classes table
    op.create_table(
        'schema_classes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('label', sa.String(length=500), nullable=True),
        sa.Column('data_properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create schema_relationships table
    op.create_table(
        'schema_relationships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_class_id', sa.Integer(), nullable=False),
        sa.Column('target_class_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['source_class_id'], ['schema_classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_class_id'], ['schema_classes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_class_id', 'target_class_id', 'relationship_type', name='uq_source_class_id_target_class_id_relationship_type')
    )

    # Create graph_entities table
    op.create_table(
        'graph_entities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('entity_type', sa.String(length=255), nullable=False),
        sa.Column('is_instance', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('uri', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for graph_entities
    op.create_index('idx_entities_name', 'graph_entities', ['name'])
    op.create_index('idx_entities_type', 'graph_entities', ['entity_type'])
    op.create_index('idx_entities_is_instance', 'graph_entities', ['is_instance'])
    op.create_index('idx_entities_type_instance', 'graph_entities', ['entity_type', 'is_instance'])

    # Create graph_relationships table
    op.create_table(
        'graph_relationships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(length=255), nullable=False),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['graph_entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_id'], ['graph_entities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'target_id', 'relationship_type', name='uq_source_id_target_id_relationship_type')
    )

    # Create indexes for graph_relationships
    op.create_index('idx_relationships_source', 'graph_relationships', ['source_id'])
    op.create_index('idx_relationships_target', 'graph_relationships', ['target_id'])
    op.create_index('idx_relationships_type', 'graph_relationships', ['relationship_type'])
    op.create_index('idx_relationships_source_target', 'graph_relationships', ['source_id', 'target_id'])
    op.create_index('idx_relationships_composite', 'graph_relationships', ['source_id', 'relationship_type', 'target_id'])


def downgrade() -> None:
    """Downgrade schema - Drop PostgreSQL graph storage tables."""

    # Drop indexes first
    op.drop_index('idx_relationships_composite', 'graph_relationships')
    op.drop_index('idx_relationships_source_target', 'graph_relationships')
    op.drop_index('idx_relationships_type', 'graph_relationships')
    op.drop_index('idx_relationships_target', 'graph_relationships')
    op.drop_index('idx_relationships_source', 'graph_relationships')

    # Drop tables
    op.drop_table('graph_relationships')

    op.drop_index('idx_entities_type_instance', 'graph_entities')
    op.drop_index('idx_entities_is_instance', 'graph_entities')
    op.drop_index('idx_entities_type', 'graph_entities')
    op.drop_index('idx_entities_name', 'graph_entities')

    op.drop_table('graph_entities')
    op.drop_table('schema_relationships')
    op.drop_table('schema_classes')
