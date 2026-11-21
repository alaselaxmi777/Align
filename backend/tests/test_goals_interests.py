import pytest
import uuid
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.dataset import GoalsInterestsDataset, GoalMaster, InterestMaster
from app.models.user import User, Profile, UserPreference
from app.scripts.import_goals_interests import import_goals_and_interests


def test_goals_interests_dataset_counts(db: Session):
    """Verify exactly 10000 dataset records, 64 goal master types, and 72 interest master types."""
    total_ds = db.scalar(select(func.count(GoalsInterestsDataset.id)))
    goal_master_count = db.scalar(select(func.count(GoalMaster.id)))
    interest_master_count = db.scalar(select(func.count(InterestMaster.id)))
    goals_count = db.scalar(
        select(func.count(GoalsInterestsDataset.id)).where(GoalsInterestsDataset.record_type == "Goal")
    )
    interests_count = db.scalar(
        select(func.count(GoalsInterestsDataset.id)).where(GoalsInterestsDataset.record_type == "Interest")
    )

    assert total_ds == 10000, f"Expected 10000 dataset rows, got {total_ds}"
    assert goal_master_count == 64, f"Expected 64 goal types, got {goal_master_count}"
    assert interest_master_count == 72, f"Expected 72 interest types, got {interest_master_count}"
    assert goals_count + interests_count == 10000, (
        f"Goal+Interest split {goals_count}+{interests_count} must equal 10000"
    )


def test_goals_and_interests_categories_api(client):
    """Test category summary endpoints for goals and interests."""
    # Goal Categories
    res_g = client.get("/api/v1/goals/categories")
    assert res_g.status_code == 200
    g_data = res_g.json()
    assert len(g_data) >= 3
    g_categories = [c["category"] for c in g_data]
    assert any("Career" in c or "Health" in c or "Personal" in c for c in g_categories)

    # Interest Categories
    res_i = client.get("/api/v1/interests/categories")
    assert res_i.status_code == 200
    i_data = res_i.json()
    assert len(i_data) >= 3
    i_categories = [c["category"] for c in i_data]
    assert any("Arts" in c or "Technology" in c or "Science" in c or "Sports" in c for c in i_categories)


def test_goals_and_interests_list_and_pagination(client):
    """Test master list endpoints with search and pagination."""
    # Goals list with limit
    res1 = client.get("/api/v1/goals?limit=10&page=1")
    assert res1.status_code == 200
    items = res1.json()
    assert len(items) == 10

    # Interests list with limit
    res2 = client.get("/api/v1/interests?limit=15&page=1")
    assert res2.status_code == 200
    i_items = res2.json()
    assert len(i_items) == 15

    # Test /api alias
    res_alias = client.get("/api/goals?limit=5")
    assert res_alias.status_code == 200
    assert len(res_alias.json()) == 5

    # Test interests /api alias
    res_alias_i = client.get("/api/interests?limit=5")
    assert res_alias_i.status_code == 200
    assert len(res_alias_i.json()) == 5


def test_goals_and_interests_search_filters(client):
    """Test deep filtering across the 10000 granular records."""
    # Search goals by category
    res_g = client.get("/api/v1/goals/search?category=Career")
    assert res_g.status_code == 200
    data_g = res_g.json()
    assert len(data_g) >= 1
    for item in data_g:
        assert item["record_type"] == "Goal"
        assert "Career" in item["category"]
        assert 1 <= item["popularity_score"] <= 10

    # Search interests with keyword
    res_i = client.get("/api/v1/interests/search?q=Painting")
    assert res_i.status_code == 200
    data_i = res_i.json()
    assert len(data_i) >= 1
    for item in data_i:
        assert item["record_type"] == "Interest"


def test_gi_stats_and_facets(client):
    """Test goals/interests stats and facet endpoints."""
    res_st = client.get("/api/v1/goals-interests/stats")
    assert res_st.status_code == 200
    st = res_st.json()
    assert st["total_records"] == 10000
    assert st["goals_count"] + st["interests_count"] == 10000
    assert st["goal_types_count"] == 64
    assert st["interest_types_count"] == 72
    assert len(st["categories"]) >= 5

    res_fc = client.get("/api/v1/goals-interests/facets")
    assert res_fc.status_code == 200
    fc = res_fc.json()
    assert "life_contexts" in fc
    assert "timelines" in fc
    assert "priorities" in fc


def test_onboarding_with_goals_and_interests(client, db: Session):
    """Test complete user registration, onboarding with goals and interests and persistence."""
    email = f"test_gi_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "StrongTestPassword123!"

    reg = client.post("/api/v1/auth/register", json={"name": "Test GI User", "email": email, "password": pwd})
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    onb_payload = {
        "bio": "A lifelong learner interested in technology, arts, and achieving career goals.",
        "location": "San Francisco, CA",
        "privacy_level": "public",
        "interests": ["Technology", "Painting"],
        "skills": ["Data Analysis"],
        "goals": "Get a promotion and learn guitar in the next year.",
        "preferred_activities": ["Online Courses", "Meetups"],
        "preferred_community_types": ["Learning & Development"],
    }
    onb_res = client.post("/api/v1/auth/onboarding", json=onb_payload, headers=headers)
    assert onb_res.status_code == 200
    prof = onb_res.json()
    assert prof["onboarding_completed"] is True
    assert "Technology" in prof["interests"] or "Painting" in prof["interests"]
    assert prof["goals"] is not None

    # Verify embedding was generated
    db_prof = db.scalar(select(Profile).where(Profile.user_id == user_id))
    assert db_prof.embedding is not None


def test_import_idempotency_goals_interests(db: Session):
    """Verify that rerunning the import is idempotent with 0 duplicates."""
    res = import_goals_and_interests()
    assert res["status"] == "success"
    assert res["dataset_records_imported"] == 10000
    assert res["goal_masters_imported"] == 64
    assert res["interest_masters_imported"] == 72

    total = db.scalar(select(func.count(GoalsInterestsDataset.id)))
    assert total == 10000


def test_gi_min_popularity_filter(client):
    """Verify min_popularity filter works on search endpoints."""
    res_g = client.get("/api/v1/goals/search?min_popularity=8")
    assert res_g.status_code == 200
    for item in res_g.json():
        assert item["popularity_score"] >= 8

    res_i = client.get("/api/v1/interests/search?min_popularity=9")
    assert res_i.status_code == 200
    for item in res_i.json():
        assert item["popularity_score"] >= 9
