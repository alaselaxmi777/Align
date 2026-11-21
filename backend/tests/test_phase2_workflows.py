import time
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.user import User, Profile
from app.models.connection import UserConnection
from app.models.community import Community, CommunityMembership
from app.models.post import Post, PostLike, PostComment
from app.models.event import Event, EventRegistration
from app.models.place import Place
from app.core.security import create_access_token, hash_password
from app.services.places_service import sync_real_places


def test_auth_and_user_profile_counts(client: TestClient, db: Session):
    timestamp = int(time.time() * 1000)
    email = f"phase2_u1_{timestamp}@align.local"
    password = "SecurePassword123!"

    # 1. Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"name": "Alice Innovator", "email": email, "password": password}
    )
    assert reg_resp.status_code == 201, reg_resp.text
    user_id = reg_resp.json()["id"]

    # 2. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Logout
    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "ok"

    # 4. Profile counts must be 0 (no fake hardcoded numbers)
    me_resp = client.get("/api/v1/users/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["followers_count"] == 0
    assert me_data["following_count"] == 0
    assert me_data["connections_count"] == 0

    # 5. Update profile
    prof_resp = client.put(
        "/api/v1/users/me/profile",
        headers=headers,
        json={
            "bio": "AI & Distributed Systems Researcher",
            "location": "Pune, India",
            "skills": "Python, FastAPI, PyTorch",
            "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400",
        }
    )
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()
    assert prof_data["bio"] == "AI & Distributed Systems Researcher"
    assert prof_data["location"] == "Pune, India"
    assert prof_data["avatar_url"] is not None


def test_user_connections_workflow(client: TestClient, db: Session):
    timestamp = int(time.time() * 1000)
    # User A
    user_a = User(name="User Alpha", email=f"alpha_{timestamp}@align.local", password_hash=hash_password("Pass123!"), is_active=True)
    # User B
    user_b = User(name="User Beta", email=f"beta_{timestamp}@align.local", password_hash=hash_password("Pass123!"), is_active=True)
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    token_a = create_access_token(str(user_a.id))
    headers_a = {"Authorization": f"Bearer {token_a}"}

    token_b = create_access_token(str(user_b.id))
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. User A sends connection request to User B
    req_resp = client.post(f"/api/v1/users/{user_b.id}/connect", headers=headers_a)
    assert req_resp.status_code in (200, 201), req_resp.text
    req_data = req_resp.json()
    assert req_data["connection_status"] == "pending"
    conn_id = req_data["connection_id"]

    # 2. User B responds to request and accepts
    resp_accept = client.post(
        f"/api/v1/users/connections/{conn_id}/accept",
        headers=headers_b
    )
    assert resp_accept.status_code == 200, resp_accept.text
    assert resp_accept.json()["status"] == "ok"

    # 3. Verify connections_count for User A and User B
    stats_a = client.get("/api/v1/users/me", headers=headers_a).json()
    stats_b = client.get("/api/v1/users/me", headers=headers_b).json()
    assert stats_a["connections_count"] == 1
    assert stats_b["connections_count"] == 1

    # 4. User A disconnects from User B
    disc_resp = client.post(f"/api/v1/users/{user_b.id}/disconnect", headers=headers_a)
    assert disc_resp.status_code == 200, disc_resp.text
    assert disc_resp.json()["status"] == "ok"

    # 5. Verify connections_count dropped back to 0
    stats_a_after = client.get("/api/v1/users/me", headers=headers_a).json()
    stats_b_after = client.get("/api/v1/users/me", headers=headers_b).json()
    assert stats_a_after["connections_count"] == 0
    assert stats_b_after["connections_count"] == 0


def test_communities_authorization_and_discussions(client: TestClient, db: Session):
    timestamp = int(time.time() * 1000)
    owner = User(name="Community Owner", email=f"owner_{timestamp}@align.local", password_hash=hash_password("Pass123!"), is_active=True)
    member = User(name="Community Member", email=f"member_{timestamp}@align.local", password_hash=hash_password("Pass123!"), is_active=True)
    db.add_all([owner, member])
    db.commit()
    db.refresh(owner)
    db.refresh(member)

    headers_owner = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    headers_member = {"Authorization": f"Bearer {create_access_token(str(member.id))}"}

    # 1. Owner creates community
    comm_resp = client.post(
        "/api/v1/communities",
        headers=headers_owner,
        json={
            "name": f"Open Source Robotics {timestamp}",
            "description": "Collaborative builders designing open hardware and robotic arms.",
            "category": "Robotics",
            "tags": "hardware, ros, python",
            "location": "Pune",
        }
    )
    assert comm_resp.status_code == 201, comm_resp.text
    comm_data = comm_resp.json()
    comm_id = comm_data["id"]
    assert comm_data["member_count"] == 1

    # 2. Member joins community
    join_resp = client.post(f"/api/v1/communities/{comm_id}/join", headers=headers_member)
    assert join_resp.status_code == 200, join_resp.text
    assert join_resp.json()["status"] == "ok"

    # Verify updated member count is 2
    get_comm = client.get(f"/api/v1/communities/{comm_id}", headers=headers_member).json()
    assert get_comm["member_count"] == 2
    assert get_comm["is_member"] is True

    # 3. Non-owner cannot delete the community (Authorization test)
    del_forbidden = client.delete(f"/api/v1/communities/{comm_id}", headers=headers_member)
    assert del_forbidden.status_code == 403

    # 4. Member posts discussion post
    post_resp = client.post(
        f"/api/v1/communities/{comm_id}/posts",
        headers=headers_member,
        json={"content": "Welcome everyone! Here is our initial ROS2 driver repository."}
    )
    assert post_resp.status_code == 201, post_resp.text
    post_id = post_resp.json()["id"]

    # 5. Owner likes the post
    like_resp = client.post(f"/api/v1/feed/{post_id}/like", headers=headers_owner)
    assert like_resp.status_code == 200, like_resp.text
    assert like_resp.json()["is_liked"] is True

    # 6. Owner comments on post
    cmt_resp = client.post(
        f"/api/v1/feed/{post_id}/comments",
        headers=headers_owner,
        json={"content": "Great repo! I have tested it on Ubuntu 22.04."}
    )
    assert cmt_resp.status_code == 201, cmt_resp.text

    # 7. Check post list returns real live counts (likes_count=1, comments_count=1, is_liked=True)
    posts_list = client.get(f"/api/v1/communities/{comm_id}/posts", headers=headers_owner).json()
    assert len(posts_list) >= 1
    found_post = next(p for p in posts_list if p["id"] == post_id)
    assert found_post["likes_count"] == 1
    assert found_post["comments_count"] == 1
    assert found_post["is_liked"] is True

    # 8. Member leaves community -> member count drops back to 1
    leave_resp = client.post(f"/api/v1/communities/{comm_id}/leave", headers=headers_member)
    assert leave_resp.status_code == 200, leave_resp.text
    assert leave_resp.json()["status"] == "ok"

    comm_after_leave = client.get(f"/api/v1/communities/{comm_id}", headers=headers_owner).json()
    assert comm_after_leave["member_count"] == 1


def test_events_capacity_filtering_and_rsvp(client: TestClient, db: Session):
    timestamp = int(time.time() * 1000)
    organizer = User(name="Organizer", email=f"organizer_{timestamp}@align.local", password_hash=hash_password("Pass123!"), is_active=True)
    attendee1 = User(name="Attendee 1", email=f"att1_{timestamp}@align.local", password_hash=hash_password("Pass123!"), is_active=True)
    attendee2 = User(name="Attendee 2", email=f"att2_{timestamp}@align.local", password_hash=hash_password("Pass123!"), is_active=True)
    attendee3 = User(name="Attendee 3", email=f"att3_{timestamp}@align.local", password_hash=hash_password("Pass123!"), is_active=True)
    db.add_all([organizer, attendee1, attendee2, attendee3])
    db.commit()

    headers_org = {"Authorization": f"Bearer {create_access_token(str(organizer.id))}"}
    headers_att1 = {"Authorization": f"Bearer {create_access_token(str(attendee1.id))}"}
    headers_att2 = {"Authorization": f"Bearer {create_access_token(str(attendee2.id))}"}
    headers_att3 = {"Authorization": f"Bearer {create_access_token(str(attendee3.id))}"}

    # 1. Create event with capacity = 2
    future_time = datetime.now(timezone.utc) + timedelta(days=7)
    evt_resp = client.post(
        "/api/v1/events",
        headers=headers_org,
        json={
            "title": f"Generative AI Hackathon {timestamp}",
            "description": "48 hour intensive hackathon building multi-modal LLM applications.",
            "category": "Hackathon",
            "location": "Baner, Pune",
            "latitude": 18.5590,
            "longitude": 73.7868,
            "starts_at": future_time.isoformat(),
            "capacity": 2
        }
    )
    assert evt_resp.status_code == 201, evt_resp.text
    evt_data = evt_resp.json()
    evt_id = evt_data["id"]
    assert evt_data["capacity"] == 2
    assert evt_data["registered_count"] == 0
    assert evt_data["is_external"] is False
    assert evt_data["is_expired"] is False

    # 2. Filter events by location
    list_resp = client.get("/api/v1/events?location=Pune", headers=headers_att1)
    assert list_resp.status_code == 200
    events_in_pune = list_resp.json()
    assert any(e["id"] == evt_id for e in events_in_pune)

    # 3. Attendee 1 registers
    reg1 = client.post(f"/api/v1/events/{evt_id}/register", headers=headers_att1)
    assert reg1.status_code == 200, reg1.text
    assert reg1.json()["status"] == "success"
    assert "ticket_code" in reg1.json()

    # 4. Attendee 2 registers
    reg2 = client.post(f"/api/v1/events/{evt_id}/register", headers=headers_att2)
    assert reg2.status_code == 200, reg2.text

    # 5. Attendee 3 attempts to register -> exceeds capacity -> 400 Bad Request
    reg3 = client.post(f"/api/v1/events/{evt_id}/register", headers=headers_att3)
    assert reg3.status_code == 400
    assert "capacity" in reg3.json()["detail"].lower()

    # 6. Attendee 1 cancels registration
    cancel_resp = client.post(f"/api/v1/events/{evt_id}/cancel", headers=headers_att1)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "ok"

    # Verify registered_count drops back to 1
    evt_after_cancel = client.get(f"/api/v1/events/{evt_id}", headers=headers_org).json()
    assert evt_after_cancel["registered_count"] == 1

    # 7. Test expired and external Eventbrite event flags
    past_time = datetime.now(timezone.utc) - timedelta(days=2)
    ext_event = Event(
        title=f"Past Eventbrite Meetup {timestamp}",
        description="Completed developer meetup from Eventbrite.",
        category="Tech",
        location="Mumbai",
        source="Eventbrite",
        starts_at=past_time,
        created_by_id=organizer.id
    )
    db.add(ext_event)
    db.commit()
    db.refresh(ext_event)

    ext_resp = client.get(f"/api/v1/events/{ext_event.id}", headers=headers_org).json()
    assert ext_resp["is_external"] is True
    assert ext_resp["is_expired"] is True


def test_places_authentic_images_and_deduplication(client: TestClient, db: Session):
    # 1. Sync real places
    res = sync_real_places(db)
    assert res["status"] == "success"

    # 2. Query places list
    places_resp = client.get("/api/v1/places?limit=10")
    assert places_resp.status_code == 200
    places = places_resp.json()
    assert len(places) > 0

    for p in places:
        assert p["name"]
        assert p["city"]
        assert p["latitude"] is not None
        assert p["longitude"] is not None
        assert p["image_url"] is not None
        assert p["image_url"].startswith("http")

    # 3. Test duplicate prevention: re-syncing must not create duplicate records
    count_before = db.scalar(select(func.count(Place.id)))
    sync_second = sync_real_places(db)
    assert sync_second["status"] == "success"
    assert sync_second["synced"] == 0  # 0 new duplicates added!
    count_after = db.scalar(select(func.count(Place.id)))
    assert count_before == count_after

    # 4. Map markers endpoint returns place and event markers
    markers_resp = client.get("/api/v1/places/map/markers")
    assert markers_resp.status_code == 200
    markers = markers_resp.json()
    assert len(markers) > 0
    place_markers = [m for m in markers if m["type"] == "place"]
    assert len(place_markers) > 0
    assert "image_url" in place_markers[0]
