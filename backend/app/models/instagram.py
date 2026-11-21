from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    instagram_user_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(60), nullable=True)  # BUSINESS, CREATOR
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="connected")  # connected, reconnect_needed, expired

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User", back_populates="instagram_account")
    media: Mapped[list["InstagramMedia"]] = relationship("InstagramMedia", back_populates="account", cascade="all, delete-orphan")


class InstagramMedia(Base):
    __tablename__ = "instagram_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("instagram_accounts.id", ondelete="CASCADE"), nullable=True)
    instagram_media_id: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(50), default="IMAGE")  # IMAGE, VIDEO, CAROUSEL_ALBUM
    media_url: Mapped[str] = mapped_column(Text, nullable=False)
    permalink: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hashtags: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User", back_populates="instagram_media")
    account: Mapped["InstagramAccount | None"] = relationship("InstagramAccount", back_populates="media")


class SuggestedInterest(Base):
    __tablename__ = "suggested_interests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    interest: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="instagram")
    source_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, accepted, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (UniqueConstraint("user_id", "interest", name="uq_user_suggested_interest"),)

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User", back_populates="suggested_interests")
