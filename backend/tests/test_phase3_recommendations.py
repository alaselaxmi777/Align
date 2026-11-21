import time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User, Profile
from app.models.community import Community
from app.models.event import Event
from app.models.place import Place
from app.models.project import Project
from app.models.opportunity import Opportunity
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.saved import SavedItem
from app.core.security import create_access_token, hash_password
from app.services.embeddings import generate_embedding


def test_recommendation_pipeline_all_entities_and_required_fields(client: TestClient, db: Session):
    timestamp = int(time.time() * 1000)

    # 1. Seed Real Database Records across all 6 required entities
    # User
    peer = User(
        name=f"Dr. Aisha Verma {timestamp}",
        email=f"aisha_{timestamp}@align.local",
        password_hash=hash_password("Pass123!"),
        is_active=True
    )
    db.add(peer)
    db.flush()
    peer_prof = Profile(
        user_id=peer.id,
        bio="Senior Deep Learning Engineer working on vision-language models and robotics.",
        skills="Python, PyTorch, ROS2, Computer Vision",
        interests="Autonomous Agents, Robotics, Multi-modal AI",
        goals="Build open source autonomous humanoid agents",
        location="Pune, India",
        latitude=18.5204,
        longitude=73.8567,
    )
    peer_prof.embedding = generate_embedding(f"{peer.name} {peer_prof.bio} {peer_prof.skills} {peer_prof.interests}")
    db.add(peer_prof)

    # Community
    comm = Community(
        name=f"Robotics & Embodied AI Lab {timestamp}",
        description="Collaborative engineering guild building ROS2 robotics and deep reinforcement learning systems.",
        category="Robotics",
        tags="ros2, python, robotics, embodied-ai",
        location="Pune, India",
        latitude=18.5300,
        longitude=73.8500,
        embedding=generate_embedding("Robotics Embodied AI Lab collaborative engineering guild building ROS2 robotics"),
        created_by_id=peer.id
    )
    db.add(comm)

    # Event
    event = Event(
        title=f"Annual Multi-Modal AI Summit {timestamp}",
        description="Hands-on intensive conference on transformer architectures, robotics manipulation, and fine-tuning.",
        category="Conference",
        location="Baner, Pune",
        latitude=18.5590,
        longitude=73.7868,
        source="ALIGN",
        embedding=generate_embedding("Annual Multi-Modal AI Summit transformer architectures robotics manipulation"),
        created_by_id=peer.id
    )
    db.add(event)

    # Place
    place = Place(
        name=f"RoboTech Fabrication Hub {timestamp}",
        description="Makerspace and rapid hardware prototyping laboratory with GPU cluster access.",
        category="Makerspaces & Hardware",
        address="12 Senapati Bapat Road",
        city="Pune",
        latitude=18.5312,
        longitude=73.8291,
        source="OpenStreetMap",
        embedding=generate_embedding("RoboTech Fabrication Hub makerspace hardware prototyping laboratory GPU cluster")
    )
    db.add(place)

    # Project
    project = Project(
        title=f"Autonomous Warehouse Drone {timestamp}",
        tagline="ROS2-powered autonomous quadcopter for indoor inventory scanning.",
        description="Open source drone framework using depth sensors and SLAM algorithms for autonomous navigation.",
        category="Robotics",
        stage="prototyping",
        status="recruiting",
        skills_needed="ROS2, Python, C++, SLAM",
        required_roles="Embedded Engineer (1), Computer Vision Specialist (1)",
        created_by_id=peer.id,
        embedding=generate_embedding("Autonomous Warehouse Drone ROS2 autonomous quadcopter indoor scanning SLAM")
    )
    db.add(project)

    # Opportunity
    opportunity = Opportunity(
        title=f"National Robotics Fellowship 2026 {timestamp}",
        organization="Center for Autonomous Systems & AI",
        opportunity_type="fellowship",
        description="Fully funded 6-month research fellowship building real-world robotic manipulation pipelines.",
        location="Pune, India",
        is_remote=False,
        apply_url="https://align.local/opportunities/robotics-fellowship-2026",
        tags="robotics, fellowship, ai, python",
        source="Verified External",
        embedding=generate_embedding("National Robotics Fellowship 2026 fully funded research building real-world robotics")
    )
    db.add(opportunity)

    db.commit()

    # 2. Setup Authenticated Searcher User
    user = User(
        name=f"Seeker User {timestamp}",
        email=f"seeker_{timestamp}@align.local",
        password_hash=hash_password("Pass123!"),
        is_active=True
    )
    db.add(user)
    db.flush()
    user_prof = Profile(
        user_id=user.id,
        bio="Software engineer enthusiastic about robotics, Python, and autonomous systems.",
        skills="Python, PyTorch, Linux",
        interests="Robotics, Artificial Intelligence, Drones",
        goals="Transition into embodied AI research",
        location="Pune, India",
        latitude=18.5204,
        longitude=73.8567,
    )
    user_prof.embedding = generate_embedding(f"{user.name} {user_prof.bio} {user_prof.skills} {user_prof.interests}")
    db.add(user_prof)
    db.commit()

    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    # 3. Test Intent Search Pipeline
    search_resp = client.post(
        "/api/v1/discovery/search",
        headers=headers,
        json={"query": "I want to build robotics and ROS2 projects with Python near Pune", "limit": 20}
    )
    assert search_resp.status_code == 200, search_resp.text
    search_results = search_resp.json()
    assert len(search_results) > 0

    # 4. Assert Every Result Satisfies Required Schema and Resolves to Real DB Record
    entity_counts = {}
    for item in search_results:
        rtype = item["result_type"]
        item_id = item["id"]
        entity_counts[rtype] = entity_counts.get(rtype, 0) + 1

        # Check required fields
        assert item["title"], f"Missing title on {item}"
        assert item["description"] is not None
        assert item["score"] > 0.0 and item["score"] <= 1.0
        assert item["reason"], f"Missing reason on {item}"
        assert item["why_recommended"], f"Missing why_recommended on {item}"
        assert isinstance(item["matching_factors"], list)
        assert item["location_relevance"], f"Missing location_relevance on {item}"
        assert item["source"], f"Missing source on {item}"
        assert item["is_verified"] is True

        # STRICT DB RECORD RESOLUTION ASSERTION:
        # Every returned ID must resolve to a real record in the corresponding PostgreSQL database table
        if rtype == "community":
            db_record = db.get(Community, item_id)
            assert db_record is not None, f"Community id {item_id} does not exist in DB!"
            assert db_record.name == item["title"]
        elif rtype == "event":
            db_record = db.get(Event, item_id)
            assert db_record is not None, f"Event id {item_id} does not exist in DB!"
            assert db_record.title == item["title"]
        elif rtype == "place":
            db_record = db.get(Place, item_id)
            assert db_record is not None, f"Place id {item_id} does not exist in DB!"
            assert db_record.name == item["title"]
        elif rtype == "user":
            db_record = db.get(User, item_id)
            assert db_record is not None, f"User id {item_id} does not exist in DB!"
            assert db_record.name == item["title"]
        elif rtype == "project":
            db_record = db.get(Project, item_id)
            assert db_record is not None, f"Project id {item_id} does not exist in DB!"
            assert db_record.title == item["title"]
        elif rtype == "opportunity":
            db_record = db.get(Opportunity, item_id)
            assert db_record is not None, f"Opportunity id {item_id} does not exist in DB!"

    # 5. Test Personalized Recommendations Endpoint
    rec_resp = client.get("/api/v1/discovery/recommendations?limit=15", headers=headers)
    assert rec_resp.status_code == 200, rec_resp.text
    rec_results = rec_resp.json()
    assert len(rec_results) > 0

    # Verify each recommendation result also resolves to a real DB record
    for rec in rec_results:
        rtype = rec["result_type"]
        item_id = rec["id"]
        assert rec["why_recommended"]
        assert rec["is_verified"] is True

        if rtype == "community":
            assert db.get(Community, item_id) is not None
        elif rtype == "event":
            assert db.get(Event, item_id) is not None
        elif rtype == "place":
            assert db.get(Place, item_id) is not None
        elif rtype == "user":
            assert db.get(User, item_id) is not None
        elif rtype == "project":
            assert db.get(Project, item_id) is not None
        elif rtype == "opportunity":
            assert db.get(Opportunity, item_id) is not None


