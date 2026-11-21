import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.instagram import InstagramAccount, InstagramMedia, SuggestedInterest
from app.models.user import User, Profile
from app.services.instagram_service import (
    build_instagram_authorize_url,
    verify_oauth_state,
    exchange_code_for_short_lived_token,
    exchange_for_long_lived_token,
    fetch_instagram_profile,
    encrypt_token,
    sync_user_instagram,
    disconnect_user_instagram,
    parse_and_verify_meta_signed_request,
    handle_meta_deauthorization,
    handle_meta_data_deletion,
)
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/instagram", tags=["instagram"])


# --- Schemas ---

class InstagramStatusResponse(BaseModel):
    enabled: bool
    connected: bool
    username: str | None = None
    account_type: str | None = None
    status: str = "not_connected"  # not_connected, connected, reconnect_needed
    media_count: int = 0
    last_synced_at: datetime | None = None
    recommendations_enabled: bool = False
    profile_visible: bool = False
    pending_suggested_interests_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class InstagramMediaItem(BaseModel):
    id: int
    instagram_media_id: str
    media_type: str
    media_url: str
    permalink: str
    caption: str | None = None
    timestamp: datetime | None = None
    hashtags: str = ""
    model_config = ConfigDict(from_attributes=True)


class InstagramPreferencesUpdate(BaseModel):
    recommendations_enabled: bool | None = None
    profile_visible: bool | None = None


class SuggestedInterestItem(BaseModel):
    id: int
    interest: str
    source: str
    source_detail: str | None = None
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Endpoints ---

@router.get("/status", response_model=InstagramStatusResponse)
def get_instagram_status(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """Returns Instagram integration feature availability and current connection status."""
    if not settings.instagram_enabled or not user:
        return InstagramStatusResponse(
            enabled=settings.instagram_enabled,
            connected=False,
            status="not_connected",
        )

    account = db.scalar(select(InstagramAccount).where(InstagramAccount.user_id == user.id))
    if not account:
        return InstagramStatusResponse(
            enabled=True,
            connected=False,
            status="not_connected",
            recommendations_enabled=bool(user.profile and user.profile.instagram_recommendations_enabled),
            profile_visible=bool(user.profile and user.profile.instagram_profile_visible),
        )

    media_count = db.scalar(
        select(func.count(InstagramMedia.id)).where(InstagramMedia.user_id == user.id)
    ) or 0

    pending_sug_count = db.scalar(
        select(func.count(SuggestedInterest.id)).where(
            SuggestedInterest.user_id == user.id,
            SuggestedInterest.source == "instagram",
            SuggestedInterest.status == "pending",
        )
    ) or 0

    return InstagramStatusResponse(
        enabled=True,
        connected=True,
        username=account.username,
        account_type=account.account_type,
        status=account.status,
        media_count=media_count,
        last_synced_at=account.last_synced_at,
        recommendations_enabled=bool(user.profile and user.profile.instagram_recommendations_enabled),
        profile_visible=bool(user.profile and user.profile.instagram_profile_visible),
        pending_suggested_interests_count=pending_sug_count,
    )


@router.get("/connect")
def get_instagram_connect_url(
    user: User = Depends(get_current_user),
):
    """
    Returns the official Meta OAuth authorization URL with a signed, expiring state
    parameter bound to the authenticated user for CSRF protection.
    """
    if not settings.instagram_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instagram integration is currently disabled by administrator configuration.",
        )

    auth_url = build_instagram_authorize_url(user.id)
    return {
        "status": "ok",
        "authorize_url": auth_url,
        "note": "Meta requires an Instagram Business or Creator account for API access.",
    }


