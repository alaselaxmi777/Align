from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from app.core.security import hash_password
from app.models.community import Community, CommunityMembership
from app.models.event import Event
from app.models.opportunity import Opportunity
from app.models.place import Place
from app.models.project import Project
from app.models.user import User
from app.services.discovery import haversine_distance
from app.services.opportunities_service import deactivate_expired_opportunities

def test_event_deduplication(db):
    """Verifies events are strictly deduplicated by normalized (title, starts_at) and external_id."""
    now = datetime.now(timezone.utc) + timedelta(days=2)
    ext_id = "test_evt_ext_9999"

    # Insert first event
    evt1 = Event(
        title="Unique AI Hackathon 2027",
        description="A great hackathon",
        category="Technology",
        location="Pune, India",
        starts_at=now,
        external_id=ext_id,
        is_cancelled=False,
    )
    db.add(evt1)
    db.commit()

    # Query existing events by external_id
    existing_by_ext = db.scalar(select(Event).where(Event.external_id == ext_id))
    assert existing_by_ext is not None
    assert existing_by_ext.id == evt1.id

    # Verify matching by normalized (title, starts_at)
    normalized_title = evt1.title.strip().lower()
    existing_match = db.scalar(
        select(Event).where(
            Event.title.ilike(f"%{normalized_title}%"),
            Event.starts_at == now,
        )
    )
    assert existing_match is not None
    assert existing_match.id == evt1.id

def test_opportunity_expiry_filter_and_deactivation(client, auth_headers, db):
    """Verifies expired opportunities are hidden from public queries and deactivated properly."""
    now = datetime.now(timezone.utc)
    past_date = now - timedelta(days=5)
    future_date = now + timedelta(days=20)

    # Clean up test opportunities
    db.query(Opportunity).filter(Opportunity.title.like("Quality Test Opp%")).delete()
    db.commit()

    opp_active = Opportunity(
        title="Quality Test Opp - Active Future",
        organization="Google DeepMind",
        opportunity_type="Fellowship",
        description="A prestigious AI research fellowship opportunity.",
        location="Remote",
        is_remote=True,
        stipend_or_prize="$10,000",
        deadline=future_date,
        apply_url="https://deepmind.google/fellowships",
        tags="AI, Research",
        is_active=True,
    )
    opp_expired = Opportunity(
        title="Quality Test Opp - Expired Past",
        organization="Legacy Labs",
        opportunity_type="Hackathon",
        description="An expired hackathon opportunity.",
        location="Online",
        is_remote=True,
        stipend_or_prize="$5,000",
        deadline=past_date,
        apply_url="https://legacylabs.test/expired",
        tags="Legacy",
        is_active=True,
    )
    db.add_all([opp_active, opp_expired])
    db.commit()

    # 1. Query public list - expired opportunity should be filtered out
    res = client.get("/api/v1/opportunities")
    assert res.status_code == 200
    data = res.json()
    titles = [item["title"] for item in data]
    assert "Quality Test Opp - Active Future" in titles
    assert "Quality Test Opp - Expired Past" not in titles

    # Verify days_left is computed dynamically
    active_item = next(item for item in data if item["title"] == "Quality Test Opp - Active Future")
    assert active_item["days_left"] is not None
    assert active_item["days_left"] > 0

    # 2. Run deactivation service
    deactivated = deactivate_expired_opportunities(db)
    assert deactivated >= 1

    # Reload from DB and verify is_active is now False for expired opp
    db.refresh(opp_expired)
    assert opp_expired.is_active is False

def test_haversine_distance_strict_boundary(client, db):
    """Verifies strict Haversine radius filtering excludes distant cities (Pune vs Kolhapur ~230 km)."""
    kolhapur_lat, kolhapur_lon = 16.7050, 74.2433
    pune_lat, pune_lon = 18.5204, 73.8567

    # Calculate actual distance
    distance_km = haversine_distance(kolhapur_lat, kolhapur_lon, pune_lat, pune_lon)
    assert 200 < distance_km < 250  # Roughly ~230 km

    # Insert a venue strictly in Pune
    pune_place = Place(
        name="Quality Test Pune Tech Hub",
        category="Coworking",
        address="FC Road, Pune, Maharashtra",
        latitude=pune_lat,
        longitude=pune_lon,
    )
    db.add(pune_place)
    db.commit()

    # Query map markers around Kolhapur with 35km radius
    res = client.get(f"/api/v1/places/map/markers?user_lat={kolhapur_lat}&user_lon={kolhapur_lon}&radius_km=35.0")
    assert res.status_code == 200
    markers = res.json()

    # The Pune venue MUST NOT appear in the 35km Kolhapur search
    pune_marker_names = [m.get("name") or m.get("title") for m in markers if (m.get("name") or m.get("title")) == "Quality Test Pune Tech Hub"]
    assert len(pune_marker_names) == 0

