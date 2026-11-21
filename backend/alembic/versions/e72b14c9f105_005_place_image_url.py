"""005_place_image_url

Revision ID: e72b14c9f105
Revises: a41f82c9e704
Create Date: 2026-11-13 21:16:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e72b14c9f105'
down_revision: Union[str, Sequence[str], None] = 'a41f82c9e704'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('places')]
    if 'image_url' not in cols:
        op.add_column('places', sa.Column('image_url', sa.String(length=500), nullable=True))

def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('places')]
    if 'image_url' in cols:
        op.drop_column('places', 'image_url')