def test_recommendation_feedback_loop(client: TestClient, db: Session):
    timestamp = int(time.time() * 1000)

    # Setup User and recommendations
    user = User(
        name=f"Feedback Tester {timestamp}",
        email=f"feedback_{timestamp}@align.local",
        password_hash=hash_password("Pass123!"),
        is_active=True
    )
    db.add(user)
    db.flush()
    profile = Profile(
        user_id=user.id,
        bio="AI Engineer testing feedback loops",
        skills="Python, PyTorch",
        interests="Machine Learning",
        location="Pune",
    )
    db.add(profile)

    # Create target community 1 & 2
    comm1 = Community(
        name=f"Target ML Guild {timestamp}",
        description="Machine learning and deep neural networks guild.",
        category="Technology",
        tags="python, ml",
        location="Pune",
        created_by_id=user.id
    )
    comm2 = Community(
        name=f"Irrelevant Topic Group {timestamp}",
        description="Completely unrelated topic community.",
        category="Technology",
        tags="irrelevant, topic",
        location="Pune",
        created_by_id=user.id
    )
    db.add_all([comm1, comm2])
    db.commit()

    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    # 1. Submit Feedback: 'relevant' for comm1
    fb_rel = client.post(
        "/api/v1/discovery/feedback",
        headers=headers,
        json={"item_type": "community", "item_id": comm1.id, "feedback": "relevant", "notes": "Great community match"}
    )
    assert fb_rel.status_code == 201, fb_rel.text
    assert fb_rel.json()["feedback"] == "relevant"

    # 2. Submit Feedback: 'not_relevant' for comm2
    fb_not_rel = client.post(
        "/api/v1/discovery/feedback",
        headers=headers,
        json={"item_type": "community", "item_id": comm2.id, "feedback": "not_relevant", "notes": "Not interested in this"}
    )
    assert fb_not_rel.status_code == 201, fb_not_rel.text
    assert fb_not_rel.json()["feedback"] == "not_relevant"

    # 3. Submit Feedback: 'save_for_later'
    fb_save = client.post(
        "/api/v1/discovery/feedback",
        headers=headers,
        json={"item_type": "community", "item_id": comm1.id, "feedback": "save_for_later"}
    )
    assert fb_save.status_code == 201
    assert fb_save.json()["feedback"] == "save_for_later"

    # Verify it automatically created a SavedItem entry
    saved_check = db.scalar(
        select(SavedItem).where(
            SavedItem.user_id == user.id,
            SavedItem.item_type == "community",
            SavedItem.item_id == comm1.id
        )
    )
    assert saved_check is not None

    # 4. Retrieve feedbacks via GET
    fb_list = client.get("/api/v1/discovery/feedback", headers=headers)
    assert fb_list.status_code == 200
    feedbacks = fb_list.json()
    assert len(feedbacks) >= 2

    # 5. Verify the feedback loop directly affects ranking
    recs = client.get("/api/v1/discovery/recommendations?limit=20", headers=headers).json()
    # comm1 has positive feedback ('save_for_later') -> should be present and boosted
    found_comm1 = next((r for r in recs if r["result_type"] == "community" and r["id"] == comm1.id), None)
    if found_comm1:
        assert "In your saved collection" in found_comm1["reason"]

    # comm2 has 'not_relevant' -> should either be filtered out or heavily penalized in rank
    found_comm2 = next((r for r in recs if r["result_type"] == "community" and r["id"] == comm2.id), None)
    if found_comm2:
        assert found_comm2["score"] < 0.20
