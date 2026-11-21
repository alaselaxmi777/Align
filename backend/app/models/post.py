from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    community_id: Mapped[int | None] = mapped_column(ForeignKey("communities.id", ondelete="SET NULL"), index=True, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="connections_only", server_default="connections_only", nullable=False, index=True)
    location_area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False, index=True)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False, index=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    author: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    community: Mapped["app.models.community.Community"] = relationship("app.models.community.Community")
    likes: Mapped[list["PostLike"]] = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    comments: Mapped[list["PostComment"]] = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")
    media: Mapped[list["PostMedia"]] = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan", order_by="PostMedia.position")

class PostMedia(Base):
    __tablename__ = "post_media"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), default="image", nullable=False)
    original_url: Mapped[str] = mapped_column(String(500), nullable=False)
    feed_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    post: Mapped["Post"] = relationship("Post", back_populates="media")

class PostLike(Base):
    __tablename__ = "post_likes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_user_like"),
    )

    post: Mapped["Post"] = relationship("Post", back_populates="likes")
    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")

class PostComment(Base):
    __tablename__ = "post_comments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("post_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    post: Mapped["Post"] = relationship("Post", back_populates="comments")
    author: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    replies: Mapped[list["PostComment"]] = relationship(
        "PostComment",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id],
        order_by="PostComment.created_at.asc()",
    )
