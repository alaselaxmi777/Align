import uuid
import pytest
from starlette.testclient import TestClient

def test_ai_personal_assistant(client: TestClient, auth_headers: dict):
    # 1. Ask assistant a query
    res = client.post(
        "/api/v1/assistant/chat",
        headers=auth_headers,
        json={"message": "Recommend communities for learning programming"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "assistant"
    assert "conversation_id" in data
    assert len(data["content"]) > 10
    assert "action_cards" in data
    assert len(data["suggested_prompts"]) > 0

    conv_id = data["conversation_id"]

    # 2. Ask follow-up question
    res2 = client.post(
        "/api/v1/assistant/chat",
        headers=auth_headers,
        json={"message": "Find upcoming technology events", "conversation_id": conv_id},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["conversation_id"] == conv_id

    # 3. List conversations
    res_convs = client.get("/api/v1/assistant/conversations", headers=auth_headers)
    assert res_convs.status_code == 200
    assert len(res_convs.json()) >= 1

    # 4. Get message history
    res_hist = client.get(f"/api/v1/assistant/conversations/{conv_id}/messages", headers=auth_headers)
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 4  # 2 user + 2 assistant messages

def test_smart_people_matching(client: TestClient, auth_headers: dict):
    # Retrieve smart peer matches
    res = client.get("/api/v1/matching/peers?min_score=10&limit=10", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_matched" in data
    assert "results" in data
    if data["results"]:
        match = data["results"][0]
        assert "compatibility" in match
        comp = match["compatibility"]
        assert "overall_percentage" in comp
        assert "semantic_similarity" in comp
        assert "skill_synergy" in comp
        assert "shared_goals" in comp
        assert "explanation" in comp

def test_interest_circles_lifecycle(client: TestClient, auth_headers: dict):
    # 1. Create an Interest Circle
    tag = uuid.uuid4().hex[:6]
    res = client.post(
        "/api/v1/circles",
        headers=auth_headers,
        json={
            "name": f"Robotics Hackers {tag}",
            "tagline": "Autonomous systems & ROS2 builds",
            "description": "Weekly deep-dives into robot kinematics and sensor fusion.",
            "category": "Technology",
            "tags": "Robotics, ROS2, C++, Hardware",
            "max_members": 20,
        },
    )
    assert res.status_code == 201
    circle = res.json()
    circle_id = circle["id"]
    assert circle["is_admin"] is True
    assert circle["member_count"] == 1

    # 2. List Circles
    res_list = client.get("/api/v1/circles?limit=10", headers=auth_headers)
    assert res_list.status_code == 200
    assert any(c["id"] == circle_id for c in res_list.json())

    # 3. Post a Discussion
    res_disc = client.post(
        f"/api/v1/circles/{circle_id}/discussions",
        headers=auth_headers,
        json={"title": "Lidar Odometry Paper", "content": "Let us review Fast-LIO2 this Thursday!"},
    )
    assert res_disc.status_code == 201
    disc_id = res_disc.json()["id"]

    # 4. Reply to Discussion
    res_rep = client.post(
        f"/api/v1/circles/{circle_id}/discussions/{disc_id}/replies",
        headers=auth_headers,
        json={"content": "I can share our simulation bag files."},
    )
    assert res_rep.status_code == 201

    # 5. Schedule an Activity
    res_act = client.post(
        f"/api/v1/circles/{circle_id}/activities",
        headers=auth_headers,
        json={
            "title": "Weekly ROS2 Jam",
            "description": "Pair programming on autonomous navigation stack.",
            "activity_type": "study_session",
            "scheduled_at": "2026-11-20T10:00:00Z",
            "location_or_link": "Google Meet",
        },
    )
    assert res_act.status_code == 201

def test_ai_goal_journey_workflow(client: TestClient, auth_headers: dict):
    # 1. Generate an AI Goal Journey
    res = client.post(
        "/api/v1/goals/generate",
        headers=auth_headers,
        json={
            "title": "Become a Senior Machine Learning Engineer",
            "timeframe": "6 months",
            "category": "AI & Data Science",
        },
    )
    assert res.status_code == 201
    journey = res.json()
    journey_id = journey["id"]
    assert journey["progress_percentage"] == 0
    assert len(journey["milestones"]) >= 4

    first_milestone = journey["milestones"][0]
    assert first_milestone["is_completed"] is False
    assert len(first_milestone["resources"]) > 0

    # 2. Toggle milestone completion
    res_comp = client.patch(
        f"/api/v1/goals/{journey_id}/milestones/{first_milestone['id']}",
        headers=auth_headers,
    )
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert comp_data["is_completed"] is True
    assert comp_data["journey_progress"] > 0
    assert comp_data["gamification"] is not None

    # 3. Retrieve journey by ID
    res_get = client.get(f"/api/v1/goals/{journey_id}", headers=auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["completed_milestones"] == 1

def test_gamification_profile_and_leaderboard(client: TestClient, auth_headers: dict):
    # 1. Fetch current gamification status
    res = client.get("/api/v1/gamification/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["xp_points"] >= 100
    assert data["current_level"] >= 1
    assert data["current_streak_days"] >= 1
    assert "badges" in data
    assert "recent_activities" in data

    # 2. Fetch leaderboard
    res_lead = client.get("/api/v1/gamification/leaderboard", headers=auth_headers)
    assert res_lead.status_code == 200
    lead = res_lead.json()
    assert len(lead) >= 1
    assert any(p["is_me"] is True for p in lead)

def test_project_collaboration_lifecycle(client: TestClient, auth_headers: dict):
    # 1. Publish a Project
    tag = uuid.uuid4().hex[:6]
    res = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={
            "title": f"Autonomous Rover AI {tag}",
            "tagline": "Open-source exploration rover with vision",
            "description": "Building a four-wheel rover running edge AI object detection.",
            "category": "Robotics & Hardware",
            "required_roles": "PyTorch Specialist, Frontend Visualizer",
            "skills_needed": "Python, OpenCV, React, ROS2",
            "github_repo_url": "https://github.com/align-org/rover-ai",
        },
    )
    assert res.status_code == 201
    proj = res.json()
    project_id = proj["id"]
    assert proj["is_owner"] is True
    assert proj["team_size"] == 1

    # 2. Add a project milestone
    res_ms = client.post(
        f"/api/v1/projects/{project_id}/milestones",
        headers=auth_headers,
        json={"title": "Camera calibration & depth inference", "step_order": 1},
    )
    assert res_ms.status_code == 201

    # 3. List projects
    res_list = client.get("/api/v1/projects", headers=auth_headers)
    assert res_list.status_code == 200
    assert any(p["id"] == project_id for p in res_list.json())

def test_opportunity_discovery_and_map(client: TestClient, auth_headers: dict):
    # 1. List opportunities (auto-seeds verified items)
    res_opps = client.get("/api/v1/opportunities", headers=auth_headers)
    assert res_opps.status_code == 200
    opps = res_opps.json()
    assert len(opps) >= 5

    first_opp = opps[0]
    opp_id = first_opp["id"]

    # 2. Bookmark opportunity (idempotent toggle check)
    res_bm = client.post(f"/api/v1/opportunities/{opp_id}/bookmark", headers=auth_headers)
    assert res_bm.status_code == 200
    if not res_bm.json()["is_bookmarked"]:
        res_bm = client.post(f"/api/v1/opportunities/{opp_id}/bookmark", headers=auth_headers)
        assert res_bm.status_code == 200
    assert res_bm.json()["is_bookmarked"] is True

    # 3. List bookmarks
    res_my_bms = client.get("/api/v1/opportunities/my/bookmarks", headers=auth_headers)
    assert res_my_bms.status_code == 200
    assert any(o["id"] == opp_id for o in res_my_bms.json())

    # 4. Map markers endpoint
    res_map = client.get("/api/v1/places/map/markers", headers=auth_headers)
    assert res_map.status_code == 200
    markers = res_map.json()
    assert len(markers) >= 3
    assert all("latitude" in m and "longitude" in m for m in markers)
