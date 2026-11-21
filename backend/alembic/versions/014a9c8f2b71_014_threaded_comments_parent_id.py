"""014 threaded comments parent id

Revision ID: 014a9c8f2b71
Revises: f31c209e41d8
Create Date: 2026-11-17 15:58:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '014a9c8f2b71'
down_revision: Union[str, None] = 'f31c209e41d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('post_comments', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_post_comments_parent_id',
        'post_comments', 'post_comments',
        ['parent_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index(op.f('ix_post_comments_parent_id'), 'post_comments', ['parent_id'], unique=False)

    op.add_column('reel_comments', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_reel_comments_parent_id',
        'reel_comments', 'reel_comments',
        ['parent_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index(op.f('ix_reel_comments_parent_id'), 'reel_comments', ['parent_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reel_comments_parent_id'), table_name='reel_comments')
    op.drop_constraint('fk_reel_comments_parent_id', 'reel_comments', type_='foreignkey')
    op.drop_column('reel_comments', 'parent_id')

    op.drop_index(op.f('ix_post_comments_parent_id'), table_name='post_comments')
    op.drop_constraint('fk_post_comments_parent_id', 'post_comments', type_='foreignkey')
    op.drop_column('post_comments', 'parent_id')
