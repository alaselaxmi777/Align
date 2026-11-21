import io
import time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User
from app.models.reel import Reel, ReelLike, ReelComment
from app.models.assistant import AssistantConversation
from app.models.goal_journey import GoalJourney, GoalMilestone
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.core.rate_limit import _limiter

def test_reels_database_persistence_and_likes(client: TestClient, db: Session):
    # Setup test user
    email = f"reel_creator_{int(time.time() * 1000)}@align.local"
    user = User(name="Reel Creator", email=email, password_hash=hash_password("Pass123!"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Reel via API
    create_resp = client.post(
        "/api/v1/reels",
        headers=headers,
        json={
            "title": "Autonomous AI Agent Architecture",
            "category": "Technology",
            "video_url": "https://assets.mixkit.co/test_agent.mp4",
            "thumbnail_url": "https://images.pexels.com/test_thumb.jpeg",
            "caption": "Testing full database persistence for reels.",
            "audio_track": "Tech Beats · Original",
            "tags": ["ai", "agents", "postgres"]
        }
    )
    assert create_resp.status_code == 201, create_resp.text
    reel_data = create_resp.json()
    reel_id = reel_data["id"]
    assert reel_data["title"] == "Autonomous AI Agent Architecture"
    assert reel_data["author_name"] == "Reel Creator"

    # 2. Verify directly in PostgreSQL
    db_reel = db.get(Reel, reel_id)
    assert db_reel is not None
    assert db_reel.author_id == user.id
    assert db_reel.category == "Technology"

    # 3. Retrieve list from API
    list_resp = client.get("/api/v1/reels?category=Technology")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(r["id"] == reel_id for r in items)

    # 4. Like the Reel
    like_resp = client.post(f"/api/v1/reels/{reel_id}/like", headers=headers)
    assert like_resp.status_code == 200
    assert like_resp.json()["is_liked"] is True
    assert like_resp.json()["likes_count"] == 1

    # Verify like exists in PostgreSQL
    db_like = db.scalar(select(ReelLike).where(ReelLike.reel_id == reel_id, ReelLike.user_id == user.id))
    assert db_like is not None

    # Unlike the Reel
    unlike_resp = client.post(f"/api/v1/reels/{reel_id}/like", headers=headers)
    assert unlike_resp.status_code == 200
    assert unlike_resp.json()["is_liked"] is False
    assert unlike_resp.json()["likes_count"] == 0

    # 5. Add a comment
    comment_resp = client.post(
        f"/api/v1/reels/{reel_id}/comments",
        headers=headers,
        json={"content": "Incredible database-backed reel!"}
    )
    assert comment_resp.status_code == 201
    cid = comment_resp.json()["id"]

    # Verify comment in PostgreSQL
    db_comment = db.get(ReelComment, cid)
    assert db_comment is not None
    assert db_comment.content == "Incredible database-backed reel!"

    # 6. Retrieve comments via API
    get_comm_resp = client.get(f"/api/v1/reels/{reel_id}/comments")
    assert get_comm_resp.status_code == 200
    assert len(get_comm_resp.json()) >= 1
    assert get_comm_resp.json()[0]["content"] == "Incredible database-backed reel!"

def test_token_refresh_lifecycle(client: TestClient, db: Session):
    email = f"refresh_user_{int(time.time() * 1000)}@align.local"
    user = User(name="Refresh User", email=email, password_hash=hash_password("Pass123!"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    # 1. Login to receive access and refresh tokens
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Pass123!"}
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    refresh_token = tokens["refresh_token"]

    # 2. Use refresh token to obtain fresh access token
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    new_access = new_tokens["access_token"]

    # 3. Verify new access token works for authenticated endpoints
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email

    # 4. Invalid refresh token rejected
    bad_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_or_forged_refresh_token_string_here"}
    )
    assert bad_resp.status_code == 401

def test_rate_limiting_defense(client: TestClient):
    _limiter.reset()
    # Trigger repeated login attempts from same IP
    status_codes = []
    for _ in range(25):
        r = client.post(
            "/api/v1/auth/login",
            headers={"X-Test-Rate-Limit": "enforce"},
            json={"email": "nonexistent@align.local", "password": "WrongPassword!"}
        )
        status_codes.append(r.status_code)

    # The first 15 requests should be 401 Unauthorized, subsequent should be 429 Too Many Requests
    assert 429 in status_codes
    assert status_codes[-1] == 429
    _limiter.reset()

def test_upload_magic_bytes_spoofing_prevention(client: TestClient, db: Session):
    user = User(name="Uploader", email=f"upload_{int(time.time() * 1000)}@align.local", password_hash="pass", is_active=True)
    db.add(user)
    db.commit()
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Malicious executable with declared image/png header
    fake_png = b"#!/bin/bash\nrm -rf / --no-preserve-root\necho 'hacked'\n"
    bad_upload = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("malicious.png", io.BytesIO(fake_png), "image/png")}
    )
    assert bad_upload.status_code == 400
    assert "file spoofing detected" in bad_upload.text.lower()

    # 2. Genuine PNG file with valid 8-byte PNG signature
    # Signature: 89 50 4E 47 0D 0A 1A 0A
    valid_png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    good_upload = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("valid.png", io.BytesIO(valid_png_header), "image/png")}
    )
    assert good_upload.status_code == 201
    assert "url" in good_upload.json()

def test_cross_user_privacy_and_isolation(client: TestClient, db: Session):
    u1 = User(name="Alice", email=f"alice_{int(time.time() * 1000)}@align.local", password_hash="pass", is_active=True)
    u2 = User(name="Bob", email=f"bob_{int(time.time() * 1000)}@align.local", password_hash="pass", is_active=True)
    db.add_all([u1, u2])
    db.commit()

    token1 = create_access_token(str(u1.id))
    token2 = create_access_token(str(u2.id))

    # 1. Alice creates an Assistant conversation
    conv = AssistantConversation(user_id=u1.id, title="Alice Secret Session")
    db.add(conv)
    db.commit()

    # Bob attempting to read Alice's conversation returns 404
    bob_req = client.get(
        f"/api/v1/assistant/conversations/{conv.id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert bob_req.status_code == 404

    # 2. Alice creates a Goal Journey
    journey = GoalJourney(user_id=u1.id, title="Alice Career Roadmap", target_category="Career")
    db.add(journey)
    db.commit()

    # Bob attempting to read or modify Alice's goal journey returns 404
    bob_journey_req = client.get(
        f"/api/v1/goals/{journey.id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert bob_journey_req.status_code == 404

    # 3. Alice creates a Reel
    reel = Reel(
        title="Alice Tech Reel",
        category="Technology",
        video_url="https://mixkit.co/v.mp4",
        thumbnail_url="https://mixkit.co/t.jpeg",
        author_id=u1.id,
        author_name=u1.name,
    )
    db.add(reel)
    db.commit()

    # Bob attempting to delete Alice's reel returns 403 Forbidden
    bob_del = client.delete(
        f"/api/v1/reels/{reel.id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert bob_del.status_code == 403
