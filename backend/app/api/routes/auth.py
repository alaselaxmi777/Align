import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_current_user_optional
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_tracked_refresh_token,
    hash_token,
    decode_token,
    hash_password,
    verify_password,
    generate_secure_token,
    verify_google_id_token,
)
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import (
    User,
    Profile,
    UserPreference,
    PasswordResetToken,
    OAuthAccount,
    EmailVerificationToken,
    RefreshTokenSession,
)
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    LogoutRequest,
    GoogleAuthRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerifyRequest,
    TokenResponse,
    UserResponse,
    ProfileUpdate,
    ProfileResponse,
    OnboardingRequest,
)
from app.services.embeddings import generate_embedding, build_profile_text
from app.services.graph_service import graph_service
from app.services.email import send_password_reset_email, send_verification_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

def get_or_create_profile(user: User, db: Session) -> Profile:
    if user.profile:
        return user.profile
    profile = Profile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

COMMON_WEAK_PASSWORDS = {
    "password", "password123", "12345678", "123456789", "1234567890",
    "qwerty123", "admin123", "welcome1", "letmein1", "iloveyou"
}

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.password.lower().strip() in COMMON_WEAK_PASSWORDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too common and easily guessable. Please choose a more secure password.",
        )
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )
    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.flush()

    # Create associated Profile
    profile = Profile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(max_requests=15, window_seconds=60))],
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support."
        )
    token = create_access_token(str(user.id))
    refresh, r_hash, fam, exp = create_tracked_refresh_token(str(user.id))
    db.add(RefreshTokenSession(user_id=user.id, token_hash=r_hash, family_id=fam, expires_at=exp))
    db.commit()

    return TokenResponse(
        access_token=token,
        refresh_token=refresh,
        token_type="bearer",
        user_id=user.id,
        name=user.name,
        email=user.email,
        onboarding_completed=user.is_onboarded,
    )

@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def refresh_access_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
        user_id_str = claims.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims.")
        user = db.get(User, int(user_id_str))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or not found.")

        t_hash = hash_token(payload.refresh_token)
        session_rec = db.scalar(select(RefreshTokenSession).where(RefreshTokenSession.token_hash == t_hash))

        if session_rec:
            if session_rec.is_revoked:
                # TOKEN REUSE DETECTED!
                # Revoke all tokens in this family immediately
                db.execute(
                    update(RefreshTokenSession)
                    .where(RefreshTokenSession.family_id == session_rec.family_id)
                    .values(is_revoked=True)
                )
                db.commit()
                logger.warning(
                    f"SECURITY ALERT: Refresh token reuse detected for user {user.id}, family {session_rec.family_id}."
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Security alert: Token reuse detected. All sessions in this family have been revoked for your safety. Please log in again."
                )
            # Mark current token as revoked (single-use rotation)
            session_rec.is_revoked = True
            current_fam = session_rec.family_id
        else:
            current_fam = claims.get("fam")

        new_access = create_access_token(str(user.id))
        new_refresh, new_hash, new_fam, new_exp = create_tracked_refresh_token(str(user.id), family_id=current_fam)
        db.add(RefreshTokenSession(user_id=user.id, token_hash=new_hash, family_id=new_fam, expires_at=new_exp))
        db.commit()

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            user_id=user.id,
            name=user.name,
            email=user.email,
            onboarding_completed=user.is_onboarded,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Refresh token invalid or expired: {exc}")

