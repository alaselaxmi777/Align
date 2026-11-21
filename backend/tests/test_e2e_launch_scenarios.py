import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def register_user(client: TestClient, prefix: str):
    uid = uuid.uuid4().hex[:8]
    email = f"{prefix}_{uid}@example.com"
    pwd = "SecurePassword123!"
    reg = client.post("/api/v1/auth/register", json={
        "name": f"User {prefix} {uid}",
        "email": email,
        "password": pwd
    })
    assert reg.status_code == 201

    login = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": pwd
    })
    assert login.status_code == 200
    data = login.json()
    token = data["access_token"]
    refresh = data["refresh_token"]
    return {
        "uid": uid,
        "email": email,
        "password": pwd,
        "token": token,
        "refresh_token": refresh,
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": data["user_id"]
    }

def test_e2e_full_launch_scenario(client: TestClient, db: Session):
    """
    Complete end-to-end scenario:
    1. User 1 registers and completes 4-step onboarding.
    2. User 1 creates post & reel.
    3. User 2 registers, onboarded, views User 1's post & reel.
    4. User 2 sends connection request; User 1 accepts.
    5. User 2 likes and comments on User 1's post & reel.
    6. User 1 edits post; User 2 is blocked (403).
    7. User 1 logs out and logs in again with persistent session.
    """
    # 1. Register User 1
    u1 = register_user(client, "alice")
    u1_handle = f"alice_{u1['uid']}"

    # Step 1: Claim Handle
    check_res = client.get(f"/api/v1/users/check-username?username={u1_handle}")
    assert check_res.status_code == 200
    assert check_res.json()["available"] is True

    s1 = client.post("/api/v1/auth/onboarding", json={"username": u1_handle, "step": 2}, headers=u1["headers"])
    assert s1.status_code == 200

    # Step 2: Name & Bio
    s2 = client.post("/api/v1/auth/onboarding", json={
        "name": f"Alice {u1['uid']}",
        "bio": "AI engineer focused on semantic vector discovery.",
        "avatar_url": "https://example.com/alice.webp",
        "step": 3
    }, headers=u1["headers"])
    assert s2.status_code == 200

    # Step 3: Demographics & Regional Hub
    s3 = client.post("/api/v1/auth/onboarding", json={
        "age_cohort": "25-34",
        "gender": "Female",
        "preferred_language": "English",
        "location": "Pune",
        "privacy_level": "public",
        "step": 3
    }, headers=u1["headers"])
    assert s3.status_code == 200

    # Step 4: Skills & Finalize
    s4 = client.post("/api/v1/auth/onboarding", json={
        "username": u1_handle,
        "name": f"Alice {u1['uid']}",
        "skills": "Python, Machine Learning, FastApi",
        "skill_proficiency": "Advanced",
        "hobbies": "Trekking, Photography",
        "interests": "Artificial Intelligence",
        "goals": "Build scalable discovery engines",
        "step": 4
    }, headers=u1["headers"])
    assert s4.status_code == 200
    assert s4.json()["onboarding_completed"] is True

    # 2. User 1 creates an image post
    post_res = client.post("/api/v1/feed", json={
        "content": "Sunset over Sinhagad Fort after a great hike! #nature #pune",
        "image_url": "https://example.com/sinhagad.webp",
        "location_area": "Pune",
        "visibility": "public"
    }, headers=u1["headers"])
    assert post_res.status_code == 201
    post_id = post_res.json()["id"]

    # User 1 creates a reel
    reel_res = client.post("/api/v1/reels", json={
        "title": "Sinhagad Foggy Trails",
        "category": "Fort Trekking",
        "video_url": "https://example.com/trail.mp4",
        "thumbnail_url": "https://example.com/trail_poster.webp",
        "duration_seconds": 28.5,
        "visibility": "public",
        "caption": "Rainy trail exploration in Pune hills",
        "tags": ["trekking", "pune"]
    }, headers=u1["headers"])
    assert reel_res.status_code == 201
    reel_id = reel_res.json()["id"]

    # 3. Register User 2
    u2 = register_user(client, "bob")
    u2_handle = f"bob_{u2['uid']}"

    # User 2 full onboarding in one shot
    client.post("/api/v1/auth/onboarding", json={
        "username": u2_handle,
        "name": f"Bob {u2['uid']}",
        "bio": "Cloud architect & mobile app enthusiast.",
        "skills": "DevOps, Docker, Kubernetes",
        "goals": "Connect with ML developers",
        "step": 4
    }, headers=u2["headers"])

    # User 2 views feed (contains Alice's post)
    feed_res = client.get("/api/v1/feed", headers=u2["headers"])
    assert feed_res.status_code == 200
    feed_ids = [p["id"] for p in feed_res.json()]
    assert post_id in feed_ids

    # User 2 views reels (contains Alice's reel)
    reels_res = client.get("/api/v1/reels", headers=u2["headers"])
    assert reels_res.status_code == 200
    reel_ids = [r["id"] for r in reels_res.json()]
    assert reel_id in reel_ids

    # User 2 views Alice's profile by ID and by Handle
    p_by_id = client.get(f"/api/v1/users/{u1['user_id']}", headers=u2["headers"])
    assert p_by_id.status_code == 200
    assert p_by_id.json()["email"] is None  # Private email protected
    assert p_by_id.json()["username"] == u1_handle

    p_by_handle = client.get(f"/api/v1/users/handle/{u1_handle}", headers=u2["headers"])
    assert p_by_handle.status_code == 200
    assert p_by_handle.json()["id"] == u1["user_id"]

    # 4. User 2 connects with User 1
    conn_req = client.post(f"/api/v1/users/{u1['user_id']}/connect", headers=u2["headers"])
    assert conn_req.status_code == 200
    conn_id = conn_req.json().get("connection_id")

    # User 1 accepts connection
    accept_res = client.post(f"/api/v1/users/connections/{conn_id}/accept", headers=u1["headers"])
    assert accept_res.status_code == 200

    # 5. User 2 likes & comments on Alice's post
    like_res = client.post(f"/api/v1/feed/{post_id}/like", headers=u2["headers"])
    assert like_res.status_code == 200
    assert like_res.json()["is_liked"] is True

    comm_res = client.post(f"/api/v1/feed/{post_id}/comments", json={
        "content": "Incredible shot! What trail did you take?"
    }, headers=u2["headers"])
    assert comm_res.status_code == 201

    # User 2 likes & comments on Alice's reel
    r_like = client.post(f"/api/v1/reels/{reel_id}/like", headers=u2["headers"])
    assert r_like.status_code == 200
    assert r_like.json()["is_liked"] is True

    r_comm = client.post(f"/api/v1/reels/{reel_id}/comments", json={
        "content": "The fog looks amazing!"
    }, headers=u2["headers"])
    assert r_comm.status_code == 201

    # 6. User 1 edits their post; User 2 attempt returns 403
    u1_edit = client.put(f"/api/v1/feed/{post_id}", json={
        "content": "Updated: Sunset over Sinhagad Fort (Kalyan Darwaza route) #nature #pune"
    }, headers=u1["headers"])
    assert u1_edit.status_code == 200

    u2_edit = client.put(f"/api/v1/feed/{post_id}", json={
        "content": "Malicious edit attempt by Bob"
    }, headers=u2["headers"])
    assert u2_edit.status_code == 403

    # 7. User 1 logs out and logs in again
    logout_res = client.post("/api/v1/auth/logout", json={"refresh_token": u1["refresh_token"]}, headers=u1["headers"])
    assert logout_res.status_code == 200

    # Revoked refresh token cannot be reused
    reuse_attempt = client.post("/api/v1/auth/refresh", json={"refresh_token": u1["refresh_token"]})
    assert reuse_attempt.status_code == 401

    # Login with credentials restores active session
    re_login = client.post("/api/v1/auth/login", json={
        "email": u1["email"],
        "password": u1["password"]
    })
    assert re_login.status_code == 200
    assert re_login.json()["onboarding_completed"] is True

