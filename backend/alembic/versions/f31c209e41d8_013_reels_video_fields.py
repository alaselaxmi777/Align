"""013 reels video fields

Revision ID: f31c209e41d8
Revises: e42b109c31d9
Create Date: 2026-11-17 15:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'f31c209e41d8'
down_revision: Union[str, None] = 'e42b109c31d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('reels', sa.Column('duration_seconds', sa.Float(), nullable=True))
    op.add_column('reels', sa.Column('visibility', sa.String(length=20), server_default='public', nullable=False))
    op.add_column('reels', sa.Column('is_test', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('reels', sa.Column('embedding', Vector(dim=384), nullable=True))

    op.create_index(op.f('ix_reels_visibility'), 'reels', ['visibility'], unique=False)
    op.create_index(op.f('ix_reels_is_test'), 'reels', ['is_test'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reels_is_test'), table_name='reels')
    op.drop_index(op.f('ix_reels_visibility'), table_name='reels')
    op.drop_column('reels', 'embedding')
    op.drop_column('reels', 'is_test')
    op.drop_column('reels', 'visibility')
    op.drop_column('reels', 'duration_seconds')
