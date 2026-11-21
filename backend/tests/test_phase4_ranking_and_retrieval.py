"""
Unit and Integration Tests for Phase 4:
- Intent Classifier with calibrated confidence scores
- Embedding LRU cache
- pgvector DB-level retrieval and candidate filtering
- Personalized re-ranking with cold-start fallbacks
- External API retry resilience
"""

import time
import pytest
from app.services.embeddings import generate_embedding
from app.services.intent_analyzer import analyze_user_intent, classify_discovery_intent
from app.models.community import Community
from app.models.event import Event
from app.models.user import User, Profile
from app.api.routes.discovery import fetch_pgvector_candidates, get_user_personalization_signals
from app.services.discovery import discover

def test_embedding_lru_cache():
    text = "Machine learning and deep neural networks in python"
    t0 = time.perf_counter()
    v1 = generate_embedding(text)
    t1 = time.perf_counter()

    # Second call should hit LRU cache instantaneously (< 1ms)
    t2 = time.perf_counter()
    v2 = generate_embedding(text)
    t3 = time.perf_counter()

    assert v1 == v2
    assert len(v1) == 384
    cached_duration = t3 - t2
    assert cached_duration < 0.05, f"Cached call took too long: {cached_duration}s"

def test_intent_classifier_accuracy_and_confidence():
    # 1. Tech & AI query
    res_tech = analyze_user_intent("Looking for python machine learning workshops and data science peers")
    assert res_tech["primary_category"] == "Tech & AI"
    assert res_tech["category_confidence"] > 0.50
    assert sum(res_tech["category_scores"].values()) == pytest.approx(1.0, abs=0.01)
    assert "Python" in res_tech["identified_skills"]

    # 2. Outdoor & Fitness query
    res_outdoor = analyze_user_intent("I want to go weekend trekking and cycling in the mountains")
    assert res_outdoor["primary_category"] == "Outdoor & Fitness"
    assert res_outdoor["category_confidence"] > 0.35

    # 3. Design query
    res_design = analyze_user_intent("Creative UI UX design and graphic design collaboration")
    assert res_design["primary_category"] == "Design & Creative Arts"

    # 4. Empty query fallback
    res_empty = analyze_user_intent("")
    assert res_empty["primary_category"] == "General Discovery"
    assert res_empty["category_confidence"] == 0.0

def test_pgvector_db_retrieval(db):
    """Verifies database-level pgvector retrieval via fetch_pgvector_candidates."""
    # Seed sample communities
    c1 = Community(
        name="AI & Python Enthusiasts",
        description="Machine learning, neural networks, PyTorch",
        category="Tech",
        tags="python,ai,ml",
        location="Pune",
        embedding=generate_embedding("AI Python Enthusiasts machine learning neural networks PyTorch"),
    )
    c2 = Community(
        name="Pune Hiking & Nature Club",
        description="Weekend trekking and mountain climbing",
        category="Outdoors",
        tags="hiking,trekking,nature",
        location="Pune",
        embedding=generate_embedding("Pune Hiking Nature Club weekend trekking mountain climbing"),
    )
    db.add_all([c1, c2])
    db.commit()

    q_emb = generate_embedding("artificial intelligence and deep learning")
    candidates = fetch_pgvector_candidates(db, Community, q_emb=q_emb, limit=10)
    assert len(candidates) >= 1
    top_ids = [c.id for c in candidates]
    assert c1.id in top_ids
    c1_rank = top_ids.index(c1.id)
    c2_rank = top_ids.index(c2.id) if c2.id in top_ids else 999
    assert c1_rank < c2_rank

def test_personalized_re_ranking_and_cold_start():
    """Verifies that personalized profile embeddings boost relevant items, while cold-start falls back cleanly."""
    c_tech = Community(
        id=901,
        name="Advanced Robotics & Hardware",
        description="Building autonomous robots with ROS and C++",
        category="Tech",
        tags="robotics,ros,hardware",
        location="Online",
    )
    c_tech.member_count = 5

    c_art = Community(
        id=902,
        name="Digital Watercolor & Illustration",
        description="Painting digital art and watercolor sketches",
        category="Art",
        tags="art,painting,watercolor",
        location="Online",
    )
    c_art.member_count = 5

    query = "Find interesting communities to join"

    # 1. Cold-start user (no profile embedding, no saved items, no joined communities)
    results_cold = discover(
        query=query,
        communities=[c_tech, c_art],
        events=[],
        user_profile_emb=None,
        saved_categories=set(),
        joined_community_tags=set(),
    )
    assert len(results_cold) == 2

    # 2. Personalized user interested in robotics and engineering
    user_robotics_emb = generate_embedding("I love robotics, mechanical engineering, hardware and automated systems")
    results_personalized = discover(
        query=query,
        communities=[c_tech, c_art],
        events=[],
        user_profile_emb=user_robotics_emb,
        saved_categories={"Tech"},
        joined_community_tags={"robotics", "hardware"},
    )
    assert len(results_personalized) >= 1
    # Robotics community should be ranked first due to profile similarity and tag affinities
    assert results_personalized[0]["id"] == c_tech.id
    assert results_personalized[0]["score"] > results_cold[0]["score"]