def test_e2e_edge_cases(client: TestClient, db: Session):
    """
    Edge case validation:
    1. Duplicate username collision.
    2. Over-length reel duration rejection (>90s).
    3. Tampered JWT signature rejection.
    4. Resumable mid-onboarding progress.
    """
    # 1. Duplicate username
    u = register_user(client, "collision_tester")
    existing_claim = client.post("/api/v1/auth/onboarding", json={"username": "super_star", "step": 2}, headers=u["headers"])
    assert existing_claim.status_code == 200

    # Second user tries to claim same handle
    u2 = register_user(client, "collision_intruder")
    check_dup = client.get("/api/v1/users/check-username?username=SUPER_STAR")
    assert check_dup.status_code == 200
    assert check_dup.json()["available"] is False

    # 2. Over-length reel duration
    bad_reel = client.post("/api/v1/reels", json={
        "title": "Too Long Video",
        "category": "Technology",
        "video_url": "https://example.com/long.mp4",
        "thumbnail_url": "https://example.com/poster.webp",
        "duration_seconds": 120.0,
    }, headers=u["headers"])
    assert bad_reel.status_code in [400, 422]

    # 3. Tampered JWT signature
    bad_auth = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.tampered.token"})
    assert bad_auth.status_code == 401

    # 4. Resumable mid-onboarding persistence
    u3 = register_user(client, "resume_tester")
    client.post("/api/v1/auth/onboarding", json={"username": f"resume_{u3['uid']}", "step": 2}, headers=u3["headers"])
    client.post("/api/v1/auth/onboarding", json={"name": "Partial User", "bio": "Halfway through setup...", "step": 3}, headers=u3["headers"])

    # Fetch /auth/me to verify saved step
    me_res = client.get("/api/v1/auth/me", headers=u3["headers"])
    assert me_res.status_code == 200
    assert me_res.json()["profile"]["onboarding_step"] == 3
    assert me_res.json()["profile"]["onboarding_completed"] is False
