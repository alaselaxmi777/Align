"""011 refresh token sessions

Revision ID: c31d953e4167
Revises: b20c942d3156
Create Date: 2026-11-17 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c31d953e4167'
down_revision: Union[str, None] = 'b20c942d3156'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'refresh_token_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('family_id', sa.String(length=64), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_refresh_token_sessions_id'), 'refresh_token_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_refresh_token_sessions_user_id'), 'refresh_token_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_refresh_token_sessions_token_hash'), 'refresh_token_sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_refresh_token_sessions_family_id'), 'refresh_token_sessions', ['family_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_refresh_token_sessions_family_id'), table_name='refresh_token_sessions')
    op.drop_index(op.f('ix_refresh_token_sessions_token_hash'), table_name='refresh_token_sessions')
    op.drop_index(op.f('ix_refresh_token_sessions_user_id'), table_name='refresh_token_sessions')
    op.drop_index(op.f('ix_refresh_token_sessions_id'), table_name='refresh_token_sessions')
    op.drop_table('refresh_token_sessions')
