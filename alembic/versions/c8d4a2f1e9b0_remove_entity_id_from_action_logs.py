"""remove entity_id from action_logs

Revision ID: c8d4a2f1e9b0
Revises: 30fd9ecc4098
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d4a2f1e9b0"
down_revision: Union[str, Sequence[str], None] = "30fd9ecc4098"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("action_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_action_logs_entity_id"))
        batch_op.drop_column("entity_id")


def downgrade() -> None:
    with op.batch_alter_table("action_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("entity_id", sa.UUID(), nullable=True))
        batch_op.create_index(batch_op.f("ix_action_logs_entity_id"), ["entity_id"], unique=False)
