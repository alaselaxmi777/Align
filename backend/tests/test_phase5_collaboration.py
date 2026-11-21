import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMilestone, ProjectApplication, ProjectDiscussion
from app.models.message import Message
from app.models.notification import Notification
from app.models.gamification import UserGamification, UserBadge, UserActivityLog
from app.services.gamification_service import award_xp, get_or_create_gamification

def test_project_lifecycle_applications_milestones_and_discussions(client: TestClient, db: Session):
    ts = int(time.time() * 1000)
    lead_email = f"lead_{ts}@align.local"
    dev_email = f"dev_{ts}@align.local"
    pw = "SecurePassword123!"

    # 1. Register Lead and Developer
    r1 = client.post("/api/v1/auth/register", json={"name": "Project Lead", "email": lead_email, "password": pw})
    assert r1.status_code == 201
    lead_id = r1.json()["id"]

    r2 = client.post("/api/v1/auth/register", json={"name": "Fullstack Dev", "email": dev_email, "password": pw})
    assert r2.status_code == 201
    dev_id = r2.json()["id"]

    # Login tokens
    t1 = client.post("/api/v1/auth/login", json={"email": lead_email, "password": pw}).json()["access_token"]
    t2 = client.post("/api/v1/auth/login", json={"email": dev_email, "password": pw}).json()["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}

    # 2. Publish Project
    proj_resp = client.post(
        "/api/v1/projects",
        headers=h1,
        json={
            "title": f"Autonomous Agent Mesh {ts}",
            "tagline": "Decentralized LLM coordination platform",
            "description": "Building multi-agent task execution mesh using FastAPI, LangChain and Vector DBs.",
            "category": "AI & Machine Learning",
            "stage": "idea",
            "required_roles": "Core Protocol Engineer, Frontend Architect",
            "skills_needed": "Python, FastAPI, PyTorch, React",
            "github_repo_url": "https://github.com/align/agent-mesh",
        },
    )
    assert proj_resp.status_code == 201, proj_resp.text
    proj_data = proj_resp.json()
    proj_id = proj_data["id"]
    assert proj_data["is_owner"] is True
    assert proj_data["team_size"] == 1
    assert proj_data["status"] == "recruiting"

    # 3. Update Project Status & Stage
    update_resp = client.patch(
        f"/api/v1/projects/{proj_id}",
        headers=h1,
        json={
            "stage": "prototyping",
            "status": "in_progress",
            "tagline": "Next-gen Autonomous Multi-Agent Mesh",
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["stage"] == "prototyping"
    assert update_resp.json()["status"] == "in_progress"

    # 4. Add Project Milestone
    ms_resp = client.post(
        f"/api/v1/projects/{proj_id}/milestones",
        headers=h1,
        json={
            "title": "Protocol Specifications & Schema",
            "description": "Finalize JSON-RPC interfaces and message contracts.",
            "step_order": 1,
        },
    )
    assert ms_resp.status_code == 201
    ms_id = ms_resp.json()["id"]
    assert ms_resp.json()["is_completed"] is False

    # 5. Developer Applies to Project
    apply_resp = client.post(
        f"/api/v1/projects/{proj_id}/apply",
        headers=h2,
        json={
            "desired_role": "Core Protocol Engineer",
            "pitch_message": "Experienced in asyncio systems and distributed consensus algorithms.",
        },
    )
    assert apply_resp.status_code == 201
    assert "submitted" in apply_resp.json()["message"].lower()

    # Verify notification sent to lead
    notif_lead = client.get("/api/v1/notifications", headers=h1).json()
    assert any("Contributor Application" in n["title"] for n in notif_lead)

    # 6. Lead reviews applications and accepts Developer
    apps = client.get(f"/api/v1/projects/{proj_id}/applications", headers=h1).json()
    assert len(apps) == 1
    app_id = apps[0]["id"]
    assert apps[0]["applicant_id"] == dev_id

    accept_resp = client.post(
        f"/api/v1/projects/{proj_id}/applications/{app_id}/accept",
        headers=h1,
    )
    assert accept_resp.status_code == 200

    # Verify developer is now project member
    dev_proj = client.get(f"/api/v1/projects/{proj_id}", headers=h2).json()
    assert dev_proj["is_member"] is True
    assert dev_proj["team_size"] == 2

    # Verify developer received acceptance notification
    dev_notifs = client.get("/api/v1/notifications", headers=h2).json()
    assert any("Accepted" in n["title"] for n in dev_notifs)

    # 7. Milestone Completion
    complete_resp = client.patch(
        f"/api/v1/projects/{proj_id}/milestones/{ms_id}",
        headers=h2,
        json={"is_completed": True},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["is_completed"] is True
    assert complete_resp.json()["completed_at"] is not None

    # 8. Project Discussions & Updates
    disc_resp = client.post(
        f"/api/v1/projects/{proj_id}/discussions",
        headers=h2,
        json={
            "title": "Architecture RFC: Event Loop Model",
            "content": "Proposing uvloop with ZeroMQ sockets for inter-node communication.",
        },
    )
    assert disc_resp.status_code == 201
    assert disc_resp.json()["author_name"] == "Fullstack Dev"

    discs = client.get(f"/api/v1/projects/{proj_id}/discussions", headers=h1).json()
    assert len(discs) == 1
    assert discs[0]["title"] == "Architecture RFC: Event Loop Model"

    # 9. Membership removal / leaving
    del_mem_resp = client.delete(f"/api/v1/projects/{proj_id}/members/{dev_id}", headers=h2)
    assert del_mem_resp.status_code == 200
    after_leave = client.get(f"/api/v1/projects/{proj_id}", headers=h1).json()
    assert after_leave["team_size"] == 1


def test_messaging_persistence_read_states_and_privacy(client: TestClient, db: Session):
    ts = int(time.time() * 1000)
    u1_email = f"chat1_{ts}@align.local"
    u2_email = f"chat2_{ts}@align.local"
    u3_email = f"chat3_{ts}@align.local"
    pw = "SecurePassword123!"

    # Register 3 users
    u1_id = client.post("/api/v1/auth/register", json={"name": "User One", "email": u1_email, "password": pw}).json()["id"]
    u2_id = client.post("/api/v1/auth/register", json={"name": "User Two", "email": u2_email, "password": pw}).json()["id"]
    u3_id = client.post("/api/v1/auth/register", json={"name": "User Three", "email": u3_email, "password": pw}).json()["id"]

    t1 = client.post("/api/v1/auth/login", json={"email": u1_email, "password": pw}).json()["access_token"]
    t2 = client.post("/api/v1/auth/login", json={"email": u2_email, "password": pw}).json()["access_token"]
    t3 = client.post("/api/v1/auth/login", json={"email": u3_email, "password": pw}).json()["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}
    h3 = {"Authorization": f"Bearer {t3}"}

    # 1. Send Message U1 -> U2
    send_resp = client.post(
        "/api/v1/messages",
        headers=h1,
        json={"receiver_id": u2_id, "content": "Hey! Are you open to collaborating on the AI challenge?"},
    )
    assert send_resp.status_code == 201
    msg_id = send_resp.json()["id"]
    assert send_resp.json()["is_read"] is False

    # 2. Check unread count for U2
    unread_resp = client.get("/api/v1/messages/unread/count", headers=h2)
    assert unread_resp.status_code == 200
    assert unread_resp.json()["unread_count"] == 1

    # 3. U2 gets conversations list
    convs = client.get("/api/v1/messages/conversations", headers=h2).json()
    assert len(convs) == 1
    assert convs[0]["partner_id"] == u1_id
    assert convs[0]["unread_count"] == 1
    assert "collaborating" in convs[0]["last_message"]

    # 4. Privacy: U3 tries to see messages between U1 and U2
    # Even if passing other_user_id=u1_id, U3 must only see messages where U3 is participant
    u3_view = client.get(f"/api/v1/messages?other_user_id={u1_id}", headers=h3).json()
    assert len(u3_view) == 0

    # 5. U2 fetches conversation with U1 -> automatically marks as read
    u2_msgs = client.get(f"/api/v1/messages?other_user_id={u1_id}", headers=h2).json()
    assert len(u2_msgs) == 1
    assert u2_msgs[0]["is_read"] is True

    # 6. Unread count is now 0
    unread_after = client.get("/api/v1/messages/unread/count", headers=h2).json()
    assert unread_after["unread_count"] == 0


def test_gamification_xp_verified_actions_and_anti_duplicate(client: TestClient, db: Session):
    ts = int(time.time() * 1000)
    email = f"gamer_{ts}@align.local"
    pw = "SecurePassword123!"

    reg = client.post("/api/v1/auth/register", json={"name": "Gamer Pro", "email": email, "password": pw})
    user_id = reg.json()["id"]

    token = client.post("/api/v1/auth/login", json={"email": email, "password": pw}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check Initial Gamification Profile
    gam_resp = client.get("/api/v1/gamification/me", headers=headers)
    assert gam_resp.status_code == 200
    data = gam_resp.json()
    assert data["xp_points"] >= 100
    assert data["current_level"] >= 1
    assert any(b["badge_key"] == "PIONEER" for b in data["badges"])

    # 2. Award XP via service with Dedup Key
    dedup = f"custom_action_{ts}"
    res1 = award_xp(db, user_id, "benchmark_action", 50, "Completed verified task", dedup_key=dedup)
    assert res1["status"] == "ok"
    assert res1["xp_awarded"] == 50
    xp_after_first = res1["total_xp"]

    # 3. Anti-Duplicate Protection: Attempt exact same action again
    res2 = award_xp(db, user_id, "benchmark_action", 50, "Completed verified task", dedup_key=dedup)
    assert res2["status"] == "duplicate"
    assert res2["xp_awarded"] == 0
    assert res2["total_xp"] == xp_after_first  # Points DID NOT change

    # 4. Check XP Transaction History endpoint
    hist_resp = client.get("/api/v1/gamification/history", headers=headers)
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert hist["total_transactions"] >= 2
    assert any(item["dedup_key"] == dedup for item in hist["items"])


def test_notification_multi_event_triggers_and_management(client: TestClient, db: Session):
    ts = int(time.time() * 1000)
    u1_email = f"notif1_{ts}@align.local"
    u2_email = f"notif2_{ts}@align.local"
    pw = "SecurePassword123!"

    u1_id = client.post("/api/v1/auth/register", json={"name": "Notif User 1", "email": u1_email, "password": pw}).json()["id"]
    u2_id = client.post("/api/v1/auth/register", json={"name": "Notif User 2", "email": u2_email, "password": pw}).json()["id"]

    t1 = client.post("/api/v1/auth/login", json={"email": u1_email, "password": pw}).json()["access_token"]
    t2 = client.post("/api/v1/auth/login", json={"email": u2_email, "password": pw}).json()["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}

    # 1. Connection request triggers notification
    req_resp = client.post(f"/api/v1/users/{u2_id}/connect", headers=h1)
    assert req_resp.status_code == 200
    conn_id = req_resp.json()["connection_id"]

    # U2 checks notifications
    n_resp = client.get("/api/v1/notifications", headers=h2)
    assert n_resp.status_code == 200
    notifs = n_resp.json()
    assert len(notifs) >= 1
    assert any("Connection Request" in n["title"] for n in notifs)

    # 2. Connection accept triggers notification back to U1
    client.post(f"/api/v1/users/connections/{conn_id}/accept", headers=h2)
    n1_resp = client.get("/api/v1/notifications", headers=h1)
    assert any("Connection Accepted" in n["title"] for n in n1_resp.json())

    # 3. Notification Read All & Count
    unread_c = client.get("/api/v1/notifications/unread/count", headers=h2).json()["unread_count"]
    assert unread_c >= 1

    read_all = client.post("/api/v1/notifications/read-all", headers=h2)
    assert read_all.status_code == 200

    unread_after = client.get("/api/v1/notifications/unread/count", headers=h2).json()["unread_count"]
    assert unread_after == 0
