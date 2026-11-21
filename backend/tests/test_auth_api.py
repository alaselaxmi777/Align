import uuid

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["pgvector"] == "enabled"

def test_register_and_login_flow(client):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    reg_payload = {
        "name": "Alex Mercer",
        "email": unique_email,
        "password": "Password123!"
    }
    # 1. Register
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == unique_email
    assert user_data["name"] == "Alex Mercer"

    # 2. Duplicate registration fails
    dup_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 409

    # 3. Login
    login_res = client.post("/api/v1/auth/login", json={"email": unique_email, "password": "Password123!"})
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data

    # 4. Access /auth/me with bearer token
    token = token_data["access_token"]
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == unique_email

def test_forgot_and_reset_password_flow(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")
    monkeypatch.setattr(settings, "smtp_username", "testuser")

    captured_tokens = {}
    def mock_send_reset(email, token):
        captured_tokens[email] = token
        return True

    monkeypatch.setattr("app.api.routes.auth.send_password_reset_email", mock_send_reset)

    unique_email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"name": "Reset Tester", "email": unique_email, "password": "OldPassword123!"})

    # Request reset
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": unique_email})
    assert forgot_res.status_code == 200
    assert forgot_res.json().get("dev_token") is None
    dev_token = captured_tokens.get(unique_email)
    assert dev_token is not None

    # Reset password using token
    reset_res = client.post("/api/v1/auth/reset-password", json={"token": dev_token, "new_password": "NewPassword123!"})
    assert reset_res.status_code == 200

    # Old password fails
    old_login = client.post("/api/v1/auth/login", json={"email": unique_email, "password": "OldPassword123!"})
    assert old_login.status_code == 401

    # New password succeeds
    new_login = client.post("/api/v1/auth/login", json={"email": unique_email, "password": "NewPassword123!"})
    assert new_login.status_code == 200

