"""015 moderation reports and content masking

Revision ID: 015a109b31d9
Revises: 014a9c8f2b71
Create Date: 2026-11-17 16:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '015a109b31d9'
down_revision: Union[str, None] = '014a9c8f2b71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Content masking flags on posts and reels
    op.add_column('posts', sa.Column('is_hidden', sa.Boolean(), server_default='false', nullable=False))
    op.create_index(op.f('ix_posts_is_hidden'), 'posts', ['is_hidden'], unique=False)

    op.add_column('reels', sa.Column('is_hidden', sa.Boolean(), server_default='false', nullable=False))
    op.create_index(op.f('ix_reels_is_hidden'), 'reels', ['is_hidden'], unique=False)

    # 2. Expanded reporting targets (user, post, reel, comment)
    op.add_column('user_reports', sa.Column('target_type', sa.String(length=30), server_default='user', nullable=False))
    op.create_index(op.f('ix_user_reports_target_type'), 'user_reports', ['target_type'], unique=False)

    op.add_column('user_reports', sa.Column('post_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_user_reports_post_id',
        'user_reports', 'posts',
        ['post_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_user_reports_post_id'), 'user_reports', ['post_id'], unique=False)

    op.add_column('user_reports', sa.Column('reel_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_user_reports_reel_id',
        'user_reports', 'reels',
        ['reel_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_user_reports_reel_id'), 'user_reports', ['reel_id'], unique=False)

    op.alter_column('user_reports', 'reported_user_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column('user_reports', 'reported_user_id', existing_type=sa.Integer(), nullable=False)
    op.drop_constraint('fk_user_reports_reel_id', 'user_reports', type_='foreignkey')
    op.drop_index(op.f('ix_user_reports_reel_id'), table_name='user_reports')
    op.drop_column('user_reports', 'reel_id')

    op.drop_constraint('fk_user_reports_post_id', 'user_reports', type_='foreignkey')
    op.drop_index(op.f('ix_user_reports_post_id'), table_name='user_reports')
    op.drop_column('user_reports', 'post_id')

    op.drop_index(op.f('ix_user_reports_target_type'), table_name='user_reports')
    op.drop_column('user_reports', 'target_type')

    op.drop_index(op.f('ix_reels_is_hidden'), table_name='reels')
    op.drop_column('reels', 'is_hidden')

    op.drop_index(op.f('ix_posts_is_hidden'), table_name='posts')
    op.drop_column('posts', 'is_hidden')
