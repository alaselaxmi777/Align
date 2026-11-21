"""008_add_is_test_flags

Revision ID: e82b39a7c140
Revises: 7c4e21a9b831
Create Date: 2026-11-16 20:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e82b39a7c140'
down_revision: Union[str, Sequence[str], None] = '7c4e21a9b831'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1. users table
    if 'users' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('users')]
        if 'is_test' not in cols:
            op.add_column('users', sa.Column('is_test', sa.Boolean(), server_default='false', nullable=False))
            op.create_index(op.f('ix_users_is_test'), 'users', ['is_test'], unique=False)

    # 2. communities table
    if 'communities' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('communities')]
        if 'is_test' not in cols:
            op.add_column('communities', sa.Column('is_test', sa.Boolean(), server_default='false', nullable=False))
            op.create_index(op.f('ix_communities_is_test'), 'communities', ['is_test'], unique=False)

    # 3. projects table
    if 'projects' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('projects')]
        if 'is_test' not in cols:
            op.add_column('projects', sa.Column('is_test', sa.Boolean(), server_default='false', nullable=False))
            op.create_index(op.f('ix_projects_is_test'), 'projects', ['is_test'], unique=False)

    # 4. Mark existing test rows in PostgreSQL
    op.execute(
        sa.text(
            "UPDATE users SET is_test = TRUE WHERE "
            "name ILIKE '%test%' OR name ILIKE '%audit%' OR "
            "email ILIKE '%test%' OR email ILIKE '%audit%' OR "
            "name ~ '[0-9]{7,}';"
        )
    )
    op.execute(
        sa.text(
            "UPDATE communities SET is_test = TRUE WHERE "
            "name ILIKE '%test%' OR name ILIKE '%audit%' OR "
            "name ~ '[0-9]{7,}';"
        )
    )
    op.execute(
        sa.text(
            "UPDATE projects SET is_test = TRUE WHERE "
            "title ILIKE '%test%' OR title ILIKE '%audit%' OR "
            "title ~ '[0-9]{7,}';"
        )
    )

def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if 'projects' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('projects')]
        if 'is_test' in cols:
            op.drop_index(op.f('ix_projects_is_test'), table_name='projects')
            op.drop_column('projects', 'is_test')

    if 'communities' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('communities')]
        if 'is_test' in cols:
            op.drop_index(op.f('ix_communities_is_test'), table_name='communities')
            op.drop_column('communities', 'is_test')

    if 'users' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('users')]
        if 'is_test' in cols:
            op.drop_index(op.f('ix_users_is_test'), table_name='users')
            op.drop_column('users', 'is_test')
