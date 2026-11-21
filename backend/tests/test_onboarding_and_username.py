import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User, Profile

def test_check_username_endpoint(client: TestClient, db: Session):
    # 1. Check an available valid username
    res = client.get("/api/v1/users/check-username?username=cool_dev99")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is True
    assert data["username"] == "cool_dev99"

    # 2. Check an invalid format username (too short or special chars)
    res = client.get("/api/v1/users/check-username?username=ab")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is False

    res = client.get("/api/v1/users/check-username?username=bad@user!")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is False

    # 3. Check reserved username
    res = client.get("/api/v1/users/check-username?username=admin")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is False
    assert "reserved" in data["message"].lower()

def test_multi_step_onboarding_flow(client: TestClient, db: Session):
    # Register a new user
    import uuid
    uid = uuid.uuid4().hex[:8]
    reg_res = client.post("/api/v1/auth/register", json={
        "name": f"Onboard User {uid}",
        "email": f"onboard_{uid}@example.com",
        "password": "Password123!"
    })
    assert reg_res.status_code == 201

    login_res = client.post("/api/v1/auth/login", json={
        "email": f"onboard_{uid}@example.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Claim username
    handle = f"user_{uid}"
    s1_res = client.post("/api/v1/auth/onboarding", json={
        "username": handle,
        "step": 2
    }, headers=headers)
    assert s1_res.status_code == 200
    assert s1_res.json()["onboarding_completed"] is False

    # Step 2: Name & Bio
    s2_res = client.post("/api/v1/auth/onboarding", json={
        "name": f"Updated Name {uid}",
        "bio": "Full-stack engineer passionate about decentralized systems and AI.",
        "step": 3
    }, headers=headers)
    assert s2_res.status_code == 200
    assert s2_res.json()["onboarding_completed"] is False

    # Step 3: Demographics & Location
    s3_res = client.post("/api/v1/auth/onboarding", json={
        "age_cohort": "18-24",
        "gender": "Female",
        "preferred_language": "English",
        "location": "Pune",
        "privacy_level": "public",
        "step": 3
    }, headers=headers)
    assert s3_res.status_code == 200
    assert s3_res.json()["onboarding_completed"] is False

    # Step 4: Final submission
    s4_res = client.post("/api/v1/auth/onboarding", json={
        "username": handle,
        "skills": "Python, React, FastAPI, Machine Learning",
        "skill_proficiency": "Intermediate",
        "hobbies": "Cycling, Reading, Open Source",
        "goals": "Build a multi-agent recommendation engine in Pune",
        "step": 4
    }, headers=headers)
    assert s4_res.status_code == 200
    profile_data = s4_res.json()
    assert profile_data["onboarding_completed"] is True

    # Verify me endpoint reflects completed status & username
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == handle
    assert me_data["onboarding_completed"] is True
