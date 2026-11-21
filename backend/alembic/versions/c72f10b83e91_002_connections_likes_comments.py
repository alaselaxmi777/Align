"""002_connections_likes_comments

Revision ID: c72f10b83e91
Revises: be3b49f27e88
Create Date: 2026-11-03 14:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c72f10b83e91'
down_revision: Union[str, Sequence[str], None] = 'be3b49f27e88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create user_connections table
    op.create_table(
        'user_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('receiver_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['receiver_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sender_id', 'receiver_id', name='uq_user_connection_pair')
    )
    op.create_index(op.f('ix_user_connections_id'), 'user_connections', ['id'], unique=False)
    op.create_index(op.f('ix_user_connections_receiver_id'), 'user_connections', ['receiver_id'], unique=False)
    op.create_index(op.f('ix_user_connections_sender_id'), 'user_connections', ['sender_id'], unique=False)
    op.create_index(op.f('ix_user_connections_status'), 'user_connections', ['status'], unique=False)

    # 2. Create post_likes table
    op.create_table(
        'post_likes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'user_id', name='uq_post_user_like')
    )
    op.create_index(op.f('ix_post_likes_id'), 'post_likes', ['id'], unique=False)
    op.create_index(op.f('ix_post_likes_post_id'), 'post_likes', ['post_id'], unique=False)
    op.create_index(op.f('ix_post_likes_user_id'), 'post_likes', ['user_id'], unique=False)

    # 3. Create post_comments table
    op.create_table(
        'post_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_post_comments_author_id'), 'post_comments', ['author_id'], unique=False)
    op.create_index(op.f('ix_post_comments_id'), 'post_comments', ['id'], unique=False)
    op.create_index(op.f('ix_post_comments_post_id'), 'post_comments', ['post_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_post_comments_post_id'), table_name='post_comments')
    op.drop_index(op.f('ix_post_comments_id'), table_name='post_comments')
    op.drop_index(op.f('ix_post_comments_author_id'), table_name='post_comments')
    op.drop_table('post_comments')

    op.drop_index(op.f('ix_post_likes_user_id'), table_name='post_likes')
    op.drop_index(op.f('ix_post_likes_post_id'), table_name='post_likes')
    op.drop_index(op.f('ix_post_likes_id'), table_name='post_likes')
    op.drop_table('post_likes')

    op.drop_index(op.f('ix_user_connections_status'), table_name='user_connections')
    op.drop_index(op.f('ix_user_connections_sender_id'), table_name='user_connections')
    op.drop_index(op.f('ix_user_connections_receiver_id'), table_name='user_connections')
    op.drop_index(op.f('ix_user_connections_id'), table_name='user_connections')
    op.drop_table('user_connections')
