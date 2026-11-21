from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class UserConnection(Base):
    __tablename__ = "user_connections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)  # pending, accepted, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("sender_id", "receiver_id", name="uq_user_connection_pair"),
    )

    sender: Mapped["app.models.user.User"] = relationship("app.models.user.User", foreign_keys=[sender_id])
    receiver: Mapped["app.models.user.User"] = relationship("app.models.user.User", foreign_keys=[receiver_id])
