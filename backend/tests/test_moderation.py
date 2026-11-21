import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.post import Post
from app.models.reel import Reel
from app.models.user import User, UserReport
from app.models.notification import Notification

def create_test_user(client: TestClient, email: str, name: str, is_admin: bool = False, db: Session = None) -> tuple[int, dict]:
    payload = {"email": email, "password": "Password123!", "name": name}
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db.scalar(select(User).where(User.email == email))
    if is_admin:
        user.is_admin = True
        user.role = "admin"
        db.commit()

    return user.id, headers

def test_report_submission_post_and_self_report_block(client: TestClient, db: Session):
    """Test reporting a post and verifying self-reporting is rejected."""
    uid_a, headers_a = create_test_user(client, "mod_author@test.com", "Mod Author", db=db)
    uid_b, headers_b = create_test_user(client, "mod_reporter@test.com", "Mod Reporter", db=db)

    # User A creates a post
    post_res = client.post(
        "/api/v1/feed",
        headers=headers_a,
        json={"content": "Post with suspicious content", "visibility": "public"}
    )
    assert post_res.status_code == 201
    post_id = post_res.json()["id"]

    # User A tries to report own post -> rejected
    self_rep = client.post(
        "/api/v1/reports",
        headers=headers_a,
        json={"target_type": "post", "target_id": post_id, "reason": "Spam"}
    )
    assert self_rep.status_code == 400
    assert "own post" in self_rep.json()["detail"].lower()

    # User B reports User A's post
    rep_res = client.post(
        "/api/v1/reports",
        headers=headers_b,
        json={
            "target_type": "post",
            "target_id": post_id,
            "reason": "Harassment",
            "details": "Violates community standards"
        }
    )
    assert rep_res.status_code == 201
    data = rep_res.json()
    assert data["status"] == "ok"
    report_id = data["report_id"]

    # Verify report in database
    report = db.get(UserReport, report_id)
    assert report is not None
    assert report.target_type == "post"
    assert report.post_id == post_id
    assert report.reported_user_id == uid_a
    assert report.reporter_id == uid_b
    assert report.status == "pending"

def test_report_submission_reel_and_user(client: TestClient, db: Session):
    """Test reporting a reel and reporting a user directly."""
    uid_a, headers_a = create_test_user(client, "reel_author@test.com", "Reel Author", db=db)
    uid_b, headers_b = create_test_user(client, "reel_reporter@test.com", "Reel Reporter", db=db)

    # User A creates a reel
    reel_res = client.post(
        "/api/v1/reels",
        headers=headers_a,
        json={
            "title": "Questionable Tech Reel",
            "category": "Technology",
            "video_url": "/uploads/test.mp4",
            "thumbnail_url": "/uploads/test.webp",
            "visibility": "public",
        }
    )
    assert reel_res.status_code == 201
    reel_id = reel_res.json()["id"]

    # User B reports User A's reel
    rep_reel = client.post(
        "/api/v1/reports",
        headers=headers_b,
        json={"target_type": "reel", "target_id": reel_id, "reason": "Inappropriate / NSFW"}
    )
    assert rep_reel.status_code == 201
    assert rep_reel.json()["target_id"] == reel_id

    # User B reports User A directly
    rep_user = client.post(
        "/api/v1/reports",
        headers=headers_b,
        json={"target_type": "user", "target_id": uid_a, "reason": "Spam Account"}
    )
    assert rep_user.status_code == 201

    # User B cannot report self
    self_rep = client.post(
        "/api/v1/reports",
        headers=headers_b,
        json={"target_type": "user", "target_id": uid_b, "reason": "Self"}
    )
    assert self_rep.status_code == 400

