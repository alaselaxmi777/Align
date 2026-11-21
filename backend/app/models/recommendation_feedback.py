from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    item_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)  # community, event, place, user, project, opportunity
    item_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    feedback: Mapped[str] = mapped_column(String(40), index=True, nullable=False)  # relevant, not_relevant, already_done, save_for_later
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_recommendation_feedback"),
    )

    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")
