from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class UserGamification(Base):
    __tablename__ = "user_gamification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    xp_points: Mapped[int] = mapped_column(Integer, default=50)  # Initial starter XP
    current_level: Mapped[int] = mapped_column(Integer, default=1)
    current_streak_days: Mapped[int] = mapped_column(Integer, default=1)
    last_activity_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    community_contribution_points: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    badges: Mapped[list["UserBadge"]] = relationship(
        "UserBadge", back_populates="gamification", cascade="all, delete-orphan", order_by="UserBadge.unlocked_at.desc()"
    )
    activity_logs: Mapped[list["UserActivityLog"]] = relationship(
        "UserActivityLog", back_populates="gamification", cascade="all, delete-orphan", order_by="UserActivityLog.created_at.desc()"
    )

class UserBadge(Base):
    __tablename__ = "user_badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gamification_id: Mapped[int] = mapped_column(ForeignKey("user_gamification.id", ondelete="CASCADE"), index=True)
    badge_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="community")  # community, learning, networking, milestones
    icon_name: Mapped[str] = mapped_column(String(50), default="Award")
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("gamification_id", "badge_key", name="uq_gamification_badge"),)

    gamification: Mapped["UserGamification"] = relationship("UserGamification", back_populates="badges")

class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gamification_id: Mapped[int] = mapped_column(ForeignKey("user_gamification.id", ondelete="CASCADE"), index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)  # milestone_completed, circle_created, event_rsvp, peer_connected
    xp_awarded: Mapped[int] = mapped_column(Integer, default=10)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    dedup_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    gamification: Mapped["UserGamification"] = relationship("UserGamification", back_populates="activity_logs")
