"""007_project_discussions_and_dedup

Revision ID: 7c4e21a9b831
Revises: f53a19b8c042
Create Date: 2026-11-13 22:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '7c4e21a9b831'
down_revision: Union[str, Sequence[str], None] = 'f53a19b8c042'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    # 1. Create project_discussions if not exists
    if 'project_discussions' not in tables:
        op.create_table(
            'project_discussions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=160), server_default='', nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_project_discussions_id'), 'project_discussions', ['id'], unique=False)
        op.create_index(op.f('ix_project_discussions_project_id'), 'project_discussions', ['project_id'], unique=False)
        op.create_index(op.f('ix_project_discussions_user_id'), 'project_discussions', ['user_id'], unique=False)

    # 2. Add dedup_key column to user_activity_logs if missing
    columns = [c['name'] for c in insp.get_columns('user_activity_logs')]
    if 'dedup_key' not in columns:
        op.add_column('user_activity_logs', sa.Column('dedup_key', sa.String(length=128), nullable=True))
        op.create_index(op.f('ix_user_activity_logs_dedup_key'), 'user_activity_logs', ['dedup_key'], unique=False)

def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    columns = [c['name'] for c in insp.get_columns('user_activity_logs')]
    if 'dedup_key' in columns:
        op.drop_index(op.f('ix_user_activity_logs_dedup_key'), table_name='user_activity_logs')
        op.drop_column('user_activity_logs', 'dedup_key')

    if 'project_discussions' in tables:
        op.drop_index(op.f('ix_project_discussions_user_id'), table_name='project_discussions')
        op.drop_index(op.f('ix_project_discussions_project_id'), table_name='project_discussions')
        op.drop_index(op.f('ix_project_discussions_id'), table_name='project_discussions')
        op.drop_table('project_discussions')
