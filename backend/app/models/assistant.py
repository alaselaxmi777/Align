from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New Discovery Session", index=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    messages: Mapped[list["AssistantMessage"]] = relationship(
        "AssistantMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="AssistantMessage.created_at"
    )

    __table_args__ = (
        Index("ix_assistant_conv_user_updated", "user_id", "updated_at"),
        Index("ix_assistant_conv_user_pinned", "user_id", "pinned"),
        Index("ix_assistant_conv_user_archived", "user_id", "archived"),
    )

class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("assistant_conversations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # "user", "assistant", "system", "tool"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # Backward compat JSON cards
    tool_calls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-serialized tool calls / executions
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Citations, sources, cards, followups
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    conversation: Mapped["AssistantConversation"] = relationship("AssistantConversation", back_populates="messages")

    __table_args__ = (
        Index("ix_assistant_msg_conv_created", "conversation_id", "created_at"),
    )

class AssistantMemory(Base):
    __tablename__ = "assistant_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    memory_type: Mapped[str] = mapped_column(String(32), default="context")  # interest, skill, learning_goal, career_goal, preference, project, context
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_conversation_id: Mapped[int | None] = mapped_column(ForeignKey("assistant_conversations.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending", index=True)  # pending, approved, rejected
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")

    __table_args__ = (
        Index("ix_assistant_memories_user_status", "user_id", "status"),
    )

class AssistantSettings(Base):
    __tablename__ = "assistant_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    auto_suggest_followups: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    research_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")

class AssistantSavedRecommendation(Base):
    __tablename__ = "assistant_saved_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)  # user, community, event, place, opportunity, resource
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String(16), nullable=True)  # useful, not_useful, dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")

    __table_args__ = (
        Index("ix_assistant_saved_recs_user", "user_id", "entity_type"),
    )

class AssistantGoalJourney(Base):
    __tablename__ = "assistant_goal_journeys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    journey_type: Mapped[str] = mapped_column(String(32), default="learning")  # learning, career, personal, networking, project
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    plans_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON { seven_day: [...], thirty_day: [...], ninety_day: [...] }
    milestones_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON [{ id, title, description, is_completed }]
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(32), default="active", server_default="active", index=True)  # active, paused, completed
    linked_conversation_id: Mapped[int | None] = mapped_column(ForeignKey("assistant_conversations.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")

    __table_args__ = (
        Index("ix_assistant_goal_journeys_user_status", "user_id", "status"),
    )
