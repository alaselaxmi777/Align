import pytest
import uuid
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.dataset import SkillsHobbiesDataset, SkillMaster, HobbyMaster
from app.models.user import User, Profile, UserPreference
from app.scripts.import_skills_hobbies import import_skills_and_hobbies

def test_skills_hobbies_dataset_counts(db: Session):
    """Verify exactly 5000 dataset records, 38 skill master types, and 40 hobby master types are in PostgreSQL."""
    total_ds = db.scalar(select(func.count(SkillsHobbiesDataset.id)))
    skill_master_count = db.scalar(select(func.count(SkillMaster.id)))
    hobby_master_count = db.scalar(select(func.count(HobbyMaster.id)))
    skills_count = db.scalar(select(func.count(SkillsHobbiesDataset.id)).where(SkillsHobbiesDataset.record_type == "Skill"))
    hobbies_count = db.scalar(select(func.count(SkillsHobbiesDataset.id)).where(SkillsHobbiesDataset.record_type == "Hobby"))

    assert total_ds == 5000, f"Expected 5000 dataset rows, got {total_ds}"
    assert skill_master_count == 38, f"Expected 38 skill types, got {skill_master_count}"
    assert hobby_master_count == 40, f"Expected 40 hobby types, got {hobby_master_count}"
    assert skills_count == 2457, f"Expected 2457 skills, got {skills_count}"
    assert hobbies_count == 2543, f"Expected 2543 hobbies, got {hobbies_count}"

def test_skills_and_hobbies_categories_api(client):
    """Test category summary endpoints."""
    # 1. Skill Categories
    res_s = client.get("/api/v1/skills/categories")
    assert res_s.status_code == 200
    s_data = res_s.json()
    assert len(s_data) >= 4
    categories = [c["category"] for c in s_data]
    assert any("Technical" in c for c in categories)
    assert any("Behavioral" in c for c in categories)
    assert any("Cognitive" in c for c in categories)

    # 2. Hobby Categories
    res_h = client.get("/api/v1/hobbies/categories")
    assert res_h.status_code == 200
    h_data = res_h.json()
    assert len(h_data) >= 5
    h_categories = [c["category"] for c in h_data]
    assert any("Creative" in c for c in h_categories)
    assert any("Physical" in c for c in h_categories)
    assert any("Intellectual" in c for c in h_categories)

def test_skills_and_hobbies_list_and_pagination(client):
    """Test master list endpoints with search and pagination."""
    # Test skills list with limit
    res1 = client.get("/api/v1/skills?limit=10&page=1")
    assert res1.status_code == 200
    items = res1.json()
    assert len(items) == 10

    # Test search q on skills
    res2 = client.get("/api/v1/skills?q=Coding")
    assert res2.status_code == 200
    coding_items = res2.json()
    assert len(coding_items) >= 1
    assert any("Coding" in x["type"] for x in coding_items)

    # Test hobbies list
    res3 = client.get("/api/v1/hobbies?limit=15&page=1")
    assert res3.status_code == 200
    h_items = res3.json()
    assert len(h_items) == 15

    # Test direct /api alias
    res_alias = client.get("/api/skills?limit=5")
    assert res_alias.status_code == 200
    assert len(res_alias.json()) == 5

def test_skills_and_hobbies_search_filters(client):
    """Test deep filtering across the 5000 granular records."""
    # Search skills by context and proficiency
    res_s = client.get("/api/v1/skills/search?q=Coding&proficiency=Expert&setting=Individual")
    assert res_s.status_code == 200
    data_s = res_s.json()
    assert len(data_s) >= 1
    for item in data_s:
        assert item["record_type"] == "Skill"
        assert item["proficiency_engagement_level"] == "Expert"
        assert item["setting"] == "Individual"
        assert 1 <= item["popularity_score"] <= 10

    # Search hobbies by motivation and frequency
    res_h = client.get("/api/v1/hobbies/search?motivation=Mindfulness&frequency=Daily")
    assert res_h.status_code == 200
    data_h = res_h.json()
    assert len(data_h) >= 1
    for item in data_h:
        assert item["record_type"] == "Hobby"
        assert item["primary_motivation"] == "Mindfulness"
        assert item["frequency"] == "Daily"

def test_dataset_stats_and_facets(client):
    """Test dataset stats and facet endpoints."""
    res_st = client.get("/api/v1/dataset/stats")
    assert res_st.status_code == 200
    st = res_st.json()
    assert st["total_records"] == 5000
    assert st["skills_count"] == 2457
    assert st["hobbies_count"] == 2543
    assert st["skill_types_count"] == 38
    assert st["hobby_types_count"] == 40
    assert len(st["categories"]) == 9

    res_fc = client.get("/api/v1/dataset/facets")
    assert res_fc.status_code == 200
    fc = res_fc.json()
    assert "contexts" in fc and len(fc["contexts"]) >= 5
    assert "proficiencies" in fc and len(fc["proficiencies"]) >= 4
    assert "frequencies" in fc and len(fc["frequencies"]) >= 4
    assert "motivations" in fc and len(fc["motivations"]) >= 5

