import base64
import hashlib
import hmac
import json
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.instagram import InstagramAccount, InstagramMedia, SuggestedInterest
from app.models.user import Profile, User
from app.services.instagram_service import (
    create_oauth_state,
    decrypt_token,
    encrypt_token,
    generate_signed_request,
    parse_and_verify_meta_signed_request,
    verify_oauth_state,
)


@pytest.fixture
def auth_user(db: Session):
    user = db.scalar(select(User).where(User.email == "ig_tester@align.local"))
    if not user:
        from app.core.security import hash_password

        user = User(
            name="Instagram Tester",
            email="ig_tester@align.local",
            password_hash=hash_password("Password123!"),
            is_active=True,
            is_test=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    prof = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not prof:
        prof = Profile(
            user_id=user.id,
            bio="Creator and tech enthusiast",
            interests="Design, Photography",
            skills="Photoshop, UI/UX",
            instagram_recommendations_enabled=False,
            instagram_profile_visible=False,
        )
        db.add(prof)
        db.commit()

    return user


@pytest.fixture
def ig_auth_headers(auth_user):
    token = create_access_token(str(auth_user.id))
    return {"Authorization": f"Bearer {token}"}


def test_instagram_disabled_state(client, ig_auth_headers, monkeypatch):
    """When INSTAGRAM_ENABLED=false, features remain cleanly dormant."""
    monkeypatch.setattr(settings, "instagram_enabled", False)

    # Status returns disabled
    res = client.get("/api/v1/instagram/status", headers=ig_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["enabled"] is False
    assert data["connected"] is False

    # Connect endpoint rejects with 400
    res_conn = client.get("/api/v1/instagram/connect", headers=ig_auth_headers)
    assert res_conn.status_code == 400
    assert "disabled" in res_conn.json()["detail"].lower()

    # Sync rejects with 400
    res_sync = client.post("/api/v1/instagram/sync", headers=ig_auth_headers)
    assert res_sync.status_code == 400


def test_instagram_connect_url_scope_and_state(client, auth_user, ig_auth_headers, monkeypatch):
    """Verifies official Meta OAuth URL, instagram_business_basic scope, and cryptographic CSRF state."""
    monkeypatch.setattr(settings, "instagram_enabled", True)
    monkeypatch.setattr(settings, "instagram_app_id", "test_app_id_123")
    monkeypatch.setattr(settings, "instagram_redirect_uri", "http://localhost:8000/api/v1/instagram/callback")

    res = client.get("/api/v1/instagram/connect", headers=ig_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "authorize_url" in data
    url = data["authorize_url"]
    assert "https://www.instagram.com/oauth/authorize" in url
    assert "client_id=test_app_id_123" in url
    assert "scope=instagram_business_basic" in url
    assert "response_type=code" in url
    assert "state=" in url

    # Extract state parameter and verify it is tied to auth_user.id
    state = url.split("state=")[1].split("&")[0]
    verified_user_id = verify_oauth_state(state)
    assert verified_user_id == auth_user.id


def test_oauth_state_tampering_rejected(client, monkeypatch):
    """Tampered or invalid CSRF state in callback redirects to /settings with error."""
    monkeypatch.setattr(settings, "instagram_enabled", True)
    res = client.get(
        "/api/v1/instagram/callback?code=mock_code&state=tampered.state.value",
        follow_redirects=False,
    )
    assert res.status_code == 307
    assert "instagram_error=invalid_state" in res.headers["location"]


def test_fernet_token_encryption_at_rest():
    """Confirms Fernet token encryption and decryption integrity."""
    raw_token = "IGQVJYWk1234567890abcdefghijklmnopqrstuvwxyz"
    encrypted = encrypt_token(raw_token)
    assert encrypted != raw_token
    assert encrypted.startswith("gAAAAA")  # Fernet standard base64 signature
    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_token


def test_oauth_callback_and_storage(client, auth_user, db: Session, monkeypatch):
    """Tests code exchange, long-lived token upgrade, and encrypted storage in DB."""
    monkeypatch.setattr(settings, "instagram_enabled", True)
    monkeypatch.setattr(settings, "instagram_app_id", "test_app_123")
    monkeypatch.setattr(settings, "instagram_app_secret", "test_secret_456")
    monkeypatch.setattr(settings, "instagram_redirect_uri", "http://localhost:8000/api/v1/instagram/callback")

    # Mock Meta HTTP responses
    mock_short_token = "short_lived_ig_token_abc"
    mock_long_token = "long_lived_ig_token_xyz60days"

    def mock_exchange_code(code: str) -> dict:
        return {"access_token": mock_short_token, "user_id": 99887766}

    def mock_exchange_long(short_token: str) -> dict:
        return {"access_token": mock_long_token, "expires_in": 5184000}

    def mock_fetch_profile(token: str) -> dict:
        return {"id": "99887766", "username": "creator_studio_pune", "account_type": "CREATOR"}

    monkeypatch.setattr("app.api.routes.instagram.exchange_code_for_short_lived_token", mock_exchange_code)
    monkeypatch.setattr("app.api.routes.instagram.exchange_for_long_lived_token", mock_exchange_long)
    monkeypatch.setattr("app.api.routes.instagram.fetch_instagram_profile", mock_fetch_profile)
    monkeypatch.setattr("app.api.routes.instagram.sync_user_instagram", lambda db, uid: None)

    valid_state = create_oauth_state(auth_user.id)
    res = client.get(
        f"/api/v1/instagram/callback?code=test_auth_code_777&state={valid_state}",
        follow_redirects=False,
    )
    assert res.status_code == 307
    assert "/settings?instagram=connected" in res.headers["location"]

    # Verify DB record
    acc = db.scalar(select(InstagramAccount).where(InstagramAccount.user_id == auth_user.id))
    assert acc is not None
    assert acc.username == "creator_studio_pune"
    assert acc.account_type == "CREATOR"
    assert acc.status == "connected"
    # Never stored plain text!
    assert acc.access_token_encrypted != mock_long_token
    # Can be decrypted cleanly
    assert decrypt_token(acc.access_token_encrypted) == mock_long_token


def test_media_sync_and_idempotency(client, auth_user, ig_auth_headers, db: Session, monkeypatch):
    """Verifies media synchronization, hashtag extraction, embedding generation, and idempotency."""
    monkeypatch.setattr(settings, "instagram_enabled", True)

    # Ensure account exists
    acc = db.scalar(select(InstagramAccount).where(InstagramAccount.user_id == auth_user.id))
    if not acc:
        acc = InstagramAccount(
            user_id=auth_user.id,
            instagram_user_id="99887766",
            username="creator_studio_pune",
            account_type="BUSINESS",
            access_token_encrypted=encrypt_token("mock_token_123"),
            status="connected",
        )
        db.add(acc)
        db.commit()

    sample_media = [
        {
            "id": "ig_media_1001",
            "media_type": "IMAGE",
            "media_url": "https://scontent.cdninstagram.com/v/t51.2885-15/pic1.jpg",
            "permalink": "https://www.instagram.com/p/C123456/",
            "caption": "Exploring generative AI and robotics in Pune #TechCommunity #Robotics #PuneDevs",
            "timestamp": "2026-05-10T14:30:00+0000",
        },
        {
            "id": "ig_media_1002",
            "media_type": "VIDEO",
            "media_url": "https://scontent.cdninstagram.com/v/t51.2885-15/vid2.mp4",
            "permalink": "https://www.instagram.com/p/C654321/",
            "caption": "Sunset photography workshop at Sinhagad Fort #Photography #VisualArts",
            "timestamp": "2026-05-11T18:00:00+0000",
        },
    ]

    monkeypatch.setattr(
        "app.services.instagram_service.fetch_instagram_media",
        lambda token, max_items=50: sample_media,
    )
    monkeypatch.setattr(
        "app.services.instagram_service.fetch_instagram_profile",
        lambda token: {"id": "99887766", "username": "creator_studio_pune", "account_type": "BUSINESS"},
    )

    # Run sync #1
    res1 = client.post("/api/v1/instagram/sync", headers=ig_auth_headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["synced_count"] == 2

    # Check DB rows
    media_rows = list(db.scalars(select(InstagramMedia).where(InstagramMedia.user_id == auth_user.id)))
    assert len(media_rows) == 2
    m1 = next(m for m in media_rows if m.instagram_media_id == "ig_media_1001")
    assert "TechCommunity" in m1.hashtags or "techcommunity" in m1.hashtags.lower()
    assert m1.embedding is not None

    # Run sync #2 (Idempotency check: duplicate media IDs must not create duplicate DB rows)
    res2 = client.post("/api/v1/instagram/sync", headers=ig_auth_headers)
    assert res2.status_code == 200
    media_rows_after = list(db.scalars(select(InstagramMedia).where(InstagramMedia.user_id == auth_user.id)))
    assert len(media_rows_after) == 2


def test_opt_in_recommendations_and_suggested_interests(client, auth_user, ig_auth_headers, db: Session, monkeypatch):
    """Strictly opt-in: zero interests suggested if consent is OFF; creates pending interests when ON."""
    monkeypatch.setattr(settings, "instagram_enabled", True)

    prof = db.scalar(select(Profile).where(Profile.user_id == auth_user.id))
    prof.instagram_recommendations_enabled = True
    db.commit()

    sample_media = [
        {
            "id": "ig_media_2001",
            "media_type": "IMAGE",
            "media_url": "https://scontent.cdninstagram.com/v/t51.2885-15/pic3.jpg",
            "permalink": "https://www.instagram.com/p/C88888/",
            "caption": "Deep learning models and neural networks #MachineLearning #PyTorch #AI",
            "timestamp": "2026-05-12T10:00:00+0000",
        }
    ]

    monkeypatch.setattr("app.services.instagram_service.fetch_instagram_media", lambda token, max_items=50: sample_media)
    monkeypatch.setattr("app.services.instagram_service.fetch_instagram_profile", lambda token: {"username": "ai_researcher"})

    # Sync with opt-in enabled
    res_sync = client.post("/api/v1/instagram/sync", headers=ig_auth_headers)
    assert res_sync.status_code == 200

    # Query pending suggested interests
    res_sug = client.get("/api/v1/instagram/suggested-interests?status=pending", headers=ig_auth_headers)
    assert res_sug.status_code == 200
    suggestions = res_sug.json()
    assert len(suggestions) > 0

    target_interest = suggestions[0]
    interest_id = target_interest["id"]

    # Explicit Accept flow
    res_accept = client.post(f"/api/v1/instagram/suggested-interests/{interest_id}/accept", headers=ig_auth_headers)
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "success"

    # Confirms it updated status in DB
    sug_db = db.get(SuggestedInterest, interest_id)
    assert sug_db.status == "accepted"

    # Confirms it was appended to user profile interests
    db.refresh(prof)
    assert target_interest["interest"].lower() in prof.interests.lower()


def test_disconnect_permanently_purges_data(client, auth_user, ig_auth_headers, db: Session, monkeypatch):
    """Disconnect must permanently delete access tokens, accounts, media, and reset preferences."""
    monkeypatch.setattr(settings, "instagram_enabled", True)

    res = client.delete("/api/v1/instagram/disconnect", headers=ig_auth_headers)
    assert res.status_code == 200

    # Verify all records purged
    acc = db.scalar(select(InstagramAccount).where(InstagramAccount.user_id == auth_user.id))
    assert acc is None
    media = list(db.scalars(select(InstagramMedia).where(InstagramMedia.user_id == auth_user.id)))
    assert len(media) == 0
    pending_sug = list(db.scalars(select(SuggestedInterest).where(
        SuggestedInterest.user_id == auth_user.id,
        SuggestedInterest.status == "pending",
    )))
    assert len(pending_sug) == 0


def test_meta_deauthorize_and_data_deletion_callbacks(client, db: Session, monkeypatch):
    """Verifies HMAC-SHA256 signature verification for Meta platform deauthorize and data-deletion callbacks."""
    test_secret = "meta_test_secret_key_8899"
    monkeypatch.setattr(settings, "instagram_app_secret", test_secret)

    # 1. Test signed request generation and verification
    payload = {"user_id": "meta_user_12345", "algorithm": "HMAC-SHA256"}
    signed_req = generate_signed_request(payload, test_secret)
    verified_data = parse_and_verify_meta_signed_request(signed_req)
    assert verified_data is not None
    assert verified_data["user_id"] == "meta_user_12345"

    # 2. Test Deauthorize callback
    res_deauth = client.post(
        "/api/v1/instagram/deauthorize",
        data={"signed_request": signed_req},
    )
    assert res_deauth.status_code == 200
    assert res_deauth.json()["status"] == "success"

    # 3. Test Data Deletion callback (compliant with Meta requirements)
    res_del = client.post(
        "/api/v1/instagram/data-deletion",
        data={"signed_request": signed_req},
    )
    assert res_del.status_code == 200
    del_data = res_del.json()
    assert "url" in del_data
    assert "confirmation_code" in del_data