@router.get("/callback")
def instagram_oauth_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_reason: str | None = Query(None),
    error_description: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    OAuth redirect endpoint:
    1. Validates the CSRF signed state.
    2. Exchanges authorization code for short-lived token.
    3. Exchanges for a 60-day long-lived token.
    4. Encrypts token with Fernet and stores InstagramAccount.
    5. Performs initial media sync and redirects to /settings.
    """
    frontend_base = settings.cors_origins.split(",")[0].strip()

    if error or not code or not state:
        logger.warning("Instagram OAuth error returned: %s - %s", error, error_description)
        return RedirectResponse(url=f"{frontend_base}/settings?instagram_error={error or 'cancelled'}")

    if not settings.instagram_enabled:
        return RedirectResponse(url=f"{frontend_base}/settings?instagram_error=disabled")

    # 1. Validate signed CSRF state
    try:
        user_id = verify_oauth_state(state)
    except Exception as exc:
        logger.error("Instagram OAuth invalid state: %s", exc)
        return RedirectResponse(url=f"{frontend_base}/settings?instagram_error=invalid_state")

    user = db.get(User, user_id)
    if not user:
        return RedirectResponse(url=f"{frontend_base}/settings?instagram_error=user_not_found")

    # 2. Exchange code for short-lived token
    try:
        short_res = exchange_code_for_short_lived_token(code)
        short_token = short_res["access_token"]
        ig_user_id = str(short_res.get("user_id", ""))
    except Exception as exc:
        logger.error("Instagram short-lived token exchange failed: %s", exc)
        return RedirectResponse(url=f"{frontend_base}/settings?instagram_error=token_exchange_failed")

    # 3. Exchange for long-lived token
    try:
        long_res = exchange_for_long_lived_token(short_token)
        long_token = long_res["access_token"]
        expires_in = long_res.get("expires_in", 5184000)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    except Exception as exc:
        logger.error("Instagram long-lived token exchange failed: %s", exc)
        return RedirectResponse(url=f"{frontend_base}/settings?instagram_error=long_lived_token_failed")

    # 4. Fetch profile
    profile_info = {}
    try:
        profile_info = fetch_instagram_profile(long_token)
    except Exception as exc:
        logger.warning("Instagram profile fetch warning: %s", exc)

    encrypted_token = encrypt_token(long_token)

    # 5. Upsert InstagramAccount
    account = db.scalar(select(InstagramAccount).where(InstagramAccount.user_id == user_id))
    if account:
        account.access_token_encrypted = encrypted_token
        account.token_expires_at = expires_at
        account.instagram_user_id = str(profile_info.get("id") or ig_user_id or account.instagram_user_id)
        account.username = profile_info.get("username") or account.username
        account.account_type = profile_info.get("account_type") or account.account_type
        account.status = "connected"
    else:
        account = InstagramAccount(
            user_id=user_id,
            instagram_user_id=str(profile_info.get("id") or ig_user_id),
            username=profile_info.get("username", "instagram_user"),
            account_type=profile_info.get("account_type", "BUSINESS"),
            access_token_encrypted=encrypted_token,
            token_expires_at=expires_at,
            status="connected",
        )
        db.add(account)

    db.commit()

    # 6. Initial background sync
    try:
        sync_user_instagram(db, user_id)
    except Exception as exc:
        logger.warning("Initial Instagram media sync failed non-fatally: %s", exc)

    return RedirectResponse(url=f"{frontend_base}/settings?instagram=connected")


@router.post(
    "/sync",
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def sync_instagram(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Synchronizes profile and media from Instagram Graph API."""
    if not settings.instagram_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instagram integration is currently disabled.",
        )
    return sync_user_instagram(db, user.id)


