import uuid

def test_communities_lifecycle(client, auth_headers):
    # 1. List communities
    list_res = client.get("/api/v1/communities")
    assert list_res.status_code == 200
    assert isinstance(list_res.json(), list)

    # 2. Create community
    comm_name = f"Test Group {uuid.uuid4().hex[:6]}"
    create_res = client.post(
        "/api/v1/communities",
        json={
            "name": comm_name,
            "description": "A test community exploring algorithms and design systems.",
            "category": "Technology",
            "tags": "tech, algorithms",
            "location": "Online"
        },
        headers=auth_headers
    )
    assert create_res.status_code == 201
    created_comm = create_res.json()
    assert created_comm["name"] == comm_name
    comm_id = created_comm["id"]

    # 3. Get community detail
    get_res = client.get(f"/api/v1/communities/{comm_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == comm_name
    assert get_res.json()["is_member"] is True

    # 4. Leave community
    leave_res = client.post(f"/api/v1/communities/{comm_id}/leave", headers=auth_headers)
    assert leave_res.status_code == 200

    # 5. Join community
    join_res = client.post(f"/api/v1/communities/{comm_id}/join", headers=auth_headers)
    assert join_res.status_code == 200

def test_events_lifecycle(client, auth_headers):
    # 1. List events
    list_res = client.get("/api/v1/events")
    assert list_res.status_code == 200
    assert isinstance(list_res.json(), list)

    # 2. Create event
    event_title = f"Test Hackathon {uuid.uuid4().hex[:6]}"
    create_res = client.post(
        "/api/v1/events",
        json={
            "title": event_title,
            "description": "Collaborative coding and project showcase.",
            "category": "Hackathon",
            "location": "Online",
            "capacity": 20
        },
        headers=auth_headers
    )
    assert create_res.status_code == 201
    created_event = create_res.json()
    event_id = created_event["id"]

    # 3. Register for event
    reg_res = client.post(f"/api/v1/events/{event_id}/register", headers=auth_headers)
    assert reg_res.status_code == 200

    # 4. Check status
    get_res = client.get(f"/api/v1/events/{event_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["is_registered"] is True

    # 5. Cancel registration
    cancel_res = client.post(f"/api/v1/events/{event_id}/cancel", headers=auth_headers)
    assert cancel_res.status_code == 200

def test_event_capacity_and_duplicate_registration(client, auth_headers):
    # Create event with capacity 1
    create_res = client.post(
        "/api/v1/events",
        json={
            "title": f"Limited Workshop {uuid.uuid4().hex[:6]}",
            "description": "Exclusive single seat workshop.",
            "category": "Workshop",
            "location": "Online",
            "capacity": 1
        },
        headers=auth_headers
    )
    assert create_res.status_code == 201
    evt_id = create_res.json()["id"]

    # Register first attendee
    r1 = client.post(f"/api/v1/events/{evt_id}/register", headers=auth_headers)
    assert r1.status_code == 200

    # Duplicate registration fails
    dup = client.post(f"/api/v1/events/{evt_id}/register", headers=auth_headers)
    assert dup.status_code == 400

    # Register second attendee with a different user -> fails due to capacity limit
    u2_email = f"cap_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"name": "Second Attendee", "email": u2_email, "password": "Password123!"})
    t2 = client.post("/api/v1/auth/login", json={"email": u2_email, "password": "Password123!"}).json()["access_token"]
    h2 = {"Authorization": f"Bearer {t2}"}

    over_cap = client.post(f"/api/v1/events/{evt_id}/register", headers=h2)
    assert over_cap.status_code == 400
    assert "capacity" in over_cap.json()["detail"].lower()
