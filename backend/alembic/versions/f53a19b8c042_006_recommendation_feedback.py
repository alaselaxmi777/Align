"""006_recommendation_feedback

Revision ID: f53a19b8c042
Revises: e72b14c9f105
Create Date: 2026-11-13 21:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f53a19b8c042'
down_revision: Union[str, Sequence[str], None] = 'e72b14c9f105'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    if 'recommendation_feedbacks' not in tables:
        op.create_table(
            'recommendation_feedbacks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('item_type', sa.String(length=40), nullable=False),
            sa.Column('item_id', sa.Integer(), nullable=False),
            sa.Column('feedback', sa.String(length=40), nullable=False),
            sa.Column('notes', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'item_type', 'item_id', name='uq_user_recommendation_feedback')
        )
        op.create_index(op.f('ix_recommendation_feedbacks_id'), 'recommendation_feedbacks', ['id'], unique=False)
        op.create_index(op.f('ix_recommendation_feedbacks_user_id'), 'recommendation_feedbacks', ['user_id'], unique=False)
        op.create_index(op.f('ix_recommendation_feedbacks_item_type'), 'recommendation_feedbacks', ['item_type'], unique=False)
        op.create_index(op.f('ix_recommendation_feedbacks_item_id'), 'recommendation_feedbacks', ['item_id'], unique=False)
        op.create_index(op.f('ix_recommendation_feedbacks_feedback'), 'recommendation_feedbacks', ['feedback'], unique=False)

def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    if 'recommendation_feedbacks' in tables:
        op.drop_index(op.f('ix_recommendation_feedbacks_feedback'), table_name='recommendation_feedbacks')
        op.drop_index(op.f('ix_recommendation_feedbacks_item_id'), table_name='recommendation_feedbacks')
        op.drop_index(op.f('ix_recommendation_feedbacks_item_type'), table_name='recommendation_feedbacks')
        op.drop_index(op.f('ix_recommendation_feedbacks_user_id'), table_name='recommendation_feedbacks')
        op.drop_index(op.f('ix_recommendation_feedbacks_id'), table_name='recommendation_feedbacks')
        op.drop_table('recommendation_feedbacks')
