from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class GoalJourney(Base):
    __tablename__ = "goal_journeys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_category: Mapped[str] = mapped_column(String(80), default="Career & Learning")
    timeframe: Mapped[str] = mapped_column(String(60), default="3-6 months")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="in_progress")  # in_progress, completed, paused
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    milestones: Mapped[list["GoalMilestone"]] = relationship(
        "GoalMilestone", back_populates="journey", cascade="all, delete-orphan", order_by="GoalMilestone.step_order"
    )

class GoalMilestone(Base):
    __tablename__ = "goal_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    journey_id: Mapped[int] = mapped_column(ForeignKey("goal_journeys.id", ondelete="CASCADE"), index=True)
    step_order: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    estimated_weeks: Mapped[int] = mapped_column(Integer, default=2)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recommended_resources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded array of resources/links
    recommended_communities_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded IDs/cards
    recommended_events_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_peers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    journey: Mapped["GoalJourney"] = relationship("GoalJourney", back_populates="milestones")
