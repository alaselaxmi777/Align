"""016 add username and onboarding fields

Revision ID: 016a210c41f9
Revises: 015a109b31d9
Create Date: 2026-11-20 23:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '016a210c41f9'
down_revision: Union[str, None] = '015a109b31d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add username to users table
    op.add_column('users', sa.Column('username', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # 2. Add demographic and progress fields to profiles table
    op.add_column('profiles', sa.Column('age_cohort', sa.String(length=32), nullable=True))
    op.add_column('profiles', sa.Column('gender', sa.String(length=32), nullable=True))
    op.add_column('profiles', sa.Column('preferred_language', sa.String(length=32), server_default='English', nullable=True))
    op.add_column('profiles', sa.Column('onboarding_step', sa.Integer(), server_default='1', nullable=False))


def downgrade() -> None:
    op.drop_column('profiles', 'onboarding_step')
    op.drop_column('profiles', 'preferred_language')
    op.drop_column('profiles', 'gender')
    op.drop_column('profiles', 'age_cohort')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_column('users', 'username')