def test_email_verification_flow(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")
    monkeypatch.setattr(settings, "smtp_username", "testuser")

    captured_tokens = {}
    def mock_send_verif(email, token):
        captured_tokens[email] = token
        return True

    monkeypatch.setattr("app.api.routes.auth.send_verification_email", mock_send_verif)

    unique_email = f"verify_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"name": "Verify Tester", "email": unique_email, "password": "Password123!"})
    login_res = client.post("/api/v1/auth/login", json={"email": unique_email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Request verification token
    send_res = client.post("/api/v1/auth/send-verification", headers=headers)
    assert send_res.status_code == 200
    assert send_res.json().get("dev_token") is None
    dev_token = captured_tokens.get(unique_email)
    assert dev_token is not None

    # Verify with invalid token fails
    bad_res = client.post("/api/v1/auth/verify-email", json={"token": "invalid_token_123"}, headers=headers)
    assert bad_res.status_code == 400

    # Verify with correct token succeeds
    good_res = client.post("/api/v1/auth/verify-email", json={"token": dev_token}, headers=headers)
    assert good_res.status_code == 200

    # Check that user is now marked verified
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["is_verified"] is True

def test_connections_flow(client):
    # Register two users
    email1 = f"conn1_{uuid.uuid4().hex[:8]}@example.com"
    email2 = f"conn2_{uuid.uuid4().hex[:8]}@example.com"

    r1 = client.post("/api/v1/auth/register", json={"name": "Peer Alpha", "email": email1, "password": "Password123!"})
    u1_id = r1.json()["id"]
    r2 = client.post("/api/v1/auth/register", json={"name": "Peer Beta", "email": email2, "password": "Password123!"})
    u2_id = r2.json()["id"]

    # Login user 1
    t1 = client.post("/api/v1/auth/login", json={"email": email1, "password": "Password123!"}).json()["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}

    # Login user 2
    t2 = client.post("/api/v1/auth/login", json={"email": email2, "password": "Password123!"}).json()["access_token"]
    h2 = {"Authorization": f"Bearer {t2}"}

    # User 1 sends connection request to User 2
    req_res = client.post(f"/api/v1/users/{u2_id}/connect", headers=h1)
    assert req_res.status_code == 200
    conn_data = req_res.json()
    assert conn_data["connection_status"] == "pending"
    conn_id = conn_data["connection_id"]

    # Check connection status from User 2 perspective
    st_res = client.get(f"/api/v1/users/{u1_id}/connection-status", headers=h2)
    assert st_res.status_code == 200
    assert st_res.json()["status"] == "pending"
    assert st_res.json()["is_sender"] is False

    # User 2 accepts connection
    accept_res = client.post(f"/api/v1/users/connections/{conn_id}/accept", headers=h2)
    assert accept_res.status_code == 200

    # User 1 checks connections
    my_conns = client.get("/api/v1/users/me/connections", headers=h1)
    assert my_conns.status_code == 200
    conns_list = my_conns.json()
    assert len(conns_list) >= 1
    assert any(c["partner_id"] == u2_id and c["status"] == "accepted" for c in conns_list)


def test_onboarding_and_embedding_flow(client):
    uid = uuid.uuid4().hex[:8]
    email = f"onboard_{uid}@example.com"
    pwd = "Password123!"

    # 1. Register
    reg = client.post("/api/v1/auth/register", json={"name": "Onboarding Tester", "email": email, "password": pwd})
    assert reg.status_code == 201

    # 2. Login - should show onboarding_completed is False initially
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["onboarding_completed"] is False
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Complete onboarding
    onboard_payload = {
        "bio": "Robotics engineer and autonomous systems developer passionate about reinforcement learning.",
        "location": "Boston, MA",
        "interests": ["Robotics", "Autonomous Vehicles", "Reinforcement Learning"],
        "skills": ["Python", "ROS2", "C++", "PyTorch"],
        "goals": "Build multi-agent autonomous robotic navigation frameworks",
        "preferred_activities": ["Hackathons", "Workshops"],
        "preferred_community_types": ["Technical & Engineering", "Research & Academia"],
        "privacy_level": "public",
    }
    res_onboard = client.post("/api/v1/auth/onboarding", json=onboard_payload, headers=headers)
    assert res_onboard.status_code == 200
    p = res_onboard.json()
    assert p["onboarding_completed"] is True
    assert "Robotics" in p["interests"]
    assert "ROS2" in p["skills"]

    # 4. Next login reflects onboarding_completed is True
    login_again = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_again.status_code == 200
    assert login_again.json()["onboarding_completed"] is True


def test_people_discovery_semantic_ranking(client):
    uid1 = uuid.uuid4().hex[:8]
    uid2 = uuid.uuid4().hex[:8]

    # Create Alice with AI interests
    email1 = f"alice_{uid1}@example.com"
    pwd = "Password123!"
    client.post("/api/v1/auth/register", json={"name": "Alice ML", "email": email1, "password": pwd})
    t1 = client.post("/api/v1/auth/login", json={"email": email1, "password": pwd}).json()["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}
    client.post("/api/v1/auth/onboarding", headers=h1, json={
        "bio": "Deep learning researcher focusing on Transformers and PyTorch.",
        "location": "Seattle, WA",
        "interests": ["Deep Learning", "Transformers", "NLP"],
        "skills": ["Python", "PyTorch", "HuggingFace"],
        "goals": "Publish LLM interpretability papers",
    })

    # Create Bob with matching AI skills
    email2 = f"bob_{uid2}@example.com"
    client.post("/api/v1/auth/register", json={"name": "Bob PyTorch", "email": email2, "password": pwd})
    t2 = client.post("/api/v1/auth/login", json={"email": email2, "password": pwd}).json()["access_token"]
    h2 = {"Authorization": f"Bearer {t2}"}
    client.post("/api/v1/auth/onboarding", headers=h2, json={
        "bio": "ML engineer scaling PyTorch transformer inference.",
        "location": "Seattle, WA",
        "interests": ["Transformers", "Deep Learning"],
        "skills": ["PyTorch", "Python", "CUDA"],
        "goals": "Optimize open-source foundation models",
    })

    # Alice queries People Discovery
    res_people = client.get("/api/v1/users?q=Transformers", headers=h1)
    assert res_people.status_code == 200
    people = res_people.json()
    assert len(people) > 0

    bob = next((p for p in people if "Bob PyTorch" in p["name"]), None)
    assert bob is not None
    assert "recommendation_reason" in bob
    assert len(bob["recommendation_reason"]) > 0
    assert bob["connection_status"] in ("none", "pending", "accepted")


def test_refresh_token_rotation_and_reuse_detection(client):
    uid = uuid.uuid4().hex[:8]
    email = f"rotation_{uid}@example.com"
    pwd = "ValidPass123!"
    client.post("/api/v1/auth/register", json={"name": "Rotator", "email": email, "password": pwd})

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token1 = login_res.json()["refresh_token"]

    # 1. Rotate token
    rotate_res = client.post("/api/v1/auth/refresh", json={"refresh_token": token1})
    assert rotate_res.status_code == 200
    token2 = rotate_res.json()["refresh_token"]
    assert token2 != token1

    # 2. Token reuse detection: Re-using token1 must fail with 401 and revoke the family
    reuse_res = client.post("/api/v1/auth/refresh", json={"refresh_token": token1})
    assert reuse_res.status_code == 401
    assert "reused" in reuse_res.json()["detail"].lower() or "revoked" in reuse_res.json()["detail"].lower()

    # 3. token2 was also revoked because of family revocation
    next_res = client.post("/api/v1/auth/refresh", json={"refresh_token": token2})
    assert next_res.status_code == 401


def test_logout_and_logout_all(client):
    uid = uuid.uuid4().hex[:8]
    email = f"logout_{uid}@example.com"
    pwd = "ValidPass123!"
    client.post("/api/v1/auth/register", json={"name": "LogoutUser", "email": email, "password": pwd})

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    t_data = login_res.json()
    refresh = t_data["refresh_token"]

    # Logout single
    lo_res = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert lo_res.status_code == 200
    # Refresh should fail now
    ref_fail = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert ref_fail.status_code == 401

    # Login again
    l2 = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    acc2 = l2.json()["access_token"]
    ref2 = l2.json()["refresh_token"]

    # Logout all
    lo_all = client.post("/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {acc2}"})
    assert lo_all.status_code == 200
    # Refresh should fail
    ref2_fail = client.post("/api/v1/auth/refresh", json={"refresh_token": ref2})
    assert ref2_fail.status_code == 401


def test_change_password_flow(client):
    uid = uuid.uuid4().hex[:8]
    email = f"pwdchange_{uid}@example.com"
    old_pwd = "OldPassword123!"
    new_pwd = "NewSecurePassword456!"
    client.post("/api/v1/auth/register", json={"name": "PwdChanger", "email": email, "password": old_pwd})

    l_res = client.post("/api/v1/auth/login", json={"email": email, "password": old_pwd})
    acc = l_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {acc}"}

    # Wrong old password
    fail_res = client.post("/api/v1/auth/change-password", headers=headers, json={
        "old_password": "WrongOldPassword999!",
        "new_password": new_pwd,
    })
    assert fail_res.status_code == 400

    # Common weak password
    weak_res = client.post("/api/v1/auth/change-password", headers=headers, json={
        "old_password": old_pwd,
        "new_password": "password",
    })
    assert weak_res.status_code == 400

    # Successful change
    succ_res = client.post("/api/v1/auth/change-password", headers=headers, json={
        "old_password": old_pwd,
        "new_password": new_pwd,
    })
    assert succ_res.status_code == 200

    # Old password fails login
    old_login = client.post("/api/v1/auth/login", json={"email": email, "password": old_pwd})
    assert old_login.status_code == 401

    # New password succeeds
    new_login = client.post("/api/v1/auth/login", json={"email": email, "password": new_pwd})
    assert new_login.status_code == 200


def test_user_export_and_deletion(client):
    uid = uuid.uuid4().hex[:8]
    email = f"gdpr_{uid}@example.com"
    pwd = "ValidPass123!"
    client.post("/api/v1/auth/register", json={"name": "GDPR User", "email": email, "password": pwd})
    l_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    acc = l_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {acc}"}

    # Export
    exp_res = client.get("/api/v1/users/me/export", headers=headers)
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert "account" in exp_data
    assert exp_data["account"]["email"] == email
    assert "export_generated_at" in exp_data

    # Delete
    del_res = client.delete("/api/v1/users/me", headers=headers)
    assert del_res.status_code == 200

    # User no longer exists
    after_login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert after_login.status_code == 401
