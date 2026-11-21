import re
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from app.models.user import User, Profile, UserBlock
from app.models.connection import UserConnection
from app.services.embeddings import cosine_similarity, generate_embedding
from app.services.discovery import haversine_distance, tokens

STOP_WORDS = {
    "and", "or", "the", "in", "of", "to", "for", "with", "at", "by", "on",
    "a", "an", "as", "is", "it", "this", "that", "from", "skills", "skill",
    "tools", "etc", "general", "both", "all", "our"
}

def clean_tokens(val: str | None) -> set[str]:
    if not val:
        return set()
    cleaned = re.sub(r"[^\w\s,]", " ", val.lower())
    parts = {p.strip() for p in cleaned.split(",") if p.strip()}
    individual_words = {
        w for w in re.findall(r"\b[a-zA-Z]{3,}\b", cleaned)
        if w not in STOP_WORDS
    }
    return (parts - STOP_WORDS) | individual_words

def extract_clean_phrases(val: str | None) -> list[str]:
    """Returns distinct, non-empty skill/interest phrases preserving original casing."""
    if not val:
        return []
    seen = set()
    res = []
    for item in val.split(","):
        trimmed = item.strip()
        if trimmed and trimmed.lower() not in seen and trimmed.lower() not in STOP_WORDS:
            seen.add(trimmed.lower())
            res.append(trimmed)
    return res

def extract_shared_phrases(val1: str | None, val2: str | None) -> list[str]:
    """Finds exact and fuzzy shared skill/interest phrases with proper casing."""
    phrases1 = extract_clean_phrases(val1)
    phrases2 = extract_clean_phrases(val2)
    p2_map = {p.lower(): p for p in phrases2}
    
    shared = []
    for p in phrases1:
        if p.lower() in p2_map and p not in shared:
            shared.append(p)
    return shared

