import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def register_and_login(client: TestClient, prefix: str):
    uid = uuid.uuid4().hex[:8]
    email = f"{prefix}_{uid}@example.com"
    pwd = "Password123!"
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
    token = login.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}, "email": email}

def test_author_post_crud_and_forbidden_for_others(client: TestClient, db: Session):
    user_a = register_and_login(client, "author_a")
    user_b = register_and_login(client, "intruder_b")

    # 1. User A creates a post
    post_res = client.post(
        "/api/v1/feed",
        json={
            "content": "Original Post Content by User A #tech",
            "image_url": "https://example.com/original.jpg",
            "location_area": "Pune"
        },
        headers=user_a["headers"]
    )
    assert post_res.status_code == 201
    post_id = post_res.json()["id"]

    # 2. User A successfully edits their own post
    edit_res = client.put(
        f"/api/v1/feed/{post_id}",
        json={"content": "Updated Post Content by User A #tech #updated"},
        headers=user_a["headers"]
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["content"] == "Updated Post Content by User A #tech #updated"

    # 3. User B attempts to edit User A's post -> 403 Forbidden
    b_edit_res = client.put(
        f"/api/v1/feed/{post_id}",
        json={"content": "Hacked content by User B"},
        headers=user_b["headers"]
    )
    assert b_edit_res.status_code == 403
    assert "own posts" in b_edit_res.json()["detail"].lower()

    # 4. User B attempts to delete User A's post -> 403 Forbidden
    b_del_res = client.delete(
        f"/api/v1/feed/{post_id}",
        headers=user_b["headers"]
    )
    assert b_del_res.status_code == 403
    assert "own posts" in b_del_res.json()["detail"].lower()

    # 5. User A successfully deletes their own post -> 200 OK
    a_del_res = client.delete(
        f"/api/v1/feed/{post_id}",
        headers=user_a["headers"]
    )
    assert a_del_res.status_code == 200
    assert a_del_res.json()["status"] == "ok"

    # 6. Deleting already deleted post returns 404
    a_del_again = client.delete(
        f"/api/v1/feed/{post_id}",
        headers=user_a["headers"]
    )
    assert a_del_again.status_code == 404

def test_author_reel_crud_and_forbidden_for_others(client: TestClient, db: Session):
    user_a = register_and_login(client, "reel_a")
    user_b = register_and_login(client, "reel_b")

    # 1. User A creates a reel
    reel_res = client.post(
        "/api/v1/reels",
        json={
            "title": "Amazing Trek at Sinhagad",
            "category": "Fort Trekking",
            "video_url": "https://example.com/reel1.mp4",
            "thumbnail_url": "https://example.com/thumb1.jpg",
            "duration_seconds": 25.0,
            "visibility": "public",
            "caption": "Rainy morning trek in Pune",
            "tags": ["trek", "maharashtra"]
        },
        headers=user_a["headers"]
    )
    assert reel_res.status_code == 201
    reel_id = reel_res.json()["id"]

    # 2. User A successfully edits reel caption
    edit_res = client.put(
        f"/api/v1/reels/{reel_id}",
        json={"caption": "Updated trek caption with sunset view"},
        headers=user_a["headers"]
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["caption"] == "Updated trek caption with sunset view"

    # 3. User B attempts to edit User A's reel -> 403 Forbidden
    b_edit_res = client.put(
        f"/api/v1/reels/{reel_id}",
        json={"caption": "Vandalized caption by user B"},
        headers=user_b["headers"]
    )
    assert b_edit_res.status_code == 403
    assert "author" in b_edit_res.json()["detail"].lower()

    # 4. User B attempts to delete User A's reel -> 403 Forbidden
    b_del_res = client.delete(
        f"/api/v1/reels/{reel_id}",
        headers=user_b["headers"]
    )
    assert b_del_res.status_code == 403
    assert "author" in b_del_res.json()["detail"].lower()

    # 5. User A successfully deletes their own reel -> 200 OK
    a_del_res = client.delete(
        f"/api/v1/reels/{reel_id}",
        headers=user_a["headers"]
    )
    assert a_del_res.status_code == 200
    assert a_del_res.json()["status"] == "ok"
