import math
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.post import Post, PostMedia
from app.models.user import User, Profile
from app.models.connection import UserConnection
from app.models.community import Community, CommunityMembership
from app.services.feed_ranker import (
    WEIGHTS,
    compute_feed_shapley_breakdown,
    generate_why_recommended,
    score_and_rank_post,
    rank_feed_posts,
    get_user_graph_context,
)

def test_weights_sum_to_one():
    """Verify that the 6 factor weights sum to exactly 1.00."""
    total_weight = round(sum(WEIGHTS.values()), 4)
    assert total_weight == 1.00
    assert len(WEIGHTS) == 6
    assert set(WEIGHTS.keys()) == {"semantic", "graph", "recency", "engagement", "media", "geo"}

def test_shapley_exact_additivity():
    """Verify that Shapley breakdown strictly sums to the final score for various factor combinations."""
    test_cases = [
        {"semantic": 0.85, "graph": 1.0, "recency": 0.95, "engagement": 0.60, "media": 1.0, "geo": 0.70},
        {"semantic": 0.12, "graph": 0.15, "recency": 0.22, "engagement": 0.05, "media": 0.35, "geo": 0.30},
        {"semantic": 0.50, "graph": 0.70, "recency": 0.50, "engagement": 0.50, "media": 0.65, "geo": 1.0},
        {"semantic": 0.999, "graph": 0.999, "recency": 0.999, "engagement": 0.999, "media": 0.999, "geo": 0.999},
    ]

    for factors in test_cases:
        score = sum(WEIGHTS[k] * factors[k] for k in WEIGHTS)
        score = round(score, 4)
        breakdown = compute_feed_shapley_breakdown(factors, score)

        assert round(sum(breakdown.values()), 4) == score, f"Failed for {factors}: sum={sum(breakdown.values())} vs {score}"
        for k in WEIGHTS:
            assert k in breakdown
            assert breakdown[k] >= 0.0

def test_generate_why_recommended():
    """Verify non-LLM why_recommended generates grounded strings based on top contributors."""
    factors = {"semantic": 0.9, "graph": 1.0, "recency": 0.8, "engagement": 0.2, "media": 0.5, "geo": 0.3}
    score = round(sum(WEIGHTS[k] * factors[k] for k in WEIGHTS), 4)
    breakdown = compute_feed_shapley_breakdown(factors, score)
    why = generate_why_recommended(factors, breakdown)

    assert isinstance(why, str)
    assert len(why) > 0
    # Should highlight top factors (graph or semantic)
    assert any(term in why.lower() for term in ["network", "interest", "freshly", "alignment"])

def test_ranking_logic_ordering(db: Session):
    """Verify that a high-relevance, fresh, connected post outranks a stale, disconnected post."""
    now = datetime.now(timezone.utc)

    author1 = User(
        email="rank_author1@test.com",
        password_hash="fake",
        name="Rank Author 1",
        is_test=False,
    )
    author2 = User(
        email="rank_author2@test.com",
        password_hash="fake",
        name="Rank Author 2",
        is_test=False,
    )
    viewer = User(
        email="rank_viewer@test.com",
        password_hash="fake",
        name="Rank Viewer",
        is_test=False,
    )
    db.add_all([author1, author2, viewer])
    db.commit()

    viewer.profile = Profile(
        user_id=viewer.id,
        location="Pune, Maharashtra",
        embedding=[0.1] * 384,
    )
    author1.profile = Profile(
        user_id=author1.id,
        location="Pune, Maharashtra",
        embedding=[0.1] * 384,
    )
    author2.profile = Profile(
        user_id=author2.id,
        location="Delhi",
        embedding=[-0.1] * 384,
    )

    # Viewer is connected to author 1
    conn = UserConnection(
        sender_id=viewer.id,
        receiver_id=author1.id,
        status="accepted",
    )
    db.add(conn)
    db.commit()

    # Post 1: Fresh, Pune, high semantic match, from connected friend, video
    p1 = Post(
        author_id=author1.id,
        content="Fresh Pune Tech Post with Video",
        visibility="public",
        location_area="Pune",
        created_at=now - timedelta(minutes=10),
        embedding=[0.1] * 384,
    )
    # Post 2: 7 days old, Delhi, opposite embedding, stranger, text only
    p2 = Post(
        author_id=author2.id,
        content="Old Stale Post",
        visibility="public",
        location_area="Delhi",
        created_at=now - timedelta(days=7),
        embedding=[-0.1] * 384,
    )
    db.add_all([p1, p2])
    db.commit()

    # Add video media to p1
    m1 = PostMedia(
        post_id=p1.id,
        position=0,
        media_type="video",
        original_url="/uploads/v.mp4",
        feed_url="/uploads/v.mp4",
        thumbnail_url="/uploads/v.webp",
    )
    db.add(m1)
    db.commit()

    ranked = rank_feed_posts([p2, p1], viewer, db)
    assert len(ranked) == 2
    top_post, top_score, top_breakdown, top_why = ranked[0]
    bottom_post, bottom_score, bottom_breakdown, bottom_why = ranked[1]

    assert top_post.id == p1.id
    assert bottom_post.id == p2.id
    assert top_score > bottom_score
    assert round(sum(top_breakdown.values()), 4) == top_score
    assert round(sum(bottom_breakdown.values()), 4) == bottom_score

def test_feed_endpoint_ranked_response(client: TestClient, db: Session):
    """Test that GET /api/v1/feed returns posts with score, breakdown, and why_recommended."""
    # 1. Register and login a user
    user_data = {
        "email": "feed_rank_user@example.com",
        "password": "Password123!",
        "name": "Feed Rank User",
    }
    reg_res = client.post("/api/v1/auth/register", json=user_data)
    assert reg_res.status_code == 201

    login_res = client.post("/api/v1/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create a post
    post_res = client.post(
        "/api/v1/feed",
        headers=headers,
        json={
            "content": "Exploring robotics and AI in Pune #robotics",
            "visibility": "public",
            "location_area": "Pune",
        },
    )
    assert post_res.status_code == 201

    # 3. Retrieve feed
    feed_res = client.get("/api/v1/feed", headers=headers)
    assert feed_res.status_code == 200
    posts = feed_res.json()
    assert len(posts) >= 1

    top = posts[0]
    assert "score" in top
    assert top["score"] is not None
    assert "score_breakdown" in top
    assert top["score_breakdown"] is not None
    assert "why_recommended" in top
    assert top["why_recommended"] is not None
    assert round(sum(top["score_breakdown"].values()), 4) == round(top["score"], 4)