def compute_multi_dimensional_match(
    u1: User,
    u2: User,
    u1_emb: list[float] | None,
    u2_emb: list[float] | None,
) -> dict:
    p1 = u1.profile
    p2 = u2.profile

    # 1. Semantic Embedding Similarity (40% weight)
    sem_sim = 0.5
    if u1_emb and u2_emb:
        sem_sim = max(0.0, min(1.0, cosine_similarity(u1_emb, u2_emb)))

    # 2. Skill Synergy (20% weight)
    skills1 = clean_tokens(p1.skills if p1 else "")
    skills2 = clean_tokens(p2.skills if p2 else "")
    shared_skills = skills1 & skills2
    # Skill overlap or complementary technical skill
    skill_score = min(1.0, len(shared_skills) * 0.35 + (0.3 if skills1 and skills2 else 0.0))

    # 3. Shared Goals (15% weight)
    goals1 = clean_tokens(p1.goals if p1 else "")
    goals2 = clean_tokens(p2.goals if p2 else "")
    shared_goals = goals1 & goals2
    goals_score = min(1.0, len(shared_goals) * 0.45 + (0.2 if goals1 and goals2 else 0.0))

    # 4. Common Interests & Hobbies (15% weight)
    interests1 = clean_tokens(f"{p1.interests if p1 else ''} {p1.hobbies if p1 else ''}")
    interests2 = clean_tokens(f"{p2.interests if p2 else ''} {p2.hobbies if p2 else ''}")
    shared_interests = interests1 & interests2
    interests_score = min(1.0, len(shared_interests) * 0.3 + (0.2 if interests1 and interests2 else 0.0))

    # 5. Location Proximity (10% weight)
    loc_score = 0.5  # Neutral default for online/remote
    dist_km = None
    if p1 and p2 and p1.latitude is not None and p2.latitude is not None:
        dist_km = haversine_distance(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
        if dist_km <= 25:
            loc_score = 1.0
        elif dist_km <= 75:
            loc_score = 0.8
        elif dist_km <= 200:
            loc_score = 0.6
        else:
            loc_score = 0.3
    elif p1 and p2 and p1.location and p2.location and p1.location.strip().lower() == p2.location.strip().lower():
        loc_score = 0.95

    # Overall Weighted Score (0 to 100)
    composite = (
        (sem_sim * 0.40) +
        (skill_score * 0.20) +
        (goals_score * 0.15) +
        (interests_score * 0.15) +
        (loc_score * 0.10)
    )
    overall_percentage = int(round(composite * 100))

    # Highlight explanation
    reasons = []
    canonical_shared_skills = extract_shared_phrases(p1.skills if p1 else "", p2.skills if p2 else "")
    if not canonical_shared_skills and shared_skills:
        canonical_shared_skills = [s.title() for s in shared_skills if s not in STOP_WORDS]

    canonical_shared_goals = extract_shared_phrases(p1.goals if p1 else "", p2.goals if p2 else "")
    if not canonical_shared_goals and shared_goals:
        canonical_shared_goals = [g.title() for g in shared_goals if g not in STOP_WORDS]

    if canonical_shared_skills:
        reasons.append(f"Shared expertise in {', '.join(canonical_shared_skills[:2])}")
    if canonical_shared_goals:
        reasons.append(f"Aligned on {', '.join(canonical_shared_goals[:2])}")
    if shared_interests:
        clean_interests = [i.title() for i in shared_interests if i not in STOP_WORDS]
        if clean_interests:
            reasons.append(f"Common passion in {', '.join(clean_interests[:2])}")
    if dist_km is not None and dist_km < 30:
        reasons.append(f"Nearby ({int(dist_km)} km)")

    if not reasons:
        reasons.append(f"{overall_percentage}% semantic and professional alignment")

    return {
        "overall_percentage": overall_percentage,
        "semantic_similarity": int(round(sem_sim * 100)),
        "skill_synergy": int(round(skill_score * 100)),
        "shared_goals": int(round(goals_score * 100)),
        "common_interests": int(round(interests_score * 100)),
        "location_proximity": int(round(loc_score * 100)),
        "distance_km": round(dist_km, 1) if dist_km is not None else None,
        "shared_skills": canonical_shared_skills[:4],
        "shared_goals_list": canonical_shared_goals[:3],
        "explanation": " · ".join(reasons[:2]),
    }

def get_smart_matches_for_user(
    db: Session,
    current_user: User,
    limit: int = 15,
    min_score: int = 40,
) -> list[dict]:
    # Exclude blocked users both ways
    blocked_by_me = select(UserBlock.blocked_user_id).where(UserBlock.blocker_id == current_user.id)
    blocking_me = select(UserBlock.blocker_id).where(UserBlock.blocked_user_id == current_user.id)
    blocked_ids = set(db.scalars(blocked_by_me)).union(set(db.scalars(blocking_me)))

    stmt = (
        select(User)
        .join(Profile, User.id == Profile.user_id, isouter=True)
        .where(User.is_active == True, User.is_test == False)
        .where(User.id != current_user.id)
        .where(or_(Profile.privacy_level.is_(None), Profile.privacy_level != "private"))
    )
    if blocked_ids:
        stmt = stmt.where(User.id.not_in(blocked_ids))

    candidates = list(db.scalars(stmt))
    u1_emb = current_user.profile.embedding if current_user.profile else None

    # Pre-fetch connections
    conns = list(
        db.scalars(
            select(UserConnection).where(
                or_(UserConnection.sender_id == current_user.id, UserConnection.receiver_id == current_user.id)
            )
        )
    )
    conn_map = {}
    for c in conns:
        partner_id = c.receiver_id if c.sender_id == current_user.id else c.sender_id
        conn_map[partner_id] = (c.status, c.id, c.sender_id == current_user.id)

    results = []
    for cand in candidates:
        cand_emb = cand.profile.embedding if cand.profile else None
        breakdown = compute_multi_dimensional_match(current_user, cand, u1_emb, cand_emb)
        if breakdown["overall_percentage"] >= min_score:
            conn_info = conn_map.get(cand.id)
            results.append({
                "user_id": cand.id,
                "name": cand.name,
                "avatar_url": cand.profile.avatar_url if cand.profile else None,
                "bio": cand.profile.bio if cand.profile else "",
                "skills": cand.profile.skills if cand.profile else "",
                "interests": cand.profile.interests if cand.profile else "",
                "goals": cand.profile.goals if cand.profile else "",
                "location": cand.profile.location if cand.profile else "Global",
                "connection_status": conn_info[0] if conn_info else "none",
                "connection_id": conn_info[1] if conn_info else None,
                "is_connection_sender": conn_info[2] if conn_info else False,
                "compatibility": breakdown,
            })

    results.sort(key=lambda x: x["compatibility"]["overall_percentage"], reverse=True)
    return results[:limit]
