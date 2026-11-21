"""009_opportunity_and_event_columns

Revision ID: a19b831c2045
Revises: e82b39a7c140
Create Date: 2026-11-16 21:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a19b831c2045'
down_revision: Union[str, Sequence[str], None] = 'e82b39a7c140'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1. opportunities table
    if 'opportunities' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('opportunities')]
        if 'is_active' not in cols:
            op.add_column('opportunities', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
            op.create_index(op.f('ix_opportunities_is_active'), 'opportunities', ['is_active'], unique=False)
        if 'last_verified_at' not in cols:
            op.add_column('opportunities', sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True))

    # 2. events table
    if 'events' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('events')]
        if 'external_id' not in cols:
            op.add_column('events', sa.Column('external_id', sa.String(length=120), nullable=True))
            op.create_index(op.f('ix_events_external_id'), 'events', ['external_id'], unique=False)

def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if 'events' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('events')]
        if 'external_id' in cols:
            op.drop_index(op.f('ix_events_external_id'), table_name='events')
            op.drop_column('events', 'external_id')

    if 'opportunities' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('opportunities')]
        if 'last_verified_at' in cols:
            op.drop_column('opportunities', 'last_verified_at')
        if 'is_active' in cols:
            op.drop_index(op.f('ix_opportunities_is_active'), table_name='opportunities')
            op.drop_column('opportunities', 'is_active')
