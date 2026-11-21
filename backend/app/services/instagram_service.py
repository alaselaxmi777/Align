import base64
import hashlib
import hmac
import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
import jwt
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.instagram import InstagramAccount, InstagramMedia, SuggestedInterest
from app.models.user import User, Profile
from app.services.embeddings import generate_embedding
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)

# --- Fernet Token Encryption at Rest ---

def get_fernet() -> Fernet:
    """Returns a configured Fernet cipher for encrypting access tokens at rest."""
    key = settings.token_encryption_key
    if not key or key == "generate_with_python_cryptography_fernet_generate_key":
        # Deterministic fallback key derived from jwt_secret_key in dev/test environments
        derived = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret_key.encode("utf-8")).digest())
        return Fernet(derived)
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)

def encrypt_token(token: str) -> str:
    """Encrypts cleartext token to an opaque ciphertext string."""
    f = get_fernet()
    return f.encrypt(token.encode("utf-8")).decode("utf-8")

def decrypt_token(encrypted: str) -> str:
    """Decrypts ciphertext back into the cleartext token string."""
    f = get_fernet()
    return f.decrypt(encrypted.encode("utf-8")).decode("utf-8")


# --- State & CSRF Token Helpers ---

STATE_TOKEN_EXPIRY_MINUTES = 10

