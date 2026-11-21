from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class InterestCircle(Base):
    __tablename__ = "interest_circles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    tagline: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="Technology", index=True)
    tags: Mapped[str] = mapped_column(String(255), default="")
    max_members: Mapped[int] = mapped_column(Integer, default=25)  # Small groups
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    creator: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    memberships: Mapped[list["CircleMembership"]] = relationship(
        "CircleMembership", back_populates="circle", cascade="all, delete-orphan"
    )
    discussions: Mapped[list["CircleDiscussion"]] = relationship(
        "CircleDiscussion", back_populates="circle", cascade="all, delete-orphan", order_by="CircleDiscussion.created_at.desc()"
    )
    activities: Mapped[list["CircleActivity"]] = relationship(
        "CircleActivity", back_populates="circle", cascade="all, delete-orphan", order_by="CircleActivity.scheduled_at"
    )

class CircleMembership(Base):
    __tablename__ = "circle_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("interest_circles.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="member")  # admin, member
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "circle_id", name="uq_user_circle_membership"),)

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    circle: Mapped["InterestCircle"] = relationship("InterestCircle", back_populates="memberships")

class CircleDiscussion(Base):
    __tablename__ = "circle_discussions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("interest_circles.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    circle: Mapped["InterestCircle"] = relationship("InterestCircle", back_populates="discussions")
    replies: Mapped[list["CircleDiscussionReply"]] = relationship(
        "CircleDiscussionReply", back_populates="discussion", cascade="all, delete-orphan", order_by="CircleDiscussionReply.created_at"
    )

class CircleDiscussionReply(Base):
    __tablename__ = "circle_discussion_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    discussion_id: Mapped[int] = mapped_column(ForeignKey("circle_discussions.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    discussion: Mapped["CircleDiscussion"] = relationship("CircleDiscussion", back_populates="replies")

class CircleActivity(Base):
    __tablename__ = "circle_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("interest_circles.id", ondelete="CASCADE"), index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    activity_type: Mapped[str] = mapped_column(String(50), default="discussion")  # study_session, project_hack, meet, workshop
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location_or_link: Mapped[str] = mapped_column(String(255), default="Online")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    circle: Mapped["InterestCircle"] = relationship("InterestCircle", back_populates="activities")
    creator: Mapped["app.models.user.User"] = relationship("app.models.user.User")
