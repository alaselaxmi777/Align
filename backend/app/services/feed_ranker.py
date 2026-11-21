import math
import logging
from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session
from app.models.post import Post, PostLike, PostComment
from app.models.user import User
from app.models.connection import UserConnection
from app.models.community import CommunityMembership
from app.services.embeddings import cosine_similarity

logger = logging.getLogger(__name__)

# 6-Factor Weights summing to exactly 1.00
WEIGHTS = {
    "semantic": 0.25,
    "graph": 0.20,
    "recency": 0.20,
    "engagement": 0.15,
    "media": 0.10,
    "geo": 0.10,
}

MAHARASHTRA_CITIES = {
    "pune", "mumbai", "kolhapur", "nagpur", "nashik",
    "aurangabad", "chhatrapati sambhajinagar", "solapur",
    "amravati", "nanded", "thane", "satara", "sangli"
}

def get_user_graph_context(db: Session, user_id: int | None) -> tuple[set[int], set[int]]:
    """Returns (1st_degree_connected_ids, shared_community_peer_ids)."""
    if not user_id:
        return set(), set()

    # 1. Accepted 1st degree connections
    c1 = set(db.scalars(
        select(UserConnection.receiver_id).where(UserConnection.sender_id == user_id, UserConnection.status == "accepted")
    ).all())
    c2 = set(db.scalars(
        select(UserConnection.sender_id).where(UserConnection.receiver_id == user_id, UserConnection.status == "accepted")
    ).all())
    connected_ids = c1 | c2

    # 2. Shared community peers
    user_communities = set(db.scalars(
        select(CommunityMembership.community_id).where(CommunityMembership.user_id == user_id)
    ).all())
    peer_ids = set()
    if user_communities:
        peer_ids = set(db.scalars(
            select(CommunityMembership.user_id).where(
                CommunityMembership.community_id.in_(user_communities),
                CommunityMembership.user_id != user_id
            )
        ).all())

    return connected_ids, peer_ids

def compute_feed_shapley_breakdown(
    factors: dict[str, float],
    final_score: float,
) -> dict[str, float]:
    """
    Computes exact Shapley attribution values for linear feed scoring factors.
    Guarantees: sum(breakdown.values()) == round(final_score, 4).
    """
    target = round(final_score, 4)
    raw = {k: WEIGHTS[k] * factors[k] for k in WEIGHTS}
    rounded = {k: round(v, 4) for k, v in raw.items()}

    diff = round(target - sum(rounded.values()), 4)
    if diff != 0:
        max_k = max(rounded, key=lambda k: rounded[k])
        rounded[max_k] = round(rounded[max_k] + diff, 4)

    return rounded

def generate_why_recommended(factors: dict[str, float], breakdown: dict[str, float]) -> str:
    """Produces explainable rationales derived directly from the highest-contributing factors."""
    factor_labels = {
        "semantic": "High interest alignment",
        "graph": "From your network or community",
        "recency": "Freshly published",
        "engagement": "Active discussion & likes",
        "media": "Rich visual media",
        "geo": "Local Maharashtra proximity",
    }
    sorted_factors = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
    top_two = [f"{factor_labels[k]} ({k}: +{v:.3f})" for k, v in sorted_factors[:2] if v > 0.02]
    if top_two:
        return " · ".join(top_two)
    return "Balanced discovery recommendation"

def score_and_rank_post(
    post: Post,
    user: User | None,
    connected_ids: set[int],
    peer_ids: set[int],
    now: datetime,
    db: Session,
) -> tuple[float, dict[str, float], str]:
    """
    Evaluates a single post across the 6-factor hybrid formula:
    S = 0.25*semantic + 0.20*graph + 0.20*recency + 0.15*engagement + 0.10*media + 0.10*geo
    """
    # 1. Recency: Half-life 48 hours (lambda = 0.0144)
    post_time = post.created_at
    if post_time.tzinfo is None:
        post_time = post_time.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (now - post_time).total_seconds() / 3600.0)
    x_rec = round(math.exp(-0.0144 * age_hours), 4)

    # 2. Semantic Relevance (Profile Embedding vs Post Embedding)
    x_sem = 0.5  # Neutral baseline
    if user and user.profile and user.profile.embedding and post.embedding:
        sim = cosine_similarity(user.profile.embedding, post.embedding)
        x_sem = round(max(0.0, min(1.0, sim)), 4)

    # 3. Graph Closeness
    if user:
        if post.author_id == user.id or post.author_id in connected_ids:
            x_graph = 1.0
        elif post.author_id in peer_ids:
            x_graph = 0.70
        else:
            x_graph = 0.15
    else:
        x_graph = 0.20

    # 4. Engagement (Likes + 2*Comments, log-scaled)
    likes_count = len(post.likes) if hasattr(post, "likes") and post.likes else (
        db.scalar(select(func.count(PostLike.id)).where(PostLike.post_id == post.id)) or 0
    )
    comments_count = len(post.comments) if hasattr(post, "comments") and post.comments else (
        db.scalar(select(func.count(PostComment.id)).where(PostComment.post_id == post.id)) or 0
    )
    eng_val = float(likes_count + (2 * comments_count))
    x_eng = round(min(1.0, math.log1p(eng_val) / math.log1p(30.0)), 4)

    # 5. Media Richness
    has_video = False
    has_carousel = False
    if post.media:
        has_video = any(m.media_type == "video" for m in post.media)
        has_carousel = len(post.media) > 1

    if has_video:
        x_media = 1.0
    elif has_carousel:
        x_media = 0.85
    elif post.image_url or (post.media and len(post.media) == 1):
        x_media = 0.65
    else:
        x_media = 0.35

    # 6. Geo Proximity
    user_loc = (user.profile.location or "").lower() if user and user.profile and user.profile.location else ""
    post_loc = (post.location_area or "").lower()

    if user_loc and post_loc and (post_loc in user_loc or user_loc in post_loc):
        x_geo = 1.0
    elif any(city in user_loc for city in MAHARASHTRA_CITIES) and any(city in post_loc for city in MAHARASHTRA_CITIES):
        x_geo = 0.70
    elif any(city in post_loc for city in MAHARASHTRA_CITIES):
        x_geo = 0.50
    else:
        x_geo = 0.30

    factors = {
        "semantic": x_sem,
        "graph": x_graph,
        "recency": x_rec,
        "engagement": x_eng,
        "media": x_media,
        "geo": x_geo,
    }

    final_score = sum(WEIGHTS[k] * factors[k] for k in WEIGHTS)
    final_score = round(final_score, 4)

    breakdown = compute_feed_shapley_breakdown(factors, final_score)
    why = generate_why_recommended(factors, breakdown)

    return final_score, breakdown, why

def rank_feed_posts(
    posts: list[Post],
    user: User | None,
    db: Session,
) -> list[tuple[Post, float, dict[str, float], str]]:
    """
    Ranks a list of candidate posts using the 6-factor hybrid formula.
    Pinned posts by the author are preserved at the top if viewing an author feed.
    """
    if not posts:
        return []

    now = datetime.now(timezone.utc)
    connected_ids, peer_ids = get_user_graph_context(db, user.id if user else None)

    scored = []
    for p in posts:
        score, breakdown, why = score_and_rank_post(p, user, connected_ids, peer_ids, now, db)
        scored.append((p, score, breakdown, why))

    # Pinned posts first (if any), then descending by hybrid score, tie-break by recency
    scored.sort(
        key=lambda item: (
            1 if item[0].is_pinned else 0,
            item[1],
            item[0].created_at.timestamp() if item[0].created_at else 0.0,
        ),
        reverse=True,
    )

    return scored