@router.post("/google", response_model=TokenResponse)
def google_sign_in(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticates via Google Identity Services ID Token.
    Verifies signature and audience with Google's servers.
    """
    try:
        id_info = verify_google_id_token(payload.credential)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    google_sub = id_info.get("sub")
    email = (id_info.get("email") or "").lower().strip()
    name = id_info.get("name") or "Google User"
    avatar = id_info.get("picture")

    if not google_sub or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incomplete Google account profile returned."
        )

    # Check if OAuth account exists
    oauth = db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_user_id == google_sub
        )
    )

    if oauth:
        user = oauth.user
    else:
        # Check if user with this email exists
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(
                name=name,
                email=email,
                is_active=True,
                is_verified=id_info.get("email_verified", True),
            )
            db.add(user)
            db.flush()
            profile = Profile(user_id=user.id, avatar_url=avatar)
            db.add(profile)
            db.flush()
        
        # Link OAuth
        new_oauth = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=google_sub
        )
        db.add(new_oauth)
        db.commit()
        db.refresh(user)

    token = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=token,
        refresh_token=refresh,
        token_type="bearer",
        user_id=user.id,
        name=user.name,
        email=user.email,
        onboarding_completed=user.is_onboarded,
    )

@router.post(
    "/forgot-password",
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    # Return 200 even if email not found to prevent user enumeration
    if not user:
        return {"status": "ok", "message": "If an account with that email exists, password reset instructions have been generated."}
    
    raw_token = generate_secure_token()
    token_hash = hash_password(raw_token)
    expires = datetime.now(timezone.utc) + timedelta(hours=2)

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires,
        used=False,
    )
    db.add(reset_record)
    db.commit()

    # If SMTP is configured, send email. Otherwise log instruction.
    email_sent = False
    if settings.smtp_host and settings.smtp_username:
        logger.info(f"Password reset token issued for {email}. Dispatching via SMTP.")
        email_sent = send_password_reset_email(email, raw_token)
    else:
        logger.info(f"Password reset requested for {email}. SMTP is not configured.")

    return {
        "status": "ok",
        "message": "If an account with that email exists, password reset instructions have been generated.",
    }

@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    # Find valid unexpired tokens
    tokens = list(db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at >= datetime.now(timezone.utc)
        )
    ))
    matched_record = None
    for rec in tokens:
        if verify_password(payload.token, rec.token_hash):
            matched_record = rec
            break

    if not matched_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )

    user = db.get(User, matched_record.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    user.password_hash = hash_password(payload.new_password)
    matched_record.used = True
    # Revoke all existing sessions upon password reset
    db.execute(
        update(RefreshTokenSession)
        .where(RefreshTokenSession.user_id == user.id)
        .values(is_revoked=True)
    )
    db.commit()
    return {"status": "ok", "message": "Password has been successfully updated. You may now log in."}

@router.post("/send-verification")
def send_email_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.is_verified:
        return {"status": "ok", "message": "Email is already verified."}

    raw_token = generate_secure_token()
    token_hash = hash_password(raw_token)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)

    verif_record = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires,
        used=False,
    )
    db.add(verif_record)
    db.commit()

    if settings.smtp_host and settings.smtp_username:
        logger.info(f"Verification token issued for {user.email}. Dispatching via SMTP.")
        send_verification_email(user.email, raw_token)
    else:
        logger.info(f"Verification email requested for {user.email}. SMTP is not configured.")

    return {
        "status": "ok",
        "message": "Verification code has been dispatched.",
    }

@router.post("/verify-email")
def verify_email(payload: EmailVerifyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.is_verified:
        return {"status": "ok", "message": "Email is already verified."}

    tokens = list(db.scalars(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used == False,
            EmailVerificationToken.expires_at >= datetime.now(timezone.utc)
        )
    ))

    matched = None
    for rec in tokens:
        if verify_password(payload.token, rec.token_hash):
            matched = rec
            break

    if not matched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )

    matched.used = True
    user.is_verified = True
    db.commit()
    return {"status": "ok", "message": "Email has been successfully verified."}

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_or_create_profile(user, db)
    return user

@router.put("/profile", response_model=ProfileResponse)
def update_profile(payload: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_or_create_profile(user, db)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is not None:
            setattr(profile, field, value)
    
    # Refresh embedding when profile text changes
    context_text = build_profile_text(
        bio=profile.bio,
        interests=profile.interests,
        skills=profile.skills,
        hobbies=profile.hobbies,
        skill_proficiency=profile.skill_proficiency,
        hobby_engagement_level=profile.hobby_engagement_level,
        goals=profile.goals,
        preferred_activities=profile.preferred_activities,
        preferred_community_types=profile.preferred_community_types,
    )
    profile.embedding = generate_embedding(context_text) if context_text else None
    db.commit()
    db.refresh(profile)
    return profile

@router.post("/onboarding", response_model=ProfileResponse)
def complete_onboarding(payload: OnboardingRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_or_create_profile(user, db)

    # 1. Handle Username
    if payload.username is not None and payload.username.strip():
        clean_user = payload.username.strip().lower()
        import re
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", clean_user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be 3-20 characters long and contain only letters, numbers, or underscores."
            )
        existing = db.scalar(select(User).where(func.lower(User.username) == clean_user, User.id != user.id))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken by another account."
            )
        user.username = clean_user

    # 2. Handle Name and Avatar
    if payload.name is not None and payload.name.strip():
        user.name = payload.name.strip()
    if payload.avatar_url is not None:
        profile.avatar_url = payload.avatar_url

    # 3. Handle Demographics & Step tracking
    if payload.age_cohort is not None:
        profile.age_cohort = payload.age_cohort.strip()
    if payload.gender is not None:
        profile.gender = payload.gender.strip()
    if payload.preferred_language is not None:
        profile.preferred_language = payload.preferred_language.strip()
    if payload.step is not None:
        profile.onboarding_step = payload.step

    def to_str(val):
        if isinstance(val, list):
            return ", ".join(str(x) for x in val)
        if isinstance(val, dict):
            import json
            return json.dumps(val)
        return str(val).strip() if val is not None else ""

    if payload.bio is not None:
        profile.bio = payload.bio.strip()
    if payload.privacy_level:
        profile.privacy_level = payload.privacy_level.strip()
    if payload.interests is not None:
        profile.interests = to_str(payload.interests)
    if payload.skills is not None:
        profile.skills = to_str(payload.skills)
    if payload.hobbies is not None:
        profile.hobbies = to_str(payload.hobbies)
    if payload.skill_proficiency is not None:
        profile.skill_proficiency = to_str(payload.skill_proficiency)
    if payload.hobby_engagement_level is not None:
        profile.hobby_engagement_level = to_str(payload.hobby_engagement_level)
    if payload.goals is not None:
        profile.goals = to_str(payload.goals)
    if payload.preferred_activities is not None:
        profile.preferred_activities = to_str(payload.preferred_activities)
    if payload.preferred_community_types is not None:
        profile.preferred_community_types = to_str(payload.preferred_community_types)
    if payload.location:
        profile.location = payload.location
    # Privacy safeguard: Do not collect or persist raw user GPS coordinates (rely on city/district text)
    profile.latitude = None
    profile.longitude = None

    # Complete onboarding if step is 4 (final) or step is omitted
    is_completed = (payload.step is None or payload.step >= 4)
    if is_completed:
        profile.onboarding_completed = True
        profile.onboarding_step = 4

    # Save to user_preferences table
    for k, v in [
        ("bio", profile.bio),
        ("privacy_level", profile.privacy_level),
        ("interests", profile.interests),
        ("skills", profile.skills),
        ("hobbies", profile.hobbies),
        ("skill_proficiency", profile.skill_proficiency),
        ("hobby_engagement_level", profile.hobby_engagement_level),
        ("goals", profile.goals),
        ("preferred_activities", profile.preferred_activities),
        ("preferred_community_types", profile.preferred_community_types)
    ]:
        pref = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id, UserPreference.preference_key == k))
        if pref:
            pref.preference_value = v
        else:
            db.add(UserPreference(user_id=user.id, preference_key=k, preference_value=v))

    context_text = build_profile_text(
        bio=profile.bio,
        interests=profile.interests,
        skills=profile.skills,
        hobbies=profile.hobbies,
        skill_proficiency=profile.skill_proficiency,
        hobby_engagement_level=profile.hobby_engagement_level,
        goals=profile.goals,
        preferred_activities=profile.preferred_activities,
        preferred_community_types=profile.preferred_community_types,
    )
    profile.embedding = generate_embedding(context_text) if context_text else None

    db.commit()
    db.refresh(profile)

    # Real-time sync to Neo4j Knowledge Graph
    try:
        interests_list = [i.strip() for i in profile.interests.split(",") if i.strip()]
        skills_list = [s.strip() for s in profile.skills.split(",") if s.strip()]
        goals_list = [g.strip() for g in profile.goals.split(",") if g.strip()]
        graph_service.sync_user_profile(
            user_id=user.id,
            name=user.name,
            email=user.email,
            location=profile.location or "",
            interests=interests_list,
            skills=skills_list,
            goals=goals_list,
        )
    except Exception as exc:
        logger.warning(f"Neo4j sync during onboarding skipped: {exc}")

    return profile

@router.post("/logout")
def logout(
    payload: LogoutRequest | None = None,
    user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Client token invalidation / logout acknowledgment."""
    if payload and payload.refresh_token:
        t_hash = hash_token(payload.refresh_token)
        rec = db.scalar(select(RefreshTokenSession).where(RefreshTokenSession.token_hash == t_hash))
        if rec:
            rec.is_revoked = True
            db.commit()
    elif user:
        latest = db.scalar(
            select(RefreshTokenSession)
            .where(RefreshTokenSession.user_id == user.id, RefreshTokenSession.is_revoked == False)
            .order_by(RefreshTokenSession.created_at.desc())
        )
        if latest:
            latest.is_revoked = True
            db.commit()

    return {"status": "ok", "message": "Successfully logged out. Client tokens cleared."}

@router.post("/logout-all")
def logout_all_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revokes all active refresh tokens and sessions across all devices for the current user."""
    db.execute(
        update(RefreshTokenSession)
        .where(RefreshTokenSession.user_id == user.id)
        .values(is_revoked=True)
    )
    db.commit()
    return {"status": "ok", "message": "All active sessions have been revoked. Please log in again."}

@router.post(
    "/change-password",
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Changes user password after verifying old password.
    Enforces minimum length 8 and common password check.
    Revokes all active sessions upon password change.
    """
    if not user.password_hash or not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed."
        )

    new_pwd = payload.new_password.strip()
    if new_pwd.lower() in COMMON_WEAK_PASSWORDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password is too common and easily guessable."
        )

    user.password_hash = hash_password(new_pwd)
    # Revoke all existing sessions
    db.execute(
        update(RefreshTokenSession)
        .where(RefreshTokenSession.user_id == user.id)
        .values(is_revoked=True)
    )
    db.commit()
    return {"status": "ok", "message": "Password changed successfully. All other sessions have been revoked."}

@router.delete("/me")
def delete_own_account(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently deletes user account, purging all personal data,
    profiles, preferences, uploaded media, and relationships from PostgreSQL and Neo4j.
    """
    user_id = user.id
    # Delete from Neo4j
    try:
        graph_service.delete_user_node(user_id)
    except Exception as exc:
        logger.warning(f"Neo4j user deletion non-fatal error: {exc}")

    db.delete(user)
    db.commit()
    return {"status": "ok", "message": f"Account {user_id} and all associated data permanently deleted."}
