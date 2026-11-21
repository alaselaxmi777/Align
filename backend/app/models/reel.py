from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class Reel(Base):
    __tablename__ = "reels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="Technology", index=True)
    video_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    author_name: Mapped[str] = mapped_column(String(120), nullable=False)
    author_avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_track: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tags: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="public", server_default="public", nullable=False, index=True)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False, index=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False, index=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    author: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    likes: Mapped[list["ReelLike"]] = relationship("ReelLike", back_populates="reel", cascade="all, delete-orphan")
    comments: Mapped[list["ReelComment"]] = relationship("ReelComment", back_populates="reel", cascade="all, delete-orphan")

class ReelLike(Base):
    __tablename__ = "reel_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reel_id: Mapped[int] = mapped_column(ForeignKey("reels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("reel_id", "user_id", name="uq_reel_user_like"),)

    reel: Mapped["Reel"] = relationship("Reel", back_populates="likes")
    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")

class ReelComment(Base):
    __tablename__ = "reel_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reel_id: Mapped[int] = mapped_column(ForeignKey("reels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("reel_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    reel: Mapped["Reel"] = relationship("Reel", back_populates="comments")
    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    replies: Mapped[list["ReelComment"]] = relationship(
        "ReelComment",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id],
        order_by="ReelComment.created_at.asc()",
    )