def test_onboarding_with_skills_and_hobbies(client, db: Session):
    """Test complete user registration, onboarding with skills, hobbies, proficiency and preference persistence."""
    email = f"test_sh_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "StrongTestPassword123!"

    reg = client.post("/api/v1/auth/register", json={"name": "Alex Mercer", "email": email, "password": pwd})
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Complete onboarding with skills, hobbies, proficiency, engagement level
    onb_payload = {
        "bio": "AI researcher specializing in deep learning, autonomous systems, and chess algorithms.",
        "location": "Boston, MA",
        "privacy_level": "public",
        "interests": ["Artificial Intelligence", "Machine Learning"],
        "skills": ["Coding / Programming", "Data Analysis"],
        "skill_proficiency": "Advanced",
        "hobbies": ["Chess", "Astronomy"],
        "hobby_engagement_level": "Daily",
        "goals": "Collaborate on neuro-symbolic AI frameworks.",
        "preferred_activities": ["Hackathons", "Paper Reading Groups"],
        "preferred_community_types": ["Research & Academia"],
    }
    onb_res = client.post("/api/v1/auth/onboarding", json=onb_payload, headers=headers)
    assert onb_res.status_code == 200
    prof = onb_res.json()
    assert prof["onboarding_completed"] is True
    assert "Coding / Programming" in prof["skills"]
    assert "Chess" in prof["hobbies"]
    assert prof["skill_proficiency"] == "Advanced"
    assert prof["hobby_engagement_level"] == "Daily"

    # Verify user preferences table persistence
    prefs = list(db.scalars(select(UserPreference).where(UserPreference.user_id == user_id)))
    pref_dict = {p.preference_key: p.preference_value for p in prefs}
    assert "hobbies" in pref_dict
    assert "Chess" in pref_dict["hobbies"]
    assert pref_dict.get("skill_proficiency") == "Advanced"
    assert pref_dict.get("hobby_engagement_level") == "Daily"

    # Verify embedding exists
    db_prof = db.scalar(select(Profile).where(Profile.user_id == user_id))
    assert db_prof.embedding is not None

def test_recommendations_with_shared_skills_and_hobbies(client):
    """Verify semantic user discovery factors in shared skills and hobbies and generates clear matching explanations."""
    email1 = f"peer1_{uuid.uuid4().hex[:8]}@example.com"
    email2 = f"peer2_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "StrongTestPassword123!"

    # Peer 1
    client.post("/api/v1/auth/register", json={"name": "Alice Cyber", "email": email1, "password": pwd})
    tok1 = client.post("/api/v1/auth/login", json={"email": email1, "password": pwd}).json()["access_token"]
    client.post(
        "/api/v1/auth/onboarding",
        headers={"Authorization": f"Bearer {tok1}"},
        json={
            "bio": "Security engineer who loves guitar and hiking in the mountains.",
            "location": "Denver, CO",
            "interests": ["Cybersecurity"],
            "skills": ["Coding / Programming"],
            "skill_proficiency": "Advanced",
            "hobbies": ["Playing Guitar", "Hiking"],
            "hobby_engagement_level": "Weekly",
            "goals": "Connect with fellow outdoor programmers.",
        }
    )

    # Peer 2
    client.post("/api/v1/auth/register", json={"name": "Bob Outdoor", "email": email2, "password": pwd})
    tok2 = client.post("/api/v1/auth/login", json={"email": email2, "password": pwd}).json()["access_token"]
    client.post(
        "/api/v1/auth/onboarding",
        headers={"Authorization": f"Bearer {tok2}"},
        json={
            "bio": "Software developer passionate about guitar music and mountain trails.",
            "location": "Boulder, CO",
            "interests": ["Cybersecurity"],
            "skills": ["Coding / Programming"],
            "skill_proficiency": "Intermediate",
            "hobbies": ["Playing Guitar", "Hiking"],
            "hobby_engagement_level": "Weekly",
            "goals": "Looking for pair programming and hiking buddies.",
        }
    )

    # Peer 1 lists users
    res = client.get("/api/v1/users?limit=100", headers={"Authorization": f"Bearer {tok1}"})
    assert res.status_code == 200
    users = res.json()
    bob = next((u for u in users if u["name"] == "Bob Outdoor"), None)
    assert bob is not None
    # Peer email must be protected / hidden
    assert bob.get("email") is None
    assert bob["match_score"] is not None
    assert bob["recommendation_reason"] is not None
    # Verify explanation mentions shared skills or hobbies
    assert "Coding / Programming" in bob["recommendation_reason"] or "Playing Guitar" in bob["recommendation_reason"] or "Hiking" in bob["recommendation_reason"] or "%" in bob["recommendation_reason"]

def test_import_idempotency(db: Session):
    """Verify that rerunning the import is completely idempotent with 0 duplicates."""
    res = import_skills_and_hobbies()
    assert res["status"] == "success"
    assert res["dataset_records_imported"] == 5000
    assert res["skill_masters_imported"] == 38
    assert res["hobby_masters_imported"] == 40

    total = db.scalar(select(func.count(SkillsHobbiesDataset.id)))
    assert total == 5000
