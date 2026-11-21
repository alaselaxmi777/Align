"""004_reels_and_indexes

Revision ID: a41f82c9e704
Revises: d91a27e8a301
Create Date: 2026-11-13 20:06:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a41f82c9e704'
down_revision: Union[str, Sequence[str], None] = 'd91a27e8a301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    # 1. Create reels table if not exists
    if 'reels' not in tables:
        op.create_table(
            'reels',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=150), nullable=False),
            sa.Column('category', sa.String(length=80), server_default='Technology', nullable=False),
            sa.Column('video_url', sa.String(length=500), nullable=False),
            sa.Column('thumbnail_url', sa.String(length=500), nullable=False),
            sa.Column('author_id', sa.Integer(), nullable=False),
            sa.Column('author_name', sa.String(length=120), nullable=False),
            sa.Column('author_avatar', sa.String(length=500), nullable=True),
            sa.Column('caption', sa.Text(), nullable=True),
            sa.Column('audio_track', sa.String(length=160), nullable=True),
            sa.Column('tags', sa.String(length=255), server_default='', nullable=False),
            sa.Column('views_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_reels_id'), 'reels', ['id'], unique=False)
        op.create_index(op.f('ix_reels_title'), 'reels', ['title'], unique=False)
        op.create_index(op.f('ix_reels_category'), 'reels', ['category'], unique=False)
        op.create_index(op.f('ix_reels_author_id'), 'reels', ['author_id'], unique=False)
        op.create_index(op.f('ix_reels_created_at'), 'reels', ['created_at'], unique=False)

    # 2. Create reel_likes table if not exists
    if 'reel_likes' not in tables:
        op.create_table(
            'reel_likes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('reel_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['reel_id'], ['reels.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('reel_id', 'user_id', name='uq_reel_user_like'),
        )
        op.create_index(op.f('ix_reel_likes_id'), 'reel_likes', ['id'], unique=False)
        op.create_index(op.f('ix_reel_likes_reel_id'), 'reel_likes', ['reel_id'], unique=False)
        op.create_index(op.f('ix_reel_likes_user_id'), 'reel_likes', ['user_id'], unique=False)

    # 3. Create reel_comments table if not exists
    if 'reel_comments' not in tables:
        op.create_table(
            'reel_comments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('reel_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['reel_id'], ['reels.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_reel_comments_id'), 'reel_comments', ['id'], unique=False)
        op.create_index(op.f('ix_reel_comments_reel_id'), 'reel_comments', ['reel_id'], unique=False)
        op.create_index(op.f('ix_reel_comments_user_id'), 'reel_comments', ['user_id'], unique=False)
        op.create_index(op.f('ix_reel_comments_created_at'), 'reel_comments', ['created_at'], unique=False)

    # 4. Add B-Tree indexes for previously unindexed foreign keys
    fk_indexes = [
        ('assistant_goal_journeys', 'linked_conversation_id', 'idx_asst_goal_journeys_conv_id'),
        ('assistant_memories', 'source_conversation_id', 'idx_asst_memories_src_conv_id'),
        ('assistant_messages', 'user_id', 'idx_asst_messages_user_id'),
        ('communities', 'created_by_id', 'idx_communities_created_by'),
        ('events', 'community_id', 'idx_events_community_id'),
        ('events', 'created_by_id', 'idx_events_created_by'),
        ('interest_circles', 'created_by_id', 'idx_interest_circles_created_by'),
        ('projects', 'created_by_id', 'idx_projects_created_by'),
    ]

    for tbl, col, idx_name in fk_indexes:
        if tbl in tables:
            existing_idx = [i['name'] for i in insp.get_indexes(tbl)]
            if idx_name not in existing_idx:
                op.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl} ({col})"))

    # 5. Add HNSW vector indexes for all 9 vector columns
    vector_tables = [
        ('places', 'idx_places_embedding_hnsw'),
        ('profiles', 'idx_profiles_embedding_hnsw'),
        ('communities', 'idx_communities_embedding_hnsw'),
        ('events', 'idx_events_embedding_hnsw'),
        ('interest_circles', 'idx_interest_circles_embedding_hnsw'),
        ('goal_journeys', 'idx_goal_journeys_embedding_hnsw'),
        ('projects', 'idx_projects_embedding_hnsw'),
        ('opportunities', 'idx_opportunities_embedding_hnsw'),
        ('assistant_memories', 'idx_asst_memories_embedding_hnsw'),
    ]

    for tbl, idx_name in vector_tables:
        if tbl in tables:
            cols = [c['name'] for c in insp.get_columns(tbl)]
            if 'embedding' in cols:
                op.execute(sa.text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl} USING hnsw (embedding vector_cosine_ops)"
                ))

def downgrade() -> None:
    # Drop vector indexes
    vector_indexes = [
        'idx_places_embedding_hnsw',
        'idx_profiles_embedding_hnsw',
        'idx_communities_embedding_hnsw',
        'idx_events_embedding_hnsw',
        'idx_interest_circles_embedding_hnsw',
        'idx_goal_journeys_embedding_hnsw',
        'idx_projects_embedding_hnsw',
        'idx_opportunities_embedding_hnsw',
        'idx_asst_memories_embedding_hnsw',
    ]
    for idx_name in vector_indexes:
        op.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))

    # Drop FK indexes
    fk_indexes = [
        'idx_asst_goal_journeys_conv_id',
        'idx_asst_memories_src_conv_id',
        'idx_asst_messages_user_id',
        'idx_communities_created_by',
        'idx_events_community_id',
        'idx_events_created_by',
        'idx_interest_circles_created_by',
        'idx_projects_created_by',
    ]
    for idx_name in fk_indexes:
        op.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))

    # Drop reel tables
    op.drop_table('reel_comments')
    op.drop_table('reel_likes')
    op.drop_table('reels')
