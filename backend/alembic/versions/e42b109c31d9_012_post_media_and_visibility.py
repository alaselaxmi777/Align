"""012 post media and visibility

Revision ID: e42b109c31d9
Revises: c31d953e4167
Create Date: 2026-11-17 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'e42b109c31d9'
down_revision: Union[str, None] = 'c31d953e4167'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to posts
    op.add_column('posts', sa.Column('visibility', sa.String(length=20), server_default='connections_only', nullable=False))
    op.add_column('posts', sa.Column('location_area', sa.String(length=120), nullable=True))
    op.add_column('posts', sa.Column('is_pinned', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('posts', sa.Column('embedding', Vector(dim=384), nullable=True))
    
    op.create_index(op.f('ix_posts_visibility'), 'posts', ['visibility'], unique=False)
    op.create_index(op.f('ix_posts_is_pinned'), 'posts', ['is_pinned'], unique=False)
    op.create_index(op.f('ix_posts_created_at'), 'posts', ['created_at'], unique=False)

    # 2. Create post_media table
    op.create_table(
        'post_media',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('media_type', sa.String(length=20), server_default='image', nullable=False),
        sa.Column('original_url', sa.String(length=500), nullable=False),
        sa.Column('feed_url', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('alt_text', sa.String(length=300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_post_media_id'), 'post_media', ['id'], unique=False)
    op.create_index(op.f('ix_post_media_post_id'), 'post_media', ['post_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_post_media_post_id'), table_name='post_media')
    op.drop_index(op.f('ix_post_media_id'), table_name='post_media')
    op.drop_table('post_media')

    op.drop_index(op.f('ix_posts_created_at'), table_name='posts')
    op.drop_index(op.f('ix_posts_is_pinned'), table_name='posts')
    op.drop_index(op.f('ix_posts_visibility'), table_name='posts')
    op.drop_column('posts', 'embedding')
    op.drop_column('posts', 'is_pinned')
    op.drop_column('posts', 'location_area')
    op.drop_column('posts', 'visibility')
