"""003_assistant_v2

Revision ID: d91a27e8a301
Revises: c72f10b83e91
Create Date: 2026-11-13 19:06:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'd91a27e8a301'
down_revision: Union[str, Sequence[str], None] = 'c72f10b83e91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Extend assistant_conversations
    conn = op.get_bind()
    # Check if assistant_conversations exists
    insp = sa.inspect(conn)
    tables = insp.get_table_names()
    
    if 'assistant_conversations' not in tables:
        op.create_table(
            'assistant_conversations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), server_default='New Discovery Session', nullable=False),
            sa.Column('pinned', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('archived', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_assistant_conversations_id'), 'assistant_conversations', ['id'], unique=False)
        op.create_index(op.f('ix_assistant_conversations_user_id'), 'assistant_conversations', ['user_id'], unique=False)
        op.create_index(op.f('ix_assistant_conversations_title'), 'assistant_conversations', ['title'], unique=False)
        op.create_index('ix_assistant_conv_user_updated', 'assistant_conversations', ['user_id', 'updated_at'], unique=False)
        op.create_index('ix_assistant_conv_user_pinned', 'assistant_conversations', ['user_id', 'pinned'], unique=False)
        op.create_index('ix_assistant_conv_user_archived', 'assistant_conversations', ['user_id', 'archived'], unique=False)
    else:
        existing_cols = [c['name'] for c in insp.get_columns('assistant_conversations')]
        if 'pinned' not in existing_cols:
            op.add_column('assistant_conversations', sa.Column('pinned', sa.Boolean(), server_default='false', nullable=False))
            op.create_index('ix_assistant_conv_user_pinned', 'assistant_conversations', ['user_id', 'pinned'], unique=False)
        if 'archived' not in existing_cols:
            op.add_column('assistant_conversations', sa.Column('archived', sa.Boolean(), server_default='false', nullable=False))
            op.create_index('ix_assistant_conv_user_archived', 'assistant_conversations', ['user_id', 'archived'], unique=False)
        if 'last_message_at' not in existing_cols:
            op.add_column('assistant_conversations', sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

    # 2. Extend assistant_messages
    if 'assistant_messages' not in tables:
        op.create_table(
            'assistant_messages',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('conversation_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('role', sa.String(length=32), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('intent', sa.String(length=64), nullable=True),
            sa.Column('action_data', sa.Text(), nullable=True),
            sa.Column('tool_calls', sa.Text(), nullable=True),
            sa.Column('metadata_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['conversation_id'], ['assistant_conversations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_assistant_messages_id'), 'assistant_messages', ['id'], unique=False)
        op.create_index(op.f('ix_assistant_messages_conversation_id'), 'assistant_messages', ['conversation_id'], unique=False)
        op.create_index(op.f('ix_assistant_messages_user_id'), 'assistant_messages', ['user_id'], unique=False)
        op.create_index('ix_assistant_msg_conv_created', 'assistant_messages', ['conversation_id', 'created_at'], unique=False)
    else:
        existing_msg_cols = [c['name'] for c in insp.get_columns('assistant_messages')]
        if 'user_id' not in existing_msg_cols:
            op.add_column('assistant_messages', sa.Column('user_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_assistant_messages_user_id', 'assistant_messages', 'users', ['user_id'], ['id'], ondelete='CASCADE')
            op.create_index(op.f('ix_assistant_messages_user_id'), 'assistant_messages', ['user_id'], unique=False)
        if 'tool_calls' not in existing_msg_cols:
            op.add_column('assistant_messages', sa.Column('tool_calls', sa.Text(), nullable=True))
        if 'metadata_json' not in existing_msg_cols:
            op.add_column('assistant_messages', sa.Column('metadata_json', sa.Text(), nullable=True))

    # 3. assistant_memories
    if 'assistant_memories' not in tables:
        op.create_table(
            'assistant_memories',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('memory_type', sa.String(length=32), server_default='context', nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('source_conversation_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=16), server_default='pending', nullable=False),
            sa.Column('embedding', Vector(384), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['source_conversation_id'], ['assistant_conversations.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_assistant_memories_id'), 'assistant_memories', ['id'], unique=False)
        op.create_index(op.f('ix_assistant_memories_user_id'), 'assistant_memories', ['user_id'], unique=False)
        op.create_index(op.f('ix_assistant_memories_status'), 'assistant_memories', ['status'], unique=False)
        op.create_index('ix_assistant_memories_user_status', 'assistant_memories', ['user_id', 'status'], unique=False)

    # 4. assistant_settings
    if 'assistant_settings' not in tables:
        op.create_table(
            'assistant_settings',
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('memory_enabled', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('auto_suggest_followups', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('research_enabled', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('user_id')
        )

    # 5. assistant_saved_recommendations
    if 'assistant_saved_recommendations' not in tables:
        op.create_table(
            'assistant_saved_recommendations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('entity_type', sa.String(length=32), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('feedback', sa.String(length=16), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_assistant_saved_recommendations_id'), 'assistant_saved_recommendations', ['id'], unique=False)
        op.create_index(op.f('ix_assistant_saved_recommendations_user_id'), 'assistant_saved_recommendations', ['user_id'], unique=False)
        op.create_index(op.f('ix_assistant_saved_recommendations_created_at'), 'assistant_saved_recommendations', ['created_at'], unique=False)
        op.create_index('ix_assistant_saved_recs_user', 'assistant_saved_recommendations', ['user_id', 'entity_type'], unique=False)

    # 6. assistant_goal_journeys
    if 'assistant_goal_journeys' not in tables:
        op.create_table(
            'assistant_goal_journeys',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('journey_type', sa.String(length=32), server_default='learning', nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('objective', sa.Text(), nullable=False),
            sa.Column('plans_json', sa.Text(), nullable=True),
            sa.Column('milestones_json', sa.Text(), nullable=True),
            sa.Column('progress_percentage', sa.Integer(), server_default='0', nullable=False),
            sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
            sa.Column('linked_conversation_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['linked_conversation_id'], ['assistant_conversations.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_assistant_goal_journeys_id'), 'assistant_goal_journeys', ['id'], unique=False)
        op.create_index(op.f('ix_assistant_goal_journeys_user_id'), 'assistant_goal_journeys', ['user_id'], unique=False)
        op.create_index(op.f('ix_assistant_goal_journeys_status'), 'assistant_goal_journeys', ['status'], unique=False)
        op.create_index('ix_assistant_goal_journeys_user_status', 'assistant_goal_journeys', ['user_id', 'status'], unique=False)

def downgrade() -> None:
    op.drop_table('assistant_goal_journeys')
    op.drop_table('assistant_saved_recommendations')
    op.drop_table('assistant_settings')
    op.drop_table('assistant_memories')
    op.drop_column('assistant_messages', 'metadata_json')
    op.drop_column('assistant_messages', 'tool_calls')
    op.drop_column('assistant_messages', 'user_id')
    op.drop_column('assistant_conversations', 'last_message_at')
    op.drop_column('assistant_conversations', 'archived')
    op.drop_column('assistant_conversations', 'pinned')