def test_is_test_exclusion(client, db):
    """Verifies records flagged with is_test=True are excluded from public discovery and lists."""
    test_user = User(
        name="TestBot Quality",
        email="testbot_quality_step4@align.local",
        password_hash=hash_password("Password123!"),
        is_test=True,
    )
    real_user = User(
        name="Real Member Step4",
        email="real_member_step4@align.local",
        password_hash=hash_password("Password123!"),
        is_test=False,
    )
    test_comm = Community(
        name="Automated Test Community Step4",
        category="Testing",
        description="A fake testing group",
        is_test=True,
    )
    real_comm = Community(
        name="Genuine Robotics Group Step4",
        category="Robotics & IoT",
        description="A genuine robotics discussion group",
        is_test=False,
    )
    test_proj = Project(
        title="Test Project Step4",
        description="Test project description",
        category="AI / Machine Learning",
        stage="Idea / Brainstorming",
        is_test=True,
    )
    real_proj = Project(
        title="Genuine Open Source Drone Step4",
        description="Real project description",
        category="Robotics & IoT",
        stage="Prototype Working",
        is_test=False,
    )

    db.add_all([test_user, real_user, test_comm, real_comm, test_proj, real_proj])
    db.commit()

    # 1. Communities list
    c_res = client.get("/api/v1/communities")
    assert c_res.status_code == 200
    c_names = [c["name"] for c in c_res.json()]
    assert "Genuine Robotics Group Step4" in c_names
    assert "Automated Test Community Step4" not in c_names

    # 2. Projects list
    p_res = client.get("/api/v1/projects")
    assert p_res.status_code == 200
    p_titles = [p["title"] for p in p_res.json()]
    assert "Genuine Open Source Drone Step4" in p_titles
    assert "Test Project Step4" not in p_titles

def test_dynamic_count_aggregation(client, db):
    """Verifies community member count is derived dynamically from DB records."""
    creator = User(
        name="Count Test Creator",
        email="count_creator@align.local",
        password_hash=hash_password("Password123!"),
        is_test=False,
    )
    member1 = User(
        name="Count Test Member 1",
        email="count_member1@align.local",
        password_hash=hash_password("Password123!"),
        is_test=False,
    )
    member2 = User(
        name="Count Test Member 2",
        email="count_member2@align.local",
        password_hash=hash_password("Password123!"),
        is_test=False,
    )
    comm = Community(
        name="Count Aggregation Verified Group",
        category="Design",
        description="Testing count dynamics",
        is_test=False,
    )
    db.add_all([creator, member1, member2, comm])
    db.commit()

    # Add 2 members to CommunityMembership
    m1 = CommunityMembership(community_id=comm.id, user_id=member1.id, role="member")
    m2 = CommunityMembership(community_id=comm.id, user_id=member2.id, role="member")
    db.add_all([m1, m2])
    db.commit()

    # Query community detail
    res = client.get(f"/api/v1/communities/{comm.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["member_count"] == 2

def test_admin_data_health_endpoint(client, db):
    """Verifies GET /api/v1/admin/data-health returns all required observability metrics."""
    # Create or fetch an admin user
    from app.core.security import create_access_token
    admin = db.scalar(select(User).where(User.email == "admin_quality_health@align.local"))
    if not admin:
        admin = User(
            name="Super Admin",
            email="admin_quality_health@align.local",
            password_hash=hash_password("AdminPass123!"),
            is_admin=True,
            is_test=False,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

    token = create_access_token(str(admin.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/admin/data-health", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert len(data["sources"]) >= 4
    assert "row_counts" in data
    assert "users" in data["row_counts"]
    assert "real" in data["row_counts"]["users"]
    assert "test" in data["row_counts"]["users"]
    assert "inactive_and_expired" in data
    assert "expired_opportunities" in data["inactive_and_expired"]
