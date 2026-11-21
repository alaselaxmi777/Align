from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    organization: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    opportunity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # hackathon, internship, scholarship, competition, fellowship
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(160), default="Remote / Global")
    is_remote: Mapped[bool] = mapped_column(Boolean, default=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    stipend_or_prize: Mapped[str | None] = mapped_column(String(120), nullable=True)
    apply_url: Mapped[str] = mapped_column(String(500), nullable=False)
    tags: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(80), default="Verified External")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    @property
    def org(self) -> str:
        return self.organization

    @property
    def type(self) -> str:
        return self.opportunity_type

    @property
    def remote_eligible(self) -> bool:
        return self.is_remote

    @property
    def reward(self) -> str | None:
        return self.stipend_or_prize

    @property
    def source_url(self) -> str:
        return self.apply_url

    bookmarks: Mapped[list["OpportunityBookmark"]] = relationship(
        "OpportunityBookmark", back_populates="opportunity", cascade="all, delete-orphan"
    )

class OpportunityBookmark(Base):
    __tablename__ = "opportunity_bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"), index=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "opportunity_id", name="uq_user_opportunity_bookmark"),)

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="bookmarks")
