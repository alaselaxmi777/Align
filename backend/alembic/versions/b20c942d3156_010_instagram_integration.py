"""010_instagram_integration

Revision ID: b20c942d3156
Revises: a19b831c2045
Create Date: 2026-11-17 12:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = 'b20c942d3156'
down_revision: Union[str, Sequence[str], None] = 'a19b831c2045'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing_tables = insp.get_table_names()

    # 1. Update profiles table with Instagram settings
    if 'profiles' in existing_tables:
        profile_cols = [c['name'] for c in insp.get_columns('profiles')]
        if 'instagram_recommendations_enabled' not in profile_cols:
            op.add_column(
                'profiles',
                sa.Column('instagram_recommendations_enabled', sa.Boolean(), server_default='false', nullable=False)
            )
        if 'instagram_profile_visible' not in profile_cols:
            op.add_column(
                'profiles',
                sa.Column('instagram_profile_visible', sa.Boolean(), server_default='false', nullable=False)
            )

    # 2. Create instagram_accounts table
    if 'instagram_accounts' not in existing_tables:
        op.create_table(
            'instagram_accounts',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True, nullable=False),
            sa.Column('instagram_user_id', sa.String(length=120), index=True, nullable=True),
            sa.Column('username', sa.String(length=120), nullable=True),
            sa.Column('account_type', sa.String(length=60), nullable=True),
            sa.Column('access_token_encrypted', sa.Text(), nullable=False),
            sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('connected_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('status', sa.String(length=40), server_default='connected', nullable=False),
        )

    # 3. Create instagram_media table
    if 'instagram_media' not in existing_tables:
        op.create_table(
            'instagram_media',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),
            sa.Column('account_id', sa.Integer(), sa.ForeignKey('instagram_accounts.id', ondelete='CASCADE'), nullable=True),
            sa.Column('instagram_media_id', sa.String(length=120), unique=True, index=True, nullable=False),
            sa.Column('media_type', sa.String(length=50), server_default='IMAGE', nullable=False),
            sa.Column('media_url', sa.Text(), nullable=False),
            sa.Column('permalink', sa.String(length=500), nullable=False),
            sa.Column('caption', sa.Text(), nullable=True),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
            sa.Column('hashtags', sa.Text(), server_default='', nullable=False),
            sa.Column('embedding', Vector(384), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 4. Create suggested_interests table
    if 'suggested_interests' not in existing_tables:
        op.create_table(
            'suggested_interests',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False),
            sa.Column('interest', sa.String(length=120), nullable=False),
            sa.Column('source', sa.String(length=60), server_default='instagram', nullable=False),
            sa.Column('source_detail', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('user_id', 'interest', name='uq_user_suggested_interest'),
        )

def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing_tables = insp.get_table_names()

    if 'suggested_interests' in existing_tables:
        op.drop_table('suggested_interests')

    if 'instagram_media' in existing_tables:
        op.drop_table('instagram_media')

    if 'instagram_accounts' in existing_tables:
        op.drop_table('instagram_accounts')

    if 'profiles' in existing_tables:
        profile_cols = [c['name'] for c in insp.get_columns('profiles')]
        if 'instagram_profile_visible' in profile_cols:
            op.drop_column('profiles', 'instagram_profile_visible')
        if 'instagram_recommendations_enabled' in profile_cols:
            op.drop_column('profiles', 'instagram_recommendations_enabled')
