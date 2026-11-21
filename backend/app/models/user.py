from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Backward compatibility and API aliases
    @property
    def full_name(self) -> str:
        return self.name

    @full_name.setter
    def full_name(self, value: str):
        self.name = value

    @property
    def hashed_password(self) -> str | None:
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value: str | None):
        self.password_hash = value

    def has_role(self, *roles: str) -> bool:
        if self.is_admin or self.role == "admin":
            return True
        return self.role in roles

    @property
    def is_onboarded(self) -> bool:
        return self.profile.onboarding_completed if self.profile else False

    @is_onboarded.setter
    def is_onboarded(self, value: bool):
        if self.profile:
            self.profile.onboarding_completed = value

    @property
    def onboarding_completed(self) -> bool:
        return self.profile.onboarding_completed if self.profile else False

    @onboarding_completed.setter
    def onboarding_completed(self, value: bool):
        if self.profile:
            self.profile.onboarding_completed = value

    @property
    def avatar_url(self) -> str | None:
        return self.profile.avatar_url if self.profile else None

    @avatar_url.setter
    def avatar_url(self, value: str | None):
        if self.profile:
            self.profile.avatar_url = value

    @property
    def bio(self) -> str:
        return self.profile.bio if self.profile else ""

    @bio.setter
    def bio(self, value: str):
        if self.profile:
            self.profile.bio = value

    @property
    def interests(self) -> str:
        return self.profile.interests if self.profile else ""

    @property
    def skills(self) -> str:
        return self.profile.skills if self.profile else ""

    @property
    def hobbies(self) -> str:
        return self.profile.hobbies if self.profile else ""

    profile: Mapped["Profile"] = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    memberships: Mapped[list["CommunityMembership"]] = relationship("CommunityMembership", back_populates="user", cascade="all, delete-orphan")
    registrations: Mapped[list["EventRegistration"]] = relationship("EventRegistration", back_populates="user", cascade="all, delete-orphan")
    saved_items: Mapped[list["SavedItem"]] = relationship("SavedItem", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    instagram_account: Mapped["app.models.instagram.InstagramAccount | None"] = relationship("app.models.instagram.InstagramAccount", back_populates="user", uselist=False, cascade="all, delete-orphan")
    instagram_media: Mapped[list["app.models.instagram.InstagramMedia"]] = relationship("app.models.instagram.InstagramMedia", back_populates="user", cascade="all, delete-orphan")
    suggested_interests: Mapped[list["app.models.instagram.SuggestedInterest"]] = relationship("app.models.instagram.SuggestedInterest", back_populates="user", cascade="all, delete-orphan")
    refresh_sessions: Mapped[list["RefreshTokenSession"]] = relationship("RefreshTokenSession", back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str] = mapped_column(String(160), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    privacy_level: Mapped[str] = mapped_column(String(30), default="public")
    location_privacy: Mapped[str] = mapped_column(String(30), default="approximate")
    interests: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[str] = mapped_column(Text, default="")
    hobbies: Mapped[str] = mapped_column(Text, default="")
    skill_proficiency: Mapped[str] = mapped_column(String(64), default="")
    hobby_engagement_level: Mapped[str] = mapped_column(String(64), default="")
    goals: Mapped[str] = mapped_column(Text, default="")
    preferred_activities: Mapped[str] = mapped_column(Text, default="")
    preferred_community_types: Mapped[str] = mapped_column(Text, default="")
    age_cohort: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(32), default="English", server_default="English")
    onboarding_step: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    instagram_recommendations_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    instagram_profile_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="profile")

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    preference_key: Mapped[str] = mapped_column(String(100), nullable=False)
    preference_value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(50), default="google")
    provider_user_id: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),)
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserReport(Base):
    __tablename__ = "user_reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reported_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_type: Mapped[str] = mapped_column(String(30), default="user", server_default="user", nullable=False, index=True)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id", ondelete="SET NULL"), nullable=True, index=True)
    reel_id: Mapped[int | None] = mapped_column(ForeignKey("reels.id", ondelete="SET NULL"), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, resolved, dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_id])
    reported_user: Mapped["User | None"] = relationship("User", foreign_keys=[reported_user_id])
    post: Mapped["app.models.post.Post | None"] = relationship("app.models.post.Post", foreign_keys=[post_id])
    reel: Mapped["app.models.reel.Reel | None"] = relationship("app.models.reel.Reel", foreign_keys=[reel_id])

class UserBlock(Base):
    __tablename__ = "user_blocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    blocker_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    blocked_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("blocker_id", "blocked_user_id", name="uq_user_blocks"),)

    blocker: Mapped["User"] = relationship("User", foreign_keys=[blocker_id])
    blocked_user: Mapped["User"] = relationship("User", foreign_keys=[blocked_user_id])

class RefreshTokenSession(Base):
    __tablename__ = "refresh_token_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="refresh_sessions")