def create_oauth_state(user_id: int) -> str:
    """Generates a signed, expiring state token tied directly to the authenticated user."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=STATE_TOKEN_EXPIRY_MINUTES)
    payload = {
        "user_id": user_id,
        "type": "instagram_oauth_state",
        "exp": expires,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

def verify_oauth_state(state: str) -> int:
    """
    Decodes and validates the OAuth state token.
    Returns user_id if valid; raises ValueError if tampered or expired.
    """
    try:
        payload = jwt.decode(state, settings.jwt_secret_key, algorithms=["HS256"])
        if payload.get("type") != "instagram_oauth_state":
            raise ValueError("Invalid OAuth state type")
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("Missing user_id in state payload")
        return int(user_id)
    except Exception as exc:
        raise ValueError(f"State verification failed: {exc}") from exc


# --- HTTP Helpers for Instagram / Meta APIs ---

def _http_post_form(url: str, form_data: dict[str, str], timeout: float = 10.0) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(form_data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "User-Agent": "ALIGN-Platform/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _http_get_json(url: str, params: dict[str, str] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    full_url = url
    if params:
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}" if "?" not in url else f"{url}&{query_string}"
    req = urllib.request.Request(
        full_url,
        headers={
            "User-Agent": "ALIGN-Platform/1.0",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# --- OAuth & Token Lifecycles ---

def build_instagram_authorize_url(user_id: int) -> str:
    """
    Constructs the official Instagram Login authorization URL.
    Scope: instagram_business_basic (minimum required for Business/Creator accounts).
    """
    if not settings.instagram_app_id or not settings.instagram_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Instagram integration is not configured on this server (missing app credentials).",
        )

    state = create_oauth_state(user_id)
    params = {
        "enable_fb_login": "0",
        "force_authentication": "1",
        "client_id": settings.instagram_app_id,
        "redirect_uri": settings.instagram_redirect_uri,
        "response_type": "code",
        "scope": "instagram_business_basic",
        "state": state,
    }
    return f"https://www.instagram.com/oauth/authorize?{urllib.parse.urlencode(params)}"

def exchange_code_for_short_lived_token(code: str) -> dict[str, Any]:
    """Exchanges an authorization code for a short-lived access token."""
    url = "https://api.instagram.com/oauth/access_token"
    form = {
        "client_id": settings.instagram_app_id or "",
        "client_secret": settings.instagram_app_secret or "",
        "grant_type": "authorization_code",
        "redirect_uri": settings.instagram_redirect_uri or "",
        "code": code,
    }
    try:
        return _http_post_form(url, form)
    except Exception as exc:
        logger.error("Failed to exchange Instagram authorization code: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate code with Instagram. The code may be invalid or expired.",
        ) from exc

def exchange_for_long_lived_token(short_lived_token: str) -> dict[str, Any]:
    """Exchanges a short-lived access token for a 60-day long-lived access token."""
    url = "https://graph.instagram.com/access_token"
    params = {
        "grant_type": "ig_exchange_token",
        "client_secret": settings.instagram_app_secret or "",
        "access_token": short_lived_token,
    }
    try:
        return _http_get_json(url, params)
    except Exception as exc:
        logger.error("Failed to exchange for long-lived Instagram token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to obtain long-lived token from Instagram Graph API.",
        ) from exc

def refresh_long_lived_token(token: str) -> dict[str, Any]:
    """Refreshes an active long-lived token before it expires (approx every 60 days)."""
    url = "https://graph.instagram.com/refresh_access_token"
    params = {
        "grant_type": "ig_refresh_token",
        "access_token": token,
    }
    try:
        return _http_get_json(url, params)
    except Exception as exc:
        logger.error("Failed to refresh Instagram long-lived token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to refresh Instagram token. Reconnect is required.",
        ) from exc


# --- Graph API: Profile & Media Fetching ---

def fetch_instagram_profile(access_token: str) -> dict[str, Any]:
    """Fetches user profile information (id, username, account_type) from Graph API."""
    url = "https://graph.instagram.com/me"
    params = {
        "fields": "id,username,account_type",
        "access_token": access_token,
    }
    try:
        return _http_get_json(url, params)
    except Exception as exc:
        logger.error("Failed to fetch Instagram profile: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve Instagram profile. Ensure the account is a Business or Creator account.",
        ) from exc

def fetch_instagram_media(access_token: str, max_items: int = 50) -> list[dict[str, Any]]:
    """Fetches recent user media items from Graph API with cursor pagination."""
    url = "https://graph.instagram.com/me/media"
    params = {
        "fields": "id,caption,media_type,media_url,permalink,timestamp,thumbnail_url",
        "access_token": access_token,
        "limit": "25",
    }

    all_media: list[dict[str, Any]] = []
    current_url: str | None = url
    current_params: dict[str, str] | None = params

    while current_url and len(all_media) < max_items:
        try:
            resp = _http_get_json(current_url, current_params)
        except Exception as exc:
            logger.warning("Error during Instagram media pagination: %s", exc)
            break

        data = resp.get("data", [])
        if not data:
            break
        all_media.extend(data)

        # Pagination cursor
        paging = resp.get("paging", {})
        next_page = paging.get("next")
        if next_page and len(all_media) < max_items:
            current_url = next_page
            current_params = None
        else:
            break

    return all_media[:max_items]


# --- Hashtag & Interest Inference ---

HASHTAG_REGEX = re.compile(r"#([a-zA-Z0-9_\u0080-\uffff]{2,40})")

# Noise / generic hashtags to filter out when extracting interest candidates
COMMON_NOISE_TAGS = {
    "instagram", "instagood", "photooftheday", "picoftheday", "love", "like",
    "follow", "likeforlikes", "followforfollowback", "me", "happy", "cute",
    "beautiful", "fashion", "repost", "instadaily", "viral", "explore",
    "foryou", "fyp", "trending", "selfie", "fun", "style", "smile"
}

def extract_hashtags_and_keywords(media_items: list[dict[str, Any]]) -> tuple[set[str], str]:
    """Extracts unique hashtags and aggregated caption text from media items."""
    extracted_tags: set[str] = set()
    caption_corpus: list[str] = []

    for item in media_items:
        caption = item.get("caption") or ""
        caption_corpus.append(caption)
        tags = HASHTAG_REGEX.findall(caption)
        for t in tags:
            clean = t.lower().strip()
            if len(clean) >= 3 and clean not in COMMON_NOISE_TAGS:
                extracted_tags.add(clean)

    return extracted_tags, " ".join(caption_corpus)

def infer_suggested_interests(tags: set[str], corpus: str) -> list[str]:
    """
    Infers candidate interest topics from extracted tags and caption corpus.
    Returns up to 8 clean, actionable suggested interests.
    """
    candidates = []
    for tag in sorted(tags):
        # Format tag to readable title e.g. "machinetlearning" -> "Machine Learning" or "photography" -> "Photography"
        formatted = tag.replace("_", " ").title()
        candidates.append(formatted)
        if len(candidates) >= 8:
            break
    return candidates


# --- High-Level Synchronization & Management ---

def sync_user_instagram(db: Session, user_id: int) -> dict[str, Any]:
    """
    Fetches latest profile and media for the user's connected Instagram account.
    - Decrypts token and handles token refreshes.
    - Upserts media records idempotently.
    - Generates embeddings for media and extracted hashtags.
    - If user consented to recommendations: infers suggested interests (marked pending).
    """
    account = db.scalar(select(InstagramAccount).where(InstagramAccount.user_id == user_id))
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Instagram account connected for this user.",
        )

    # Decrypt access token
    try:
        raw_token = decrypt_token(account.access_token_encrypted)
    except Exception as exc:
        account.status = "reconnect_needed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decryption of stored Instagram token failed. Reconnect is required.",
        ) from exc

    # Check expiration and attempt refresh if within 7 days
    now = datetime.now(timezone.utc)
    if account.token_expires_at and account.token_expires_at - now < timedelta(days=7):
        try:
            refreshed = refresh_long_lived_token(raw_token)
            raw_token = refreshed["access_token"]
            account.access_token_encrypted = encrypt_token(raw_token)
            expires_in_sec = refreshed.get("expires_in", 5184000)
            account.token_expires_at = now + timedelta(seconds=expires_in_sec)
            account.status = "connected"
        except Exception as exc:
            logger.warning("Token refresh failed during sync for user %s: %s", user_id, exc)
            account.status = "reconnect_needed"

    # Fetch profile information
    try:
        profile_data = fetch_instagram_profile(raw_token)
        account.instagram_user_id = profile_data.get("id") or account.instagram_user_id
        account.username = profile_data.get("username") or account.username
        account.account_type = profile_data.get("account_type") or account.account_type
    except Exception as exc:
        logger.warning("Could not fetch Instagram profile for user %s: %s", user_id, exc)

    # Fetch recent media
    media_items = fetch_instagram_media(raw_token, max_items=50)

    # Idempotent upsert of media items
    new_count = 0
    updated_count = 0

    for item in media_items:
        media_id = str(item.get("id"))
        if not media_id or not item.get("permalink"):
            continue

        caption = item.get("caption") or ""
        tags = HASHTAG_REGEX.findall(caption)
        hashtags_str = " ".join([f"#{t.lower()}" for t in tags])

        # Compute semantic embedding vector
        text_for_embedding = f"{caption} {hashtags_str}".strip()
        emb_vector = generate_embedding(text_for_embedding) if text_for_embedding else None

        # Parse timestamp
        raw_ts = item.get("timestamp")
        ts = None
        if raw_ts:
            try:
                ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            except Exception:
                pass

        media_url = item.get("media_url") or item.get("thumbnail_url") or ""

        existing_media = db.scalar(
            select(InstagramMedia).where(
                InstagramMedia.user_id == user_id,
                InstagramMedia.instagram_media_id == media_id,
            )
        )

        if existing_media:
            existing_media.caption = caption
            existing_media.media_type = item.get("media_type", "IMAGE")
            existing_media.media_url = media_url or existing_media.media_url
            existing_media.permalink = item.get("permalink") or existing_media.permalink
            existing_media.hashtags = hashtags_str
            existing_media.timestamp = ts or existing_media.timestamp
            if emb_vector is not None:
                existing_media.embedding = emb_vector
            updated_count += 1
        else:
            new_media = InstagramMedia(
                user_id=user_id,
                account_id=account.id,
                instagram_media_id=media_id,
                media_type=item.get("media_type", "IMAGE"),
                media_url=media_url,
                permalink=item.get("permalink", ""),
                caption=caption,
                timestamp=ts,
                hashtags=hashtags_str,
                embedding=emb_vector,
            )
            db.add(new_media)
            new_count += 1

    account.last_synced_at = now
    db.commit()

    # Inferred Suggested Interests (strictly opt-in via profile setting)
    user_prof = db.scalar(select(Profile).where(Profile.user_id == user_id))
    new_suggested_count = 0

    if user_prof and getattr(user_prof, "instagram_recommendations_enabled", False):
        extracted_tags, corpus = extract_hashtags_and_keywords(media_items)
        candidate_interests = infer_suggested_interests(extracted_tags, corpus)

        # Existing user interests
        existing_profile_interests = {
            i.strip().lower() for i in (user_prof.interests or "").split(",") if i.strip()
        }

        for candidate in candidate_interests:
            norm_cand = candidate.strip().lower()
            if norm_cand in existing_profile_interests:
                continue

            already_suggested = db.scalar(
                select(SuggestedInterest).where(
                    SuggestedInterest.user_id == user_id,
                    SuggestedInterest.interest.ilike(candidate.strip()),
                )
            )

            if not already_suggested:
                new_sug = SuggestedInterest(
                    user_id=user_id,
                    interest=candidate.strip(),
                    source="instagram",
                    source_detail=f"Inferred from recent #{norm_cand.replace(' ', '')} posts on Instagram",
                    status="pending",
                )
                db.add(new_sug)
                new_suggested_count += 1

        db.commit()

    return {
        "status": "success",
        "username": account.username,
        "account_type": account.account_type,
        "synced_count": len(media_items),
        "new_media_saved": new_count,
        "updated_media": updated_count,
        "new_suggested_interests": new_suggested_count,
        "last_synced_at": account.last_synced_at.isoformat() if account.last_synced_at else None,
    }

def disconnect_user_instagram(db: Session, user_id: int) -> dict[str, Any]:
    """
    Disconnects Instagram account and completely purges stored tokens,
    media records, and pending suggested interests for the user.
    """
    account = db.scalar(select(InstagramAccount).where(InstagramAccount.user_id == user_id))
    deleted_media_count = 0

    if account:
        # Delete associated media
        media_records = list(db.scalars(select(InstagramMedia).where(InstagramMedia.user_id == user_id)))
        deleted_media_count = len(media_records)
        for m in media_records:
            db.delete(m)

        # Delete account (purging encrypted access token)
        db.delete(account)

    # Delete pending suggested interests from instagram
    pending_sug = list(db.scalars(
        select(SuggestedInterest).where(
            SuggestedInterest.user_id == user_id,
            SuggestedInterest.source == "instagram",
            SuggestedInterest.status == "pending",
        )
    ))
    for s in pending_sug:
        db.delete(s)

    # Reset profile preferences
    user_prof = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if user_prof:
        user_prof.instagram_recommendations_enabled = False
        user_prof.instagram_profile_visible = False

    db.commit()
    return {
        "status": "success",
        "message": f"Successfully disconnected Instagram account and removed {deleted_media_count} stored media records.",
    }


# --- Meta Deauthorization & Data Deletion Signatures ---

def generate_signed_request(payload: dict, secret: str) -> str:
    """Helper to generate a Meta-compliant signed_request (encoded_sig.payload)."""
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_encoded = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(
        secret.encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_encoded = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    return f"{sig_encoded}.{payload_encoded}"


def parse_and_verify_meta_signed_request(signed_request: str) -> dict[str, Any]:
    """
    Verifies the HMAC-SHA256 signature of a Meta signed_request parameter.
    Raises ValueError if signature is invalid or secret is missing.
    """
    if not settings.instagram_app_secret:
        raise ValueError("Cannot verify signed_request: INSTAGRAM_APP_SECRET is not configured.")

    parts = signed_request.split(".", 1)
    if len(parts) != 2:
        raise ValueError("Invalid signed_request format (expected encoded_sig.payload)")

    encoded_sig, payload_encoded = parts

    # Base64url decode signature and payload
    def b64url_decode(inp: str) -> bytes:
        padding = "=" * ((4 - len(inp) % 4) % 4)
        return base64.urlsafe_b64decode((inp + padding).encode("utf-8"))

    try:
        sig = b64url_decode(encoded_sig)
        payload_bytes = b64url_decode(payload_encoded)
        data = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to decode signed_request payload: {exc}") from exc

    # Verify signature
    expected_sig = hmac.new(
        settings.instagram_app_secret.encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("Signed request signature verification failed.")

    return data

def handle_meta_deauthorization(db: Session, instagram_user_id: str) -> bool:
    """Handles Meta's deauthorization callback by purging stored user data."""
    account = db.scalar(select(InstagramAccount).where(InstagramAccount.instagram_user_id == instagram_user_id))
    if not account:
        return False
    disconnect_user_instagram(db, account.user_id)
    return True

def handle_meta_data_deletion(db: Session, instagram_user_id: str) -> tuple[str, str]:
    """
    Handles Meta's data deletion callback:
    Deletes user data and returns (confirmation_code, status_url).
    """
    code = f"del_{hashlib.sha256((instagram_user_id + str(datetime.now())).encode()).hexdigest()[:16]}"
    account = db.scalar(select(InstagramAccount).where(InstagramAccount.instagram_user_id == instagram_user_id))
    if account:
        disconnect_user_instagram(db, account.user_id)

    status_url = f"{settings.cors_origins.split(',')[0]}/privacy?deletion_code={code}"
    return code, status_url