@router.get("/media", response_model=list[InstagramMediaItem])
def get_user_media(
    user_id: int | None = Query(None, description="Target user ID to view public posts"),
    limit: int = Query(24, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Returns stored Instagram media items.
    If viewing another user's posts, their profile setting 'instagram_profile_visible' must be enabled.
    """
    target_user_id = user_id or (current_user.id if current_user else None)
    if not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view media.",
        )

    # Privacy check when viewing another user's profile
    if current_user is None or current_user.id != target_user_id:
        target_prof = db.scalar(select(Profile).where(Profile.user_id == target_user_id))
        if not target_prof or not target_prof.instagram_profile_visible:
            return []

    stmt = (
        select(InstagramMedia)
        .where(InstagramMedia.user_id == target_user_id)
        .order_by(InstagramMedia.timestamp.desc().nullslast(), InstagramMedia.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


@router.delete("/disconnect")
def disconnect_instagram(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Disconnects Instagram account and completely deletes all stored tokens,
    media records, and pending suggested interests.
    """
    return disconnect_user_instagram(db, user.id)


@router.post("/preferences")
def update_instagram_preferences(
    payload: InstagramPreferencesUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Updates Instagram recommendation consent and profile visibility settings."""
    profile = user.profile
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)

    if payload.recommendations_enabled is not None:
        profile.instagram_recommendations_enabled = payload.recommendations_enabled
    if payload.profile_visible is not None:
        profile.instagram_profile_visible = payload.profile_visible

    db.commit()
    return {
        "status": "success",
        "recommendations_enabled": profile.instagram_recommendations_enabled,
        "profile_visible": profile.instagram_profile_visible,
    }


# --- Suggested Interests (User Consent Management) ---

@router.get("/suggested-interests", response_model=list[SuggestedInterestItem])
def get_suggested_interests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Returns candidate interests inferred from Instagram posts awaiting user acceptance."""
    stmt = (
        select(SuggestedInterest)
        .where(
            SuggestedInterest.user_id == user.id,
            SuggestedInterest.status == "pending",
        )
        .order_by(SuggestedInterest.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.post("/suggested-interests/{interest_id}/accept")
def accept_suggested_interest(
    interest_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Accepts an inferred interest:
    1. Appends interest to user profile interests.
    2. Feeds interest into Neo4j Knowledge Graph (HAS_INTEREST).
    3. Marks suggested interest as accepted.
    """
    item = db.get(SuggestedInterest, interest_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggested interest not found.")

    profile = user.profile
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)

    current_interests = [i.strip() for i in (profile.interests or "").split(",") if i.strip()]
    if item.interest not in current_interests:
        current_interests.append(item.interest)
        profile.interests = ", ".join(current_interests)

    item.status = "accepted"
    db.commit()

    # Sync to Neo4j graph
    try:
        graph_service.sync_user_profile(
            user_id=user.id,
            name=user.name,
            email=user.email,
            location=profile.location,
            interests=current_interests,
            skills=[s.strip() for s in (profile.skills or "").split(",") if s.strip()],
            goals=[g.strip() for g in (profile.goals or "").split(",") if g.strip()],
        )
    except Exception as exc:
        logger.warning("Graph sync non-fatal warning on accepted interest: %s", exc)

    return {
        "status": "success",
        "message": f"Interest '{item.interest}' added to your profile and graph.",
        "interests": current_interests,
    }


@router.post("/suggested-interests/{interest_id}/reject")
def reject_suggested_interest(
    interest_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Rejects an inferred interest so it will not be suggested again."""
    item = db.get(SuggestedInterest, interest_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggested interest not found.")

    item.status = "rejected"
    db.commit()
    return {"status": "success", "message": f"Interest '{item.interest}' rejected."}


# --- Meta Required Callbacks (Webhook Signature Verified) ---

@router.post("/deauthorize")
def meta_deauthorize_callback(
    signed_request: str = Form(...),
    db: Session = Depends(get_db),
):
    """Meta Deauthorization Callback. Triggered if a user removes the app in Instagram settings."""
    try:
        data = parse_and_verify_meta_signed_request(signed_request)
    except Exception as exc:
        logger.error("Meta deauthorization signature verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signed_request signature.")

    ig_user_id = str(data.get("user_id", ""))
    if ig_user_id:
        handle_meta_deauthorization(db, ig_user_id)

    return {"status": "success"}


@router.post("/data-deletion")
def meta_data_deletion_callback(
    signed_request: str = Form(...),
    db: Session = Depends(get_db),
):
    """Meta Data Deletion Callback. Returns confirmation code and tracking URL as required by Meta policy."""
    try:
        data = parse_and_verify_meta_signed_request(signed_request)
    except Exception as exc:
        logger.error("Meta data deletion signature verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signed_request signature.")

    ig_user_id = str(data.get("user_id", ""))
    confirmation_code, status_url = handle_meta_data_deletion(db, ig_user_id)

    return {
        "url": status_url,
        "confirmation_code": confirmation_code,
    }
