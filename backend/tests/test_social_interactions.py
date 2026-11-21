import pytest
from app.models.user import User
from app.models.connection import UserConnection
from app.models.post import Post
from app.models.notification import Notification
from app.models.message import Message
from app.services.quota_service import DAILY_UPLOAD_LIMIT

@pytest.fixture
def test_users(db):
    from app.core.security import hash_password
    users = []
    for i in range(1, 4):
        u = db.query(User).filter(User.email == f"social_u{i}@align.local").first()
        if not u:
            u = User(
                name=f"Social User {i}",
                email=f"social_u{i}@align.local",
                password_hash=hash_password("Password123!"),
                is_active=True,
            )
            db.add(u)
    db.commit()
    for i in range(1, 4):
        users.append(db.query(User).filter(User.email == f"social_u{i}@align.local").first())

    # Establish accepted connection between User 1 and User 2
    conn = db.query(UserConnection).filter(
        UserConnection.sender_id == users[0].id,
        UserConnection.receiver_id == users[1].id,
    ).first()
    if not conn:
        conn = UserConnection(
            sender_id=users[0].id,
            receiver_id=users[1].id,
            status="accepted",
        )
        db.add(conn)
        db.commit()

    return users

def get_auth_headers_for(client, email):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_threaded_comments_and_replies(client, test_users):
    u1, u2, _ = test_users
    h1 = get_auth_headers_for(client, u1.email)
    h2 = get_auth_headers_for(client, u2.email)

    # 1. Create a post
    post_res = client.post("/api/v1/feed", json={"content": "Exploring Shivneri Fort #history", "visibility": "public"}, headers=h1)
    assert post_res.status_code == 201
    post_id = post_res.json()["id"]

    # 2. Add top-level comment by u2
    c1_res = client.post(f"/api/v1/feed/{post_id}/comments", json={"content": "Incredible architecture! Which gate did you enter through?"}, headers=h2)
    assert c1_res.status_code == 201
    c1 = c1_res.json()
    assert c1["parent_id"] is None

    # 3. Add reply by u1
    c2_res = client.post(f"/api/v1/feed/{post_id}/comments", json={"content": "Entered through Maha Darwaza!", "parent_id": c1["id"]}, headers=h1)
    assert c2_res.status_code == 201
    c2 = c2_res.json()
    assert c2["parent_id"] == c1["id"]

    # 4. Reply to reply (should flatten to top parent c1)
    c3_res = client.post(f"/api/v1/feed/{post_id}/comments", json={"content": "Awesome, thanks for the tip!", "parent_id": c2["id"]}, headers=h2)
    assert c3_res.status_code == 201
    c3 = c3_res.json()
    assert c3["parent_id"] == c1["id"]

    # 5. Query comments
    list_res = client.get(f"/api/v1/feed/{post_id}/comments")
    assert list_res.status_code == 200
    tree = list_res.json()
    assert len(tree) == 1
    top_comment = tree[0]
    assert top_comment["id"] == c1["id"]
    assert len(top_comment["replies"]) == 2
    reply_ids = [r["id"] for r in top_comment["replies"]]
    assert c2["id"] in reply_ids
    assert c3["id"] in reply_ids

def test_mention_notifications(client, test_users, db):
    u1, u2, _ = test_users
    h1 = get_auth_headers_for(client, u1.email)

    # Post with @mention of u2 ("Social User 2")
    mention_handle = "Social"
    post_res = client.post(
        "/api/v1/feed",
        json={"content": f"Hey @{mention_handle}, check out the new Sahyadri trekking schedule!", "visibility": "public"},
        headers=h1,
    )
    assert post_res.status_code == 201

    # Verify notification created for u2
    notif = db.query(Notification).filter(
        Notification.user_id == u2.id,
        Notification.title.contains("mentioned you"),
    ).first()
    assert notif is not None
    assert "mentioned you in a post" in notif.message

def test_post_pinning(client, test_users):
    u1, u2, _ = test_users
    h1 = get_auth_headers_for(client, u1.email)
    h2 = get_auth_headers_for(client, u2.email)

    # Create 4 posts
    posts = []
    for i in range(4):
        res = client.post("/api/v1/feed", json={"content": f"Pinned candidate update #{i}", "visibility": "public"}, headers=h1)
        posts.append(res.json()["id"])

    # Non-author cannot pin
    unauth_pin = client.post(f"/api/v1/feed/{posts[0]}/pin", headers=h2)
    assert unauth_pin.status_code == 403

    # Pin post 0, 1, 2
    for p_id in posts[:3]:
        pin_res = client.post(f"/api/v1/feed/{p_id}/pin", headers=h1)
        assert pin_res.status_code == 200
        assert pin_res.json()["is_pinned"] is True

    # 4th pin fails with 400 (max 3 allowed)
    fourth_pin = client.post(f"/api/v1/feed/{posts[3]}/pin", headers=h1)
    assert fourth_pin.status_code == 400
    assert "only pin up to 3 posts" in fourth_pin.json()["detail"]

    # Unpin post 0
    unpin_res = client.post(f"/api/v1/feed/{posts[0]}/pin", headers=h1)
    assert unpin_res.status_code == 200
    assert unpin_res.json()["is_pinned"] is False

    # Now post 3 can be pinned
    retry_fourth = client.post(f"/api/v1/feed/{posts[3]}/pin", headers=h1)
    assert retry_fourth.status_code == 200
    assert retry_fourth.json()["is_pinned"] is True

def test_share_post_to_dm(client, test_users, db):
    u1, u2, u3 = test_users
    h1 = get_auth_headers_for(client, u1.email)

    # 1. Share public post to u2
    pub_post = client.post("/api/v1/feed", json={"content": "Public community gathering in Pune", "visibility": "public"}, headers=h1).json()
    share_res = client.post(
        f"/api/v1/feed/{pub_post['id']}/share",
        json={"recipient_id": u2.id, "note": "Are you joining?"},
        headers=h1,
    )
    assert share_res.status_code == 200
    msg_id = share_res.json()["message_id"]

    msg = db.get(Message, msg_id)
    assert msg is not None
    assert msg.sender_id == u1.id
    assert msg.receiver_id == u2.id
    assert "Shared post" in msg.content
    assert "Are you joining?" in msg.content

    # 2. Cannot share connections_only post with non-connected user (u3)
    priv_post = client.post("/api/v1/feed", json={"content": "Private family trek", "visibility": "connections_only"}, headers=h1).json()
    invalid_share = client.post(
        f"/api/v1/feed/{priv_post['id']}/share",
        json={"recipient_id": u3.id},
        headers=h1,
    )
    assert invalid_share.status_code == 403
    assert "connections-only" in invalid_share.json()["detail"]

    # 3. Cannot share with self
    self_share = client.post(
        f"/api/v1/feed/{pub_post['id']}/share",
        json={"recipient_id": u1.id},
        headers=h1,
    )
    assert self_share.status_code == 400

def test_daily_upload_quota(client, test_users, db):
    _, _, u3 = test_users
    h3 = get_auth_headers_for(client, u3.email)

    # Simulate user having 20 posts created today
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for i in range(DAILY_UPLOAD_LIMIT):
        p = Post(
            author_id=u3.id,
            content=f"Simulated quota post #{i}",
            visibility="public",
            created_at=now,
        )
        db.add(p)
    db.commit()

    # 21st post must trigger 429
    excess_res = client.post(
        "/api/v1/feed",
        json={"content": "One post too many today!", "visibility": "public"},
        headers=h3,
    )
    assert excess_res.status_code == 429
    assert "Daily upload quota exceeded" in excess_res.json()["detail"]
