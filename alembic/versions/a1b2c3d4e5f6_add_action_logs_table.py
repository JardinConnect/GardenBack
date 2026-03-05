"""add action_logs table

Revision ID: a1b2c3d4e5f6
Revises: b2fb672a07e8
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b2fb672a07e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'action_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('action_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_action_logs_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_action_logs_resource_type'), ['resource_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_action_logs_entity_id'), ['entity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_action_logs_created_at'), ['created_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('action_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_action_logs_created_at'))
        batch_op.drop_index(batch_op.f('ix_action_logs_entity_id'))
        batch_op.drop_index(batch_op.f('ix_action_logs_resource_type'))
        batch_op.drop_index(batch_op.f('ix_action_logs_user_id'))
    op.drop_table('action_logs')
