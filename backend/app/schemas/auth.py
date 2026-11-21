from datetime import datetime
from typing import Annotated, Any
from pydantic import BaseModel, AfterValidator, Field, ConfigDict
import re

def validate_email_str(v: str) -> str:
    v = v.strip().lower()
    if not re.match(r"^[\w\.\+\-]+@[\w\.\-]+\.[a-zA-Z0-9\-]+$", v):
        raise ValueError("Invalid email format")
    return v

AppEmail = Annotated[str, AfterValidator(validate_email_str)]

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: AppEmail
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: AppEmail
    password: str

class GoogleAuthRequest(BaseModel):
    credential: str = Field(description="Google ID Token from Google Identity Services")

class PasswordResetRequest(BaseModel):
    email: AppEmail

class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8, max_length=128)

class EmailVerifyRequest(BaseModel):
    token: str = Field(min_length=8)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user_id: int | None = None
    name: str | None = None
    email: str | None = None
    onboarding_completed: bool = False

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=16)

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

class LogoutRequest(BaseModel):
    refresh_token: str | None = None

class ReportUserRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)
    details: str | None = None

class ProfileUpdate(BaseModel):
    name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    privacy_level: str | None = "public"
    location_privacy: str | None = "approximate"
    interests: str | None = None
    skills: str | None = None
    hobbies: str | None = None
    skill_proficiency: dict[str, Any] | str | None = None
    hobby_engagement_level: dict[str, Any] | str | None = None
    goals: str | None = None
    preferred_activities: str | None = None
    preferred_community_types: str | None = None

class OnboardingRequest(BaseModel):
    username: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    age_cohort: str | None = None
    gender: str | None = None
    preferred_language: str | None = "English"
    step: int | None = None
    bio: str | None = None
    interests: list[str] | str | None = None
    skills: list[str] | str | None = None
    hobbies: list[str] | str | None = None
    skill_proficiency: dict[str, Any] | str | None = None
    hobby_engagement_level: dict[str, Any] | str | None = None
    goals: list[str] | str | None = None
    preferred_activities: list[str] | str | None = None
    preferred_community_types: list[str] | str | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    privacy_level: str | None = "public"
    location_privacy: str | None = "approximate"

class ProfileResponse(BaseModel):
    id: int
    user_id: int
    bio: str = ""
    avatar_url: str | None = None
    location: str = ""
    latitude: float | None = None
    longitude: float | None = None
    privacy_level: str = "public"
    location_privacy: str = "approximate"
    interests: str = ""
    skills: str = ""
    hobbies: str = ""
    skill_proficiency: str = ""
    hobby_engagement_level: str = ""
    goals: str = ""
    preferred_activities: str = ""
    preferred_community_types: str = ""
    age_cohort: str | None = None
    gender: str | None = None
    preferred_language: str | None = "English"
    onboarding_step: int = 1
    onboarding_completed: bool = False
    followers_count: int = 0
    following_count: int = 0
    connections_count: int = 0
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    id: int
    username: str | None = None
    name: str
    email: str | None = None
    is_active: bool = True
    is_verified: bool = False
    is_admin: bool = False
    is_test: bool = False
    onboarding_completed: bool = False
    is_onboarded: bool = False
    bio: str = ""
    interests: str = ""
    skills: str = ""
    hobbies: str = ""
    location: str | None = None
    distance_band: str | None = None
    profile: ProfileResponse | None = None
    connection_status: str | None = None
    connection_id: int | None = None
    is_connection_sender: bool | None = None
    recommendation_reason: str | None = None
    match_score: float | None = None
    followers_count: int = 0
    following_count: int = 0
    connections_count: int = 0
    model_config = ConfigDict(from_attributes=True)
