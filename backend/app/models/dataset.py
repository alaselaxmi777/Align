from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class SkillsHobbiesDataset(Base):
    __tablename__ = "skills_hobbies_dataset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    record_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # "Skill", "Hobby"
    category: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    application_context: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    proficiency_engagement_level: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    setting: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    frequency: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    primary_motivation: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    popularity_score: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    expanded_record_description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_sh_type_category", "type", "category"),
        Index("ix_sh_rec_type_cat", "record_type", "category"),
    )

class SkillMaster(Base):
    __tablename__ = "skill_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class HobbyMaster(Base):
    __tablename__ = "hobby_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Goals & Interests Dataset
# ---------------------------------------------------------------------------

class GoalsInterestsDataset(Base):
    __tablename__ = "goals_interests_dataset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    record_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # "Goal", "Interest"
    category: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    life_context: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    timeline_engagement_level: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    priority_setting: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    status_frequency: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    primary_motivation: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    popularity_score: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    expanded_record_description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_gi_type_category", "type", "category"),
        Index("ix_gi_rec_type_cat", "record_type", "category"),
    )


class GoalMaster(Base):
    __tablename__ = "goal_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InterestMaster(Base):
    __tablename__ = "interest_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="v1.0")
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    record_types: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="ready")
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