def test_admin_remove_content_and_feed_masking(client: TestClient, db: Session):
    """Test admin 'remove_content' action, content masking in feed, and author notification."""
    uid_a, headers_a = create_test_user(client, "mask_author@test.com", "Mask Author", db=db)
    uid_b, headers_b = create_test_user(client, "mask_viewer@test.com", "Mask Viewer", db=db)
    _, headers_admin = create_test_user(client, "admin_user_1@test.com", "Admin User 1", is_admin=True, db=db)

    # User A posts
    post_res = client.post(
        "/api/v1/feed",
        headers=headers_a,
        json={"content": "Content destined for removal", "visibility": "public"}
    )
    post_id = post_res.json()["id"]

    # User B verifies post is in feed
    feed_before = client.get("/api/v1/feed", headers=headers_b).json()
    assert any(p["id"] == post_id for p in feed_before)

    # User B reports post
    rep_res = client.post(
        "/api/v1/reports",
        headers=headers_b,
        json={"target_type": "post", "target_id": post_id, "reason": "Hate Speech"}
    )
    report_id = rep_res.json()["report_id"]

    # Admin takes action: remove_content
    act_res = client.post(
        f"/api/v1/admin/reports/{report_id}/action",
        headers=headers_admin,
        json={"action": "remove_content"}
    )
    assert act_res.status_code == 200
    assert "removed" in act_res.json()["message"].lower() or "hidden" in act_res.json()["message"].lower()

    # Verify post is hidden in DB
    post = db.get(Post, post_id)
    assert post.is_hidden is True

    # Verify notification dispatched to User A
    notifs = list(db.scalars(select(Notification).where(Notification.user_id == uid_a)))
    assert any("removed" in n.title.lower() for n in notifs)

    # Verify post is now masked/excluded from feed for User B and unauthenticated users
    feed_after = client.get("/api/v1/feed", headers=headers_b).json()
    assert not any(p["id"] == post_id for p in feed_after)

    pub_feed = client.get("/api/v1/feed").json()
    assert not any(p["id"] == post_id for p in pub_feed)

    # Verify direct get gives 404 for User B, but Admin can still access
    assert client.get(f"/api/v1/feed/{post_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/feed/{post_id}", headers=headers_admin).status_code == 200

def test_admin_warn_user(client: TestClient, db: Session):
    """Test admin 'warn_user' action and community warning notification."""
    uid_a, headers_a = create_test_user(client, "warn_author@test.com", "Warn Author", db=db)
    uid_b, headers_b = create_test_user(client, "warn_reporter@test.com", "Warn Reporter", db=db)
    _, headers_admin = create_test_user(client, "admin_user_2@test.com", "Admin User 2", is_admin=True, db=db)

    # User B reports User A
    rep_res = client.post(
        "/api/v1/reports",
        headers=headers_b,
        json={"target_type": "user", "target_id": uid_a, "reason": "Harassment"}
    )
    report_id = rep_res.json()["report_id"]

    # Admin takes action: warn_user
    act_res = client.post(
        f"/api/v1/admin/reports/{report_id}/action",
        headers=headers_admin,
        json={"action": "warn_user"}
    )
    assert act_res.status_code == 200
    assert "warning" in act_res.json()["message"].lower()

    # Verify warning notification dispatched to User A
    notifs = list(db.scalars(select(Notification).where(Notification.user_id == uid_a)))
    assert any("warning" in n.title.lower() for n in notifs)

    # Report status marked resolved
    report = db.get(UserReport, report_id)
    assert report.status == "resolved"

def test_admin_suspend_and_dismiss_actions(client: TestClient, db: Session):
    """Test admin 'suspend_user' and 'dismiss_report' actions."""
    uid_a, headers_a = create_test_user(client, "suspend_target@test.com", "Suspend Target", db=db)
    uid_b, headers_b = create_test_user(client, "suspend_reporter@test.com", "Suspend Reporter", db=db)
    _, headers_admin = create_test_user(client, "admin_user_3@test.com", "Admin User 3", is_admin=True, db=db)

    # Report 1: For suspension
    rep_1 = client.post(
        "/api/v1/reports",
        headers=headers_b,
        json={"target_type": "user", "target_id": uid_a, "reason": "Severe Violation"}
    ).json()["report_id"]

    suspend_res = client.post(
        f"/api/v1/admin/reports/{rep_1}/action",
        headers=headers_admin,
        json={"action": "suspend_user"}
    )
    assert suspend_res.status_code == 200
    user_a = db.get(User, uid_a)
    assert user_a.is_active is False

    # Report 2: For dismissal
    rep_2 = client.post(
        "/api/v1/reports",
        headers=headers_b,
        json={"target_type": "user", "target_id": uid_a, "reason": "Spam"}
    ).json()["report_id"]

    dismiss_res = client.post(
        f"/api/v1/admin/reports/{rep_2}/action",
        headers=headers_admin,
        json={"action": "dismiss_report"}
    )
    assert dismiss_res.status_code == 200
    rep_obj = db.get(UserReport, rep_2)
    assert rep_obj.status == "dismissed"
