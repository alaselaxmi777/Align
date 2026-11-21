from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    tagline: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="AI & Machine Learning", index=True)
    stage: Mapped[str] = mapped_column(String(50), default="idea")  # idea, prototyping, mvp, active
    status: Mapped[str] = mapped_column(String(50), default="recruiting")  # recruiting, in_progress, completed
    required_roles: Mapped[str] = mapped_column(String(500), default="")  # Comma-separated: "Frontend Developer (1), ML Engineer (2)"
    skills_needed: Mapped[str] = mapped_column(String(500), default="")   # Comma-separated: "Python, PyTorch, React, FastAPI"
    github_repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    live_demo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    creator: Mapped["app.models.user.User"] = relationship("app.models.user.User")
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    milestones: Mapped[list["ProjectMilestone"]] = relationship(
        "ProjectMilestone", back_populates="project", cascade="all, delete-orphan", order_by="ProjectMilestone.step_order"
    )
    applications: Mapped[list["ProjectApplication"]] = relationship(
        "ProjectApplication", back_populates="project", cascade="all, delete-orphan", order_by="ProjectApplication.created_at.desc()"
    )
    discussions: Mapped[list["ProjectDiscussion"]] = relationship(
        "ProjectDiscussion", back_populates="project", cascade="all, delete-orphan", order_by="ProjectDiscussion.created_at.desc()"
    )

class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(100), default="Collaborator")  # Lead Architect, ML Engineer, UI Designer
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user_member"),)

    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["app.models.user.User"] = relationship("app.models.user.User")

class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    step_order: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="milestones")

class ProjectApplication(Base):
    __tablename__ = "project_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    desired_role: Mapped[str] = mapped_column(String(100), nullable=False)
    pitch_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, accepted, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="applications")
    applicant: Mapped["app.models.user.User"] = relationship("app.models.user.User")

class ProjectDiscussion(Base):
    __tablename__ = "project_discussions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="discussions")
    author: Mapped["app.models.user.User"] = relationship("app.models.user.User")
