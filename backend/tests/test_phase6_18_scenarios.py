"""
ALIGN Phase 6: 18 End-to-End Mission-Critical Scenarios Test Suite
Covers the entire user lifecycle, data source of truth, security boundaries,
authentic recommendations, and persistence guarantees.
"""
import time
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.user import User, Profile
from app.models.connection import UserConnection
from app.models.community import Community, CommunityMembership
from app.models.event import Event, EventRegistration
from app.models.place import Place
from app.models.project import Project, ProjectMember, ProjectMilestone, ProjectApplication, ProjectDiscussion
from app.models.message import Message
from app.models.notification import Notification
from app.models.gamification import UserGamification, UserBadge, UserActivityLog
from app.models.assistant import AssistantConversation, AssistantMessage
from app.models.goal_journey import GoalJourney, GoalMilestone
from app.models.recommendation_feedback import RecommendationFeedback
from app.services.gamification_service import award_xp

def test_18_end_to_end_scenarios(client: TestClient, db: Session):
    uid = uuid.uuid4().hex[:8]
    ts = int(time.time() * 1000)
    email_a = f"alice_{uid}@align.local"
    email_b = f"bob_{uid}@align.local"
    email_c = f"eve_{uid}@align.local"
    pw = "SuperSecurePass123!"

    # =========================================================================
    # SCENARIO 1: USER REGISTRATION
    # =========================================================================
    reg_a = client.post("/api/v1/auth/register", json={"name": "Alice Innovator", "email": email_a, "password": pw})
    assert reg_a.status_code == 201, reg_a.text
    user_a_id = reg_a.json()["id"]

    reg_b = client.post("/api/v1/auth/register", json={"name": "Bob Builder", "email": email_b, "password": pw})
    assert reg_b.status_code == 201, reg_b.text
    user_b_id = reg_b.json()["id"]

    reg_c = client.post("/api/v1/auth/register", json={"name": "Eve Unauthorized", "email": email_c, "password": pw})
    assert reg_c.status_code == 201, reg_c.text
    user_c_id = reg_c.json()["id"]

    # =========================================================================
    # SCENARIO 2: AUTHENTICATION & LOGIN/TOKEN EXCHANGE
    # =========================================================================
    # Bad credentials rejected
    bad_login = client.post("/api/v1/auth/login", json={"email": email_a, "password": "WrongPassword!"})
    assert bad_login.status_code == 401

    # Valid logins
    login_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": pw})
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    login_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": pw})
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    login_c = client.post("/api/v1/auth/login", json={"email": email_c, "password": pw})
    assert login_c.status_code == 200
    token_c = login_c.json()["access_token"]
    headers_c = {"Authorization": f"Bearer {token_c}"}

    # Protected route access
    me_a = client.get("/api/v1/users/me", headers=headers_a)
    assert me_a.status_code == 200
    assert me_a.json()["email"] == email_a

    # =========================================================================
    # SCENARIO 3: PROFILE EDITING & ATTRIBUTE RETRIEVAL
    # =========================================================================
    prof_a = client.put(
        "/api/v1/users/me/profile",
        headers=headers_a,
        json={
            "bio": "AI Systems Architect and Neural Networks researcher",
            "location": "San Francisco, CA",
            "skills": "Python, PyTorch, FastAPI, PostgreSQL",
            "interests": "Deep Learning, Generative AI, Robotics",
            "goals": "Build Open Source Intelligence Ecosystems",
            "preferred_activities": "Hackathons, Tech Meetups",
            "preferred_community_types": "Technical, Open-Source",
        },
    )
    assert prof_a.status_code == 200
    assert prof_a.json()["skills"] == "Python, PyTorch, FastAPI, PostgreSQL"

    prof_b = client.put(
        "/api/v1/users/me/profile",
        headers=headers_b,
        json={
            "bio": "Full-Stack Engineer building collaborative tools",
            "location": "San Francisco, CA",
            "skills": "Python, React, TypeScript, Docker",
            "interests": "Web Development, Open-Source, Cloud Architecture",
            "goals": "Collaborate on Production ML Platforms",
            "preferred_activities": "Pair Programming, Workshops",
            "preferred_community_types": "Engineering, Startups",
        },
    )
    assert prof_b.status_code == 200

    # =========================================================================
    # SCENARIO 4: DISCOVER USERS (SEMANTIC & KEYWORD MATCHING)
    # =========================================================================
    disc_users = client.get("/api/v1/users?q=Python", headers=headers_a)
    assert disc_users.status_code == 200
    user_results = disc_users.json()
    assert any(u["id"] == user_b_id for u in user_results)

    # =========================================================================
    # SCENARIO 5: PEER CONNECTION WORKFLOW
    # =========================================================================
    conn_req = client.post(f"/api/v1/users/{user_b_id}/connect", headers=headers_a)
    assert conn_req.status_code == 200
    conn_id = conn_req.json()["connection_id"]

    # Bob accepts connection
    conn_acc = client.post(f"/api/v1/users/connections/{conn_id}/accept", headers=headers_b)
    assert conn_acc.status_code == 200

    # Mutual live counts assert 1 connection
    me_a_conn = client.get("/api/v1/users/me", headers=headers_a).json()
    me_b_conn = client.get("/api/v1/users/me", headers=headers_b).json()
    assert me_a_conn["connections_count"] == 1
    assert me_b_conn["connections_count"] == 1

    # =========================================================================
    # SCENARIO 6: CREATE COMMUNITY
    # =========================================================================
    comm_resp = client.post(
        "/api/v1/communities",
        headers=headers_a,
        json={
            "name": f"Autonomous Agents Collective {uid}",
            "description": "Exploration circle for distributed agent orchestration and memory systems.",
            "category": "AI & Machine Learning",
            "purpose": "Collaborative Research",
        },
    )
    assert comm_resp.status_code == 201, comm_resp.text
    comm_id = comm_resp.json()["id"]

    # =========================================================================
    # SCENARIO 7: JOIN COMMUNITY
    # =========================================================================
    join_resp = client.post(f"/api/v1/communities/{comm_id}/join", headers=headers_b)
    assert join_resp.status_code == 200

    # =========================================================================
    # SCENARIO 8: REAL DB-CALCULATED MEMBERSHIP COUNT
    # =========================================================================
    comm_details = client.get(f"/api/v1/communities/{comm_id}", headers=headers_a).json()
    # Creator (Admin) + Joiner (Member) = 2 active members
    assert comm_details["member_count"] == 2

    # Bob leaves community -> count must decrement to 1
    leave_resp = client.post(f"/api/v1/communities/{comm_id}/leave", headers=headers_b)
    assert leave_resp.status_code == 200
    comm_after_leave = client.get(f"/api/v1/communities/{comm_id}", headers=headers_a).json()
    assert comm_after_leave["member_count"] == 1

    # Re-join for ongoing collaboration
    client.post(f"/api/v1/communities/{comm_id}/join", headers=headers_b)

    # =========================================================================
    # SCENARIO 9: REAL EVENTS (CATEGORY, DATE, REGISTRATION, CAPACITY)
    # =========================================================================
    now = datetime.now(timezone.utc)
    ev_resp = client.post(
        "/api/v1/events",
        headers=headers_a,
        json={
            "title": f"Bay Area AI Summit {uid}",
            "description": "Annual gathering of machine learning practitioners and researchers.",
            "category": "Technology",
            "location": "San Francisco, CA",
            "starts_at": (now + timedelta(days=7)).isoformat(),
            "ends_at": (now + timedelta(days=7, hours=4)).isoformat(),
            "max_attendees": 100,
        },
    )
    assert ev_resp.status_code == 201
    event_id = ev_resp.json()["id"]

    # Bob registers for event
    reg_ev = client.post(f"/api/v1/events/{event_id}/register", headers=headers_b, json={"ticket_count": 1})
    assert reg_ev.status_code == 200
    assert "ticket_code" in reg_ev.json()
    ev_detail = client.get(f"/api/v1/events/{event_id}", headers=headers_a).json()
    assert ev_detail["registered_count"] == 1

    # =========================================================================
    # SCENARIO 10: VALIDATED PLACES & VERIFIED COORDINATES
    # =========================================================================
    places_resp = client.get("/api/v1/places?limit=10")
    assert places_resp.status_code == 200
    places_list = places_resp.json()
    assert len(places_list) > 0
    # Every place must have valid coordinates
    for pl in places_list:
        assert -90.0 <= pl["latitude"] <= 90.0
        assert -180.0 <= pl["longitude"] <= 180.0
        assert pl["image_url"] is not None

    # Save place
    first_place_id = places_list[0]["id"]
    save_pl = client.post("/api/v1/saved", headers=headers_a, json={"item_type": "place", "item_id": first_place_id})
    assert save_pl.status_code == 201
    saved_items = client.get("/api/v1/saved", headers=headers_a).json()
    assert any(s["item_id"] == first_place_id for s in saved_items)

    # =========================================================================
    # SCENARIO 11: DB-BACKED RECOMMENDATIONS & FEEDBACK LOOP
    # =========================================================================
    recs_resp = client.get(
        "/api/v1/discovery/recommendations?limit=10",
        headers=headers_a,
    )
    assert recs_resp.status_code == 200
    recs = recs_resp.json()
    assert len(recs) > 0
    first_rec = recs[0]
    assert "id" in first_rec
    assert "why_recommended" in first_rec
    assert "source" in first_rec

    # Submit feedback
    fb_resp = client.post(
        "/api/v1/discovery/feedback",
        headers=headers_a,
        json={
            "item_type": first_rec["result_type"],
            "item_id": first_rec["id"],
            "feedback": "relevant",
            "notes": "Highly aligned with my AI architecture goals",
        },
    )
    assert fb_resp.status_code == 201

    # =========================================================================
    # SCENARIO 12: GROUNDED AI ASSISTANT CONVERSATIONS
    # =========================================================================
    conv_resp = client.post(
        "/api/v1/assistant/conversations",
        headers=headers_a,
        json={"title": "Agent Mesh Architecture Plan"},
    )
    assert conv_resp.status_code in (200, 201)
    conv_id = conv_resp.json()["id"]

    msg_resp = client.post(
        "/api/v1/assistant/chat",
        headers=headers_a,
        json={"conversation_id": conv_id, "message": "Find collaborators interested in machine learning and Python."},
    )
    assert msg_resp.status_code == 200
    assert "content" in msg_resp.json()

    # =========================================================================
    # SCENARIO 13: REOPEN CHATS & MESSAGE HISTORY PERSISTENCE
    # =========================================================================
    reopened = client.get(f"/api/v1/assistant/conversations/{conv_id}/messages", headers=headers_a)
    assert reopened.status_code == 200
    history = reopened.json()
    assert len(history) >= 2  # User message + Assistant reply

    # =========================================================================
    # SCENARIO 14: GOAL JOURNEYS & MILESTONES PERSISTENCE
    # =========================================================================
    journey_resp = client.post(
        "/api/v1/goals/generate",
        headers=headers_a,
        json={
            "title": "Master Production LLM Infrastructure",
            "category": "Career & Learning",
            "timeframe": "3-6 months",
        },
    )
    assert journey_resp.status_code == 201
    journey_data = journey_resp.json()
    journey_id = journey_data["id"]
    assert len(journey_data["milestones"]) > 0
    m1_id = journey_data["milestones"][0]["id"]

    # Complete Milestone 1
    m_complete = client.patch(
        f"/api/v1/goals/{journey_id}/milestones/{m1_id}",
        headers=headers_a,
    )
    assert m_complete.status_code == 200
    assert m_complete.json()["is_completed"] is True

    # Re-fetch journey
    journey_refetch = client.get(f"/api/v1/goals/{journey_id}", headers=headers_a).json()
    assert journey_refetch["completed_milestones"] >= 1
    assert journey_refetch["progress_percentage"] > 0

    # =========================================================================
    # SCENARIO 15: PERSISTENT 1:1 MESSAGING & READ STATES
    # =========================================================================
    # Alice sends message to Bob
    send_m = client.post(
        "/api/v1/messages",
        headers=headers_a,
        json={"receiver_id": user_b_id, "content": "Hey Bob! Ready to build the autonomous agent mesh?"},
    )
    assert send_m.status_code == 201
    assert send_m.json()["is_read"] is False

    # Bob's unread count is 1
    unread_bob = client.get("/api/v1/messages/unread/count", headers=headers_b).json()
    assert unread_bob["unread_count"] >= 1

    # Bob reads conversation -> marks as read
    bob_msgs = client.get(f"/api/v1/messages?other_user_id={user_a_id}", headers=headers_b).json()
    assert len(bob_msgs) >= 1
    assert bob_msgs[0]["is_read"] is True

    # =========================================================================
    # SCENARIO 16: MULTI-EVENT NOTIFICATIONS & READ MANAGEMENT
    # =========================================================================
    notifs_bob = client.get("/api/v1/notifications", headers=headers_b).json()
    assert len(notifs_bob) >= 1

    # Bob marks all notifications as read
    read_all = client.post("/api/v1/notifications/read-all", headers=headers_b)
    assert read_all.status_code == 200
    unread_n_bob = client.get("/api/v1/notifications/unread/count", headers=headers_b).json()
    assert unread_n_bob["unread_count"] == 0

    # =========================================================================
    # SCENARIO 17: VERIFIED-ONLY XP & ANTI-DUPLICATE REWARD PROTECTION
    # =========================================================================
    dedup_tag = f"verified_action_{ts}_{uid}"
    r_xp1 = award_xp(db, user_a_id, "project_hack", 60, "Participated in verified hackathon", dedup_key=dedup_tag)
    assert r_xp1["status"] == "ok"
    assert r_xp1["xp_awarded"] == 60
    total_xp_after = r_xp1["total_xp"]

    # Exact duplicate attempt MUST NOT award XP
    r_xp2 = award_xp(db, user_a_id, "project_hack", 60, "Participated in verified hackathon", dedup_key=dedup_tag)
    assert r_xp2["status"] == "duplicate"
    assert r_xp2["xp_awarded"] == 0
    assert r_xp2["total_xp"] == total_xp_after

    # Audit history endpoint returns logged transactions
    xp_hist = client.get("/api/v1/gamification/history", headers=headers_a).json()
    assert xp_hist["total_transactions"] >= 1
    assert any(item["dedup_key"] == dedup_tag for item in xp_hist["items"])

    # =========================================================================
    # SCENARIO 18: UNAUTHORIZED ACCESS BLOCKED & CROSS-USER ISOLATION
    # =========================================================================
    # Eve cannot access Alice's private assistant conversation
    eve_conv = client.get(f"/api/v1/assistant/conversations/{conv_id}", headers=headers_c)
    assert eve_conv.status_code in (403, 404)

    # Eve cannot view messages exchanged between Alice and Bob
    eve_msgs = client.get(f"/api/v1/messages?other_user_id={user_a_id}", headers=headers_c).json()
    # Scoped strictly to messages between Eve and Alice (which is empty)
    assert len(eve_msgs) == 0

    # Eve cannot delete Alice's community
    eve_del_comm = client.delete(f"/api/v1/communities/{comm_id}", headers=headers_c)
    assert eve_del_comm.status_code == 403

    # Unauthenticated request blocked
    unauth_resp = client.get("/api/v1/users/me")
    assert unauth_resp.status_code == 401
