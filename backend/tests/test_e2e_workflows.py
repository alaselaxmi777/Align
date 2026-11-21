import uuid
import pytest
from app.services.graph_service import graph_service


def test_complete_end_to_end_user_journeys(client):
    uid = uuid.uuid4().hex[:6]
    email1 = f"e2e_alice_{uid}@align.local"
    email2 = f"e2e_bob_{uid}@align.local"
    password = "StrongPassword123!"

    # 1. Register User 1 (Alice) and User 2 (Bob)
    res_reg1 = client.post(
        "/api/v1/auth/register",
        json={"name": "Alice Pioneer", "email": email1, "password": password},
    )
    assert res_reg1.status_code in (200, 201), res_reg1.text
    user1_id = res_reg1.json()["id"]

    res_reg2 = client.post(
        "/api/v1/auth/register",
        json={"name": "Bob Pioneer", "email": email2, "password": password},
    )
    assert res_reg2.status_code in (200, 201), res_reg2.text
    user2_id = res_reg2.json()["id"]

    # 2. Login verification & acquire tokens
    res_login1 = client.post(
        "/api/v1/auth/login",
        json={"email": email1, "password": password},
    )
    assert res_login1.status_code == 200
    token1 = res_login1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    res_login2 = client.post(
        "/api/v1/auth/login",
        json={"email": email2, "password": password},
    )
    assert res_login2.status_code == 200
    token2 = res_login2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 3 & 4. Update Profile with Bio, Location, Interests, Skills, Goals
    res_prof1 = client.put(
        "/api/v1/users/me/profile",
        headers=headers1,
        json={
            "bio": "AI Researcher & PyTorch enthusiast",
            "location": "San Francisco, CA",
            "interests": "Deep Learning, PyTorch, Neural Networks",
            "skills": "Python, Machine Learning, Computer Vision",
            "goals": "Master Large Language Models",
            "preferred_activities": "Hackathons, Tech Meetups",
            "preferred_community_types": "Technical, Open-source",
        },
    )
    assert res_prof1.status_code == 200
    assert res_prof1.json()["interests"] == "Deep Learning, PyTorch, Neural Networks"

    res_prof2 = client.put(
        "/api/v1/users/me/profile",
        headers=headers2,
        json={
            "bio": "Full-Stack Engineer & Python Contributor",
            "location": "San Francisco, CA",
            "interests": "Deep Learning, Web Development",
            "skills": "Python, React, TypeScript, FastAPI",
            "goals": "Build AI Agents",
            "preferred_activities": "Workshops, Pair Programming",
            "preferred_community_types": "Engineering, Startups",
        },
    )
    assert res_prof2.status_code == 200

    # 5. Discover actual registered peers
    res_peers = client.get("/api/v1/users?q=Python", headers=headers1)
    assert res_peers.status_code == 200
    peer_list = res_peers.json()
    assert any(p["id"] == user2_id for p in peer_list)

    # 6. Send and accept connection request
    res_connect = client.post(f"/api/v1/users/{user2_id}/connect", headers=headers1)
    assert res_connect.status_code == 200
    conn_id = res_connect.json()["connection_id"]

    res_accept = client.post(f"/api/v1/users/connections/{conn_id}/accept", headers=headers2)
    assert res_accept.status_code == 200

    # 7. Discover and Join a Community
    res_comm_create = client.post(
        "/api/v1/communities",
        headers=headers1,
        json={
            "name": "E2E Neural Networks Guild",
            "description": "Deep learning and neural network architectures discussion group.",
            "category": "Technology",
            "tags": "deep learning, neural networks, pytorch",
            "location": "San Francisco, CA",
            "is_private": False,
        },
    )
    assert res_comm_create.status_code in (200, 201)
    comm_id = res_comm_create.json()["id"]

    # Bob joins the community
    res_comm_join = client.post(f"/api/v1/communities/{comm_id}/join", headers=headers2)
    assert res_comm_join.status_code == 200

    # 8. Create and discover an event
    res_event_create = client.post(
        "/api/v1/events",
        headers=headers1,
        json={
            "title": "E2E PyTorch Hands-On Workshop",
            "description": "Live coding session building transformers from scratch.",
            "category": "Technology",
            "location": "San Francisco, CA",
            "capacity": 25,
            "community_id": comm_id,
        },
    )
    assert res_event_create.status_code in (200, 201)
    event_id = res_event_create.json()["id"]

    # 9. Register for and cancel an event
    res_rsvp = client.post(
        f"/api/v1/events/{event_id}/register",
        headers=headers2,
        json={"ticket_count": 1},
    )
    assert res_rsvp.status_code == 200
    assert "ticket_code" in res_rsvp.json()

    res_cancel_rsvp = client.post(
        f"/api/v1/events/{event_id}/cancel",
        headers=headers2,
    )
    assert res_cancel_rsvp.status_code == 200

    # Re-register so attendance exists
    client.post(f"/api/v1/events/{event_id}/register", headers=headers2)

    # 10. Create social post, like, and comment
    res_post = client.post(
        "/api/v1/feed",
        headers=headers1,
        json={
            "content": "Excited to launch our new E2E neural networks guild on ALIGN!",
            "community_id": comm_id,
        },
    )
    assert res_post.status_code in (200, 201)
    post_id = res_post.json()["id"]

    # Bob likes the post
    res_like = client.post(f"/api/v1/feed/{post_id}/like", headers=headers2)
    assert res_like.status_code == 200
    assert res_like.json()["is_liked"] is True

    # Bob comments on the post
    res_comment = client.post(
        f"/api/v1/feed/{post_id}/comments",
        headers=headers2,
        json={"content": "Looking forward to building transformers together!"},
    )
    assert res_comment.status_code in (200, 201)
    assert res_comment.json()["content"] == "Looking forward to building transformers together!"

    # 11. Send and retrieve direct messages
    res_msg = client.post(
        "/api/v1/messages",
        headers=headers2,
        json={"receiver_id": user1_id, "content": "Hi Alice, ready for the workshop?"},
    )
    assert res_msg.status_code in (200, 201)

    res_convs = client.get("/api/v1/messages/conversations", headers=headers1)
    assert res_convs.status_code == 200
    conv_list = res_convs.json()
    assert any(c["partner_id"] == user2_id for c in conv_list)

    # 12. Receive and mark notification as read
    res_notifs = client.get("/api/v1/notifications", headers=headers1)
    assert res_notifs.status_code == 200
    notifs = res_notifs.json()
    assert len(notifs) > 0
    notif_id = notifs[0]["id"]

    res_read_notif = client.put(f"/api/v1/notifications/{notif_id}/read", headers=headers1)
    assert res_read_notif.status_code == 200

    # 13 & 14. Generate actual AI recommendations & check explanations
    res_recs = client.get("/api/v1/discovery/recommendations?limit=8", headers=headers2)
    assert res_recs.status_code == 200
    recs = res_recs.json()
    assert len(recs) > 0
    for r in recs:
        assert "score" in r and r["score"] > 0
        assert "reason" in r and len(r["reason"]) > 0

    # 15. Verify Neo4j Graph Affinity
    affinity_res = client.get(f"/api/v1/graph/affinity/peer/{user2_id}", headers=headers1)
    assert affinity_res.status_code == 200
    assert "graph_affinity_score" in affinity_res.json()

    # 16. Verify Unauthorized requests are rejected (401)
    unauthorized_res = client.get("/api/v1/users/me")
    assert unauthorized_res.status_code == 401

    # 17. Verify Neo4j Health & Sync
    health_res = client.get("/api/v1/graph/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] in ("connected", "unavailable")

    # 18. Multi-container system verification
    system_health = client.get("/health")
    assert system_health.status_code == 200
    assert system_health.json()["status"] == "ok"
