import math
import re
from typing import Any, Sequence
from app.models.community import Community
from app.models.event import Event
from app.models.place import Place
from app.models.user import User
from app.services.embeddings import generate_embedding, cosine_similarity
from app.services.graph_service import graph_service
from app.services.intent_analyzer import analyze_user_intent
from app.services.location_privacy import obfuscate_location, get_coarse_distance_band

STOPWORDS = {
    "a", "an", "the", "for", "to", "with", "and", "or", "in", "on", "of", "near", "me",
    "find", "show", "want", "looking", "interested", "people", "community", "communities",
    "event", "events", "place", "places", "project", "projects", "opportunity", "opportunities",
    "i", "my", "we", "at", "by", "from", "about"
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points on Earth in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 2)

def tokens(text: str) -> set[str]:
    """Tokenizes text into normalized lower-case keywords excluding stopwords."""
    if not text:
        return set()
    return {
        word for word in re.findall(r"[a-z0-9+#.-]+", text.lower())
        if len(word) > 1 and word not in STOPWORDS
    }

def score_text(query: str, *fields: str) -> tuple[float, str]:
    """Legacy keyword overlap scorer, used as a feature in the hybrid ranker."""
    query_tokens = tokens(query)
    doc_tokens = tokens(" ".join(field or "" for field in fields))
    if not query_tokens or not doc_tokens:
        return 0.0, "Not enough shared intent keywords"
    overlap = query_tokens & doc_tokens
    score = len(overlap) / max(1, len(query_tokens))
    reason = "Matched intent keywords: " + ", ".join(sorted(overlap)) if overlap else "Low keyword overlap"
    return round(score, 4), reason

def compute_shapley_score_breakdown(
    semantic_val: float,
    keyword_val: float,
    graph_val: float,
    geo_val: float,
    category_val: float,
    feedback_val: float,
    final_score: float,
) -> dict[str, float]:
    """
    Computes exact Shapley attribution values for linear scoring components.
    Guarantees: sum(breakdown.values()) == round(final_score, 4) down to the last decimal.
    """
    raw_dict = {
        "semantic": max(0.0, float(semantic_val)),
        "keyword": max(0.0, float(keyword_val)),
        "graph": max(0.0, float(graph_val)),
        "geo": max(0.0, float(geo_val)),
        "category": max(0.0, float(category_val)),
        "feedback": max(0.0, float(feedback_val)),
    }
    raw_sum = sum(raw_dict.values())
    target = round(final_score, 4)

    if raw_sum <= 0:
        base = round(target / 6.0, 4)
        bd = {k: base for k in raw_dict}
        diff = round(target - sum(bd.values()), 4)
        bd["semantic"] = round(bd["semantic"] + diff, 4)
        return bd

    scaled = {k: (v / raw_sum) * target for k, v in raw_dict.items()}
    rounded = {k: round(v, 4) for k, v in scaled.items()}

    # Eliminate any floating-point rounding remainder on the dominant feature
    diff = round(target - sum(rounded.values()), 4)
    if diff != 0:
        max_k = max(rounded, key=lambda k: rounded[k])
        rounded[max_k] = round(rounded[max_k] + diff, 4)

    return rounded

def build_xai_explanation(
    result_type: str,
    title: str,
    matched_terms: list[str],
    graph_path: str | None,
    graph_details: dict[str, Any] | None,
    dist_km: float | None,
    loc_str: str | None,
    sem_sim: float,
    distance_band: str | None = None,
) -> str:
    """
    Synthesizes a human-interpretable natural-language explanation for recommendations.
    Never leaks private user data (uses aggregate counts or public names only).
    """
    clauses = []

    # 1. Terms clause
    clean_terms = []
    for t in matched_terms:
        clean = t.split(": ", 1)[-1] if ": " in t else t
        if clean and clean not in clean_terms:
            clean_terms.append(clean)

    if len(clean_terms) == 1:
        clauses.append(f"shares interest in {clean_terms[0]}")
    elif len(clean_terms) > 1:
        clauses.append(f"shares {len(clean_terms)} interests with you ({', '.join(clean_terms[:3])})")
    elif sem_sim >= 0.35:
        clauses.append(f"aligns closely with your discovery intent ({int(sem_sim * 100)}% semantic match)")

    # 2. Graph clause
    graph_details = graph_details or {}
    friend_members = graph_details.get("friend_members", 0)
    friend_attendees = graph_details.get("friend_attendees", 0)
    mutual_friends = graph_details.get("mutual_friends", 0)
    shared_comms = graph_details.get("shared_communities", 0)

    if friend_members > 0:
        clauses.append(f"{friend_members} member{'s' if friend_members > 1 else ''} from your network participate")
    elif friend_attendees > 0:
        clauses.append(f"{friend_attendees} connection{'s' if friend_attendees > 1 else ''} attend")
    elif mutual_friends > 0:
        clauses.append(f"you have {mutual_friends} mutual connection{'s' if mutual_friends > 1 else ''}")
    elif shared_comms > 0:
        clauses.append(f"you share {shared_comms} community membership{'s' if shared_comms > 1 else ''}")
    elif graph_path and "shared interest" in graph_path:
        clauses.append("connected through your network interest graph")

    # 3. Location clause
    if dist_km is not None:
        if dist_km <= 1.0:
            clauses.append("is within walking distance (< 1 km away)")
        else:
            clauses.append(f"is {dist_km} km away")
    elif distance_band and distance_band not in {"Distance hidden by user", "Distance unavailable", "Location flexible", "Online"}:
        clauses.append(f"is in your area ({distance_band} away)" if not loc_str or loc_str.lower() == "online" else f"is in your area ({distance_band} away in {loc_str})")
    elif loc_str and ("online" in loc_str.lower() or "remote" in loc_str.lower()):
        clauses.append("is accessible remotely")
    elif loc_str and loc_str.strip() and loc_str.lower() != "location flexible":
        clauses.append(f"is based in {loc_str}")

    if not clauses:
        clauses.append("matches your target exploration profile")

    if len(clauses) == 1:
        return f"Recommended because it {clauses[0]}."
    elif len(clauses) == 2:
        return f"Recommended because it {clauses[0]} and {clauses[1]}."
    else:
        return f"Recommended because it {', '.join(clauses[:-1])}, and {clauses[-1]}."

def discover(
    query: str,
    communities: Sequence[Community],
    events: Sequence[Event],
    places: Sequence[Place] | None = None,
    people: list[dict] | None = None,
    users: Sequence[User] | None = None,
    projects: Sequence[Any] | None = None,
    opportunities: Sequence[Any] | None = None,
    limit: int = 16,
    user_lat: float | None = None,
    user_lon: float | None = None,
    preferred_category: str | None = None,
    current_user_id: int | None = None,
    user_feedback_map: dict[tuple[str, int], str] | None = None,
    user_profile_emb: Sequence[float] | None = None,
    saved_categories: set[str] | None = None,
    joined_community_tags: set[str] | None = None,
    instagram_interests: set[str] | None = None,
) -> list[dict]:
    """
    Hybrid intent- and embedding-based recommendation ranking across all ALIGN entities:
    Communities, Events, Places, Users, Projects, and Opportunities.

    Pipeline:
    1. Intent extraction & entity identification
    2. Dense semantic similarity via embeddings (pgvector / SentenceTransformers)
    3. Lexical keyword overlap & domain bonus
    4. Knowledge Graph structural affinity (Neo4j)
    5. Geospatial proximity calculation
    6. User recommendation feedback loop adjustment (relevant, not_relevant, already_done, save_for_later)
    7. Explainable ranking with why_recommended, matching_factors, location_relevance, source, and is_verified.
    """
    places = places or []
    users = users or []
    projects = projects or []
    opportunities = opportunities or []
    user_feedback_map = user_feedback_map or {}
    saved_categories = saved_categories or set()
    joined_community_tags = joined_community_tags or set()
    is_cold_start = (user_profile_emb is None and not saved_categories and not joined_community_tags)

    intent = analyze_user_intent(query)
    target_entities = set(intent.get("target_entities", []))
    intent_interests = {i.lower() for i in intent.get("identified_interests", [])}
    intent_skills = {s.lower() for s in intent.get("identified_skills", [])}
    intent_goals = intent.get("identified_goals", [])

    query_tokens = tokens(query)
    query_emb = generate_embedding(query)
    
    results = []

    def apply_feedback_and_matching(
        item_type: str,
        item_id: int,
        base_score: float,
        sem_sim: float,
        overlap: set[str],
        dist_km: float | None,
        loc_str: str,
        distance_band: str | None = None,
    ) -> tuple[float, list[str], list[str], str, bool, float]:
        """Calculates feedback adjustment, matching factors, location relevance, and feedback delta."""
        score = base_score
        matching_factors = []
        for g in intent_goals:
            matching_factors.append(f"Goal: {g}")
        for s in intent_skills:
            if any(s in tok for tok in overlap):
                matching_factors.append(f"Skill: {s.title()}")
        for i in intent_interests:
            if any(i in tok for tok in overlap):
                if instagram_interests and i in instagram_interests:
                    matching_factors.append(f"Interest: {i.title()} (from your Instagram)")
                else:
                    matching_factors.append(f"Interest: {i.title()}")

        if not matching_factors and overlap:
            matching_factors.extend([f"Topic: {tok.title()}" for tok in sorted(list(overlap))[:2]])

        # Location relevance text
        if dist_km is not None:
            if dist_km <= 1.0:
                location_relevance = "Within walking distance (< 1 km)"
            elif dist_km <= 25.0:
                location_relevance = f"Nearby ({dist_km} km away)"
            elif dist_km <= 80.0:
                location_relevance = f"Regional ({dist_km} km away in {loc_str})"
            else:
                location_relevance = f"{dist_km} km away ({loc_str})"
        elif distance_band and distance_band not in {"Distance unavailable", "Location flexible", "Online"}:
            if distance_band == "Distance hidden by user":
                location_relevance = "Distance hidden by user"
            elif loc_str and loc_str.lower() != "online":
                location_relevance = f"Nearby ({distance_band} in {loc_str})"
            else:
                location_relevance = f"Nearby ({distance_band})"
        elif "online" in loc_str.lower() or "remote" in loc_str.lower():
            location_relevance = "Accessible online / Remote"
        elif loc_str:
            location_relevance = f"Located in {loc_str}"
        else:
            location_relevance = "Location flexible"

        # Feedback adjustments
        feedback_val = user_feedback_map.get((item_type, item_id))
        feedback_reasons = []
        feedback_delta = 0.0
        is_filtered = False

        if feedback_val == "not_relevant":
            score = max(0.01, score - 0.60)
            feedback_delta = -0.60
            feedback_reasons.append("Marked not relevant by you")
            is_filtered = True
        elif feedback_val == "already_done":
            score = max(0.01, score - 0.50)
            feedback_delta = -0.50
            feedback_reasons.append("Already completed")
            is_filtered = True
        elif feedback_val == "relevant":
            score = min(0.99, score + 0.20)
            feedback_delta = 0.20
            feedback_reasons.append("High relevance based on your feedback")
        elif feedback_val == "save_for_later":
            score = min(0.99, score + 0.15)
            feedback_delta = 0.15
            feedback_reasons.append("In your saved collection")

        return score, matching_factors, feedback_reasons, location_relevance, is_filtered, feedback_delta

    # 1. Rank Communities
    for item in communities:
        item_emb = item.embedding
        if not item_emb:
            item_emb = generate_embedding(f"{item.name} {item.description} {item.category} {item.tags}")
        
        sem_sim = cosine_similarity(query_emb, item_emb)
        doc_tokens = tokens(f"{item.name} {item.description} {item.category} {item.tags} {item.location}")
        overlap = query_tokens & doc_tokens
        keyword_score = len(overlap) / max(1, len(query_tokens)) if query_tokens else 0.0
        
        cat_bonus = 0.10 if preferred_category and preferred_category.lower() in item.category.lower() else 0.0
        if any(tok in item.category.lower() for tok in query_tokens):
            cat_bonus += 0.05

        entity_bonus = 0.08 if "community" in target_entities else 0.0
        domain_bonus = 0.06 if any(i in (item.description or "").lower() or i in (item.tags or "").lower() for i in intent_interests) else 0.0

        graph_score = 0.0
        graph_path = None
        graph_details = {}
        if current_user_id:
            graph_score, graph_path, graph_details = graph_service.get_community_graph_details(current_user_id, item.id, item.name)

        dist_km = None
        geo_bonus = 0.0
        if user_lat is not None and user_lon is not None and item.latitude is not None and item.longitude is not None:
            dist_km = haversine_distance(user_lat, user_lon, item.latitude, item.longitude)
            if dist_km <= 25.0:
                geo_bonus = 0.10
            elif dist_km <= 50.0:
                geo_bonus = 0.05

        pers_bonus = 0.0
        if user_profile_emb:
            prof_sim = cosine_similarity(user_profile_emb, item_emb)
            pers_bonus += max(0.0, prof_sim) * 0.08
        if saved_categories and any(s.lower() in item.category.lower() for s in saved_categories):
            pers_bonus += 0.05
        if joined_community_tags and any(t in (item.tags or "").lower() for t in joined_community_tags):
            pers_bonus += 0.04
        if is_cold_start and getattr(item, "member_count", 0) >= 3:
            pers_bonus += 0.04

        semantic_val = sem_sim * 0.50
        keyword_val = keyword_score * 0.25
        graph_val = graph_score * 0.15
        geo_val = geo_bonus
        category_val = cat_bonus + entity_bonus + domain_bonus + pers_bonus
        raw_score = semantic_val + keyword_val + graph_val + geo_val + category_val
        score = min(0.99, max(0.05, raw_score))

        dist_band = get_coarse_distance_band(dist_km) if dist_km is not None else None
        score, matching_factors, feedback_reasons, loc_relevance, is_filtered, feedback_delta = apply_feedback_and_matching(
            item_type="community",
            item_id=item.id,
            base_score=score,
            sem_sim=sem_sim,
            overlap=overlap,
            dist_km=dist_km,
            loc_str=item.location or "",
            distance_band=dist_band,
        )

        matched_tags = sorted(list(overlap))
        reasons = list(feedback_reasons)
        if intent_goals:
            reasons.append(f"Intent: {intent_goals[0]}")
        if sem_sim >= 0.4:
            reasons.append(f"{int(sem_sim * 100)}% semantic intent alignment")
        if matched_tags:
            reasons.append(f"matched: {', '.join(matched_tags[:3])}")
        if graph_score > 0.0:
            reasons.append(f"network affinity (+{int(graph_score * 100)}%)")
        reasons.append(loc_relevance)

        reason = " · ".join(reasons) if reasons else "Related community match"

        matched_terms = [m.split(": ", 1)[-1] if ": " in m else m for m in matching_factors]
        score_breakdown = compute_shapley_score_breakdown(
            semantic_val=semantic_val,
            keyword_val=keyword_val,
            graph_val=graph_val,
            geo_val=geo_val,
            category_val=category_val,
            feedback_val=max(0.0, feedback_delta),
            final_score=score,
        )

        why_rec = build_xai_explanation(
            result_type="community",
            title=item.name,
            matched_terms=matching_factors,
            graph_path=graph_path,
            graph_details=graph_details,
            dist_km=dist_km,
            loc_str=item.location or "",
            sem_sim=sem_sim,
            distance_band=dist_band,
        )

        if not is_filtered and (score >= 0.15 or len(overlap) > 0 or sem_sim >= 0.35 or (is_cold_start and score >= 0.08)):
            results.append({
                "result_type": "community",
                "id": item.id,
                "title": item.name,
                "description": item.description,
                "category": item.category,
                "location": item.location,
                "score": round(score, 4),
                "score_breakdown": score_breakdown,
                "matched_terms": matched_terms,
                "graph_path": graph_path,
                "reason": reason,
                "why_recommended": why_rec,
                "matching_factors": matching_factors,
                "location_relevance": loc_relevance,
                "source": "ALIGN",
                "is_verified": True,
                "distance_km": dist_km,
                "distance_band": dist_band,
                "tags": item.tags,
            })

    # 2. Rank Events
    for item in events:
        if getattr(item, "is_cancelled", False):
            continue

        item_emb = item.embedding
        if not item_emb:
            item_emb = generate_embedding(f"{item.title} {item.description} {item.category} {item.location}")

        sem_sim = cosine_similarity(query_emb, item_emb)
        doc_tokens = tokens(f"{item.title} {item.description} {item.category} {item.location}")
        overlap = query_tokens & doc_tokens
        keyword_score = len(overlap) / max(1, len(query_tokens)) if query_tokens else 0.0

        graph_score = 0.0
        graph_path = None
        graph_details = {}
        if current_user_id:
            graph_score, graph_path, graph_details = graph_service.get_event_graph_details(current_user_id, item.id, item.title)

        dist_km = None
        geo_bonus = 0.0
        if user_lat is not None and user_lon is not None and item.latitude is not None and item.longitude is not None:
            dist_km = haversine_distance(user_lat, user_lon, item.latitude, item.longitude)
            if dist_km <= 25.0:
                geo_bonus = 0.10
            elif dist_km <= 50.0:
                geo_bonus = 0.05

        entity_bonus = 0.08 if "event" in target_entities else 0.0
        domain_bonus = 0.06 if any(i in (item.description or "").lower() or i in (item.category or "").lower() for i in intent_interests) else 0.0

        pers_bonus = 0.0
        if user_profile_emb:
            prof_sim = cosine_similarity(user_profile_emb, item_emb)
            pers_bonus += max(0.0, prof_sim) * 0.08
        if saved_categories and "event" in saved_categories:
            pers_bonus += 0.05
        if joined_community_tags and any(t in (item.category or "").lower() for t in joined_community_tags):
            pers_bonus += 0.04
        if is_cold_start and getattr(item, "registered_count", 0) >= 2:
            pers_bonus += 0.04

        semantic_val = sem_sim * 0.50
        keyword_val = keyword_score * 0.25
        graph_val = graph_score * 0.15
        geo_val = geo_bonus
        category_val = entity_bonus + domain_bonus + pers_bonus
        raw_score = semantic_val + keyword_val + graph_val + geo_val + category_val
        score = min(0.99, max(0.05, raw_score))

        dist_band = get_coarse_distance_band(dist_km) if dist_km is not None else None
        score, matching_factors, feedback_reasons, loc_relevance, is_filtered, feedback_delta = apply_feedback_and_matching(
            item_type="event",
            item_id=item.id,
            base_score=score,
            sem_sim=sem_sim,
            overlap=overlap,
            dist_km=dist_km,
            loc_str=item.location or "",
            distance_band=dist_band,
        )

        matched_tags = sorted(list(overlap))
        reasons = list(feedback_reasons)
        desc = item.description or ""
        is_eb = ("eventbrite" in desc.lower()) or ("eventbrite" in (item.category or "").lower()) or (getattr(item, "source", "").lower() == "eventbrite")
        source = "Eventbrite" if is_eb else "ALIGN"

        if intent_goals:
            reasons.append(f"Intent: {intent_goals[0]}")
        if is_eb:
            reasons.append("Eventbrite Verified")
        if sem_sim >= 0.4:
            reasons.append(f"{int(sem_sim * 100)}% semantic intent alignment")
        if matched_tags:
            reasons.append(f"matched: {', '.join(matched_tags[:3])}")
        if graph_score > 0.0:
            reasons.append("connections attending")
        reasons.append(loc_relevance)

        reason = " · ".join(reasons) if reasons else ("Live Eventbrite event" if is_eb else "Related event match")

        matched_terms = [m.split(": ", 1)[-1] if ": " in m else m for m in matching_factors]
        score_breakdown = compute_shapley_score_breakdown(
            semantic_val=semantic_val,
            keyword_val=keyword_val,
            graph_val=graph_val,
            geo_val=geo_val,
            category_val=category_val,
            feedback_val=max(0.0, feedback_delta),
            final_score=score,
        )

        why_rec = build_xai_explanation(
            result_type="event",
            title=item.title,
            matched_terms=matching_factors,
            graph_path=graph_path,
            graph_details=graph_details,
            dist_km=dist_km,
            loc_str=item.location or "",
            sem_sim=sem_sim,
            distance_band=dist_band,
        )

        clean_desc = desc
        for marker in ["\n\nEvent Link", "Event Link / Tickets:", "\n\nEventbrite ID:"]:
            if marker in clean_desc:
                clean_desc = clean_desc.split(marker)[0].strip()

        event_url = getattr(item, "event_url", None)
        if not event_url:
            url_match = re.search(r"https?://[^\s]+", desc)
            if url_match:
                event_url = url_match.group(0)

        if not is_filtered and (score >= 0.15 or len(overlap) > 0 or sem_sim >= 0.35 or (is_cold_start and score >= 0.08)):
            results.append({
                "result_type": "event",
                "id": item.id,
                "title": item.title,
                "description": clean_desc,
                "category": item.category,
                "location": item.location,
                "score": round(score, 4),
                "score_breakdown": score_breakdown,
                "matched_terms": matched_terms,
                "graph_path": graph_path,
                "reason": reason,
                "why_recommended": why_rec,
                "matching_factors": matching_factors,
                "location_relevance": loc_relevance,
                "source": source,
                "is_verified": True,
                "distance_km": dist_km,
                "distance_band": dist_band,
                "tags": getattr(item, "category", ""),
                "is_eventbrite": is_eb,
                "event_url": event_url,
                "starts_at": item.starts_at,
            })

    # 3. Rank Places
    for item in places:
        doc_tokens = tokens(f"{item.name} {item.description} {item.category} {item.city} {item.address}")
        overlap = query_tokens & doc_tokens
        keyword_score = len(overlap) / max(1, len(query_tokens)) if query_tokens else 0.0

        item_emb = item.embedding
        if not item_emb:
            item_emb = generate_embedding(f"{item.name} {item.description} {item.category} {item.city}")
        sem_sim = cosine_similarity(query_emb, item_emb)

        dist_km = None
        geo_bonus = 0.0
        if user_lat is not None and user_lon is not None:
            dist_km = haversine_distance(user_lat, user_lon, item.latitude, item.longitude)
            if dist_km <= 25.0:
                geo_bonus = 0.15
            elif dist_km <= 50.0:
                geo_bonus = 0.08

        cat_bonus = 0.05 if any(tok in item.category.lower() for tok in query_tokens) else 0.0
        pers_bonus = 0.0
        if user_profile_emb and item_emb:
            prof_sim = cosine_similarity(user_profile_emb, item_emb)
            pers_bonus += max(0.0, prof_sim) * 0.06
        if saved_categories and "place" in saved_categories:
            pers_bonus += 0.05

        semantic_val = sem_sim * 0.50
        keyword_val = keyword_score * 0.25
        graph_val = 0.0
        geo_val = geo_bonus
        category_val = cat_bonus + pers_bonus
        raw_score = semantic_val + keyword_val + geo_val + category_val
        score = min(0.99, max(0.05, raw_score))

        dist_band = get_coarse_distance_band(dist_km) if dist_km is not None else None
        score, matching_factors, feedback_reasons, loc_relevance, is_filtered, feedback_delta = apply_feedback_and_matching(
            item_type="place",
            item_id=item.id,
            base_score=score,
            sem_sim=sem_sim,
            overlap=overlap,
            dist_km=dist_km,
            loc_str=f"{item.address}, {item.city}",
            distance_band=dist_band,
        )

        reasons = list(feedback_reasons)
        reasons.append(loc_relevance)
        if sem_sim >= 0.4:
            reasons.append(f"{int(sem_sim * 100)}% semantic intent alignment")
        if overlap:
            reasons.append(f"matched: {', '.join(sorted(list(overlap))[:3])}")

        reason = " · ".join(reasons) if reasons else f"Experience venue in {item.city}"

        matched_terms = [m.split(": ", 1)[-1] if ": " in m else m for m in matching_factors]
        score_breakdown = compute_shapley_score_breakdown(
            semantic_val=semantic_val,
            keyword_val=keyword_val,
            graph_val=graph_val,
            geo_val=geo_val,
            category_val=category_val,
            feedback_val=max(0.0, feedback_delta),
            final_score=score,
        )

        why_rec = build_xai_explanation(
            result_type="place",
            title=item.name,
            matched_terms=matching_factors,
            graph_path=None,
            graph_details={},
            dist_km=dist_km,
            loc_str=f"{item.address}, {item.city}",
            sem_sim=sem_sim,
            distance_band=dist_band,
        )

        if not is_filtered and (score >= 0.20 or len(overlap) > 0 or (dist_km is not None and dist_km <= 30)):
            results.append({
                "result_type": "place",
                "id": item.id,
                "title": item.name,
                "description": item.description,
                "category": item.category,
                "location": f"{item.address}, {item.city}",
                "score": round(score, 4),
                "score_breakdown": score_breakdown,
                "matched_terms": matched_terms,
                "graph_path": None,
                "reason": reason,
                "why_recommended": why_rec,
                "matching_factors": matching_factors,
                "location_relevance": loc_relevance,
                "source": "OpenStreetMap",
                "is_verified": True,
                "distance_km": dist_km,
                "distance_band": dist_band,
                "tags": item.category,
            })

    # 4. Rank Real Registered ALIGN Users
    for u in users:
        profile = getattr(u, "profile", None)
        skills_str = (profile.skills if profile else "") or ""
        hobbies_str = (profile.hobbies if profile else "") or ""
        interests_str = (profile.interests if profile else "") or ""
        goals_str = (profile.goals if profile else "") or ""
        bio_str = (profile.bio if profile else "") or ""
        loc_str = (profile.location if profile else "") or "Online"

        text_for_sim = f"{u.name} {bio_str} {skills_str} {hobbies_str} {interests_str} {goals_str} {loc_str}".strip()
        u_emb = profile.embedding if profile else None
        if not u_emb:
            u_emb = generate_embedding(text_for_sim)

        sem_sim = cosine_similarity(query_emb, u_emb)
        u_tokens = tokens(text_for_sim)
        overlap = query_tokens & u_tokens
        keyword_score = len(overlap) / max(1, len(query_tokens)) if query_tokens else 0.0

        graph_score = 0.0
        graph_path = None
        graph_details = {}
        if current_user_id and current_user_id != u.id:
            graph_score, graph_path, graph_details = graph_service.get_peer_graph_details(current_user_id, u.id, u.name)

        dist_km = None
        geo_bonus = 0.0
        distance_band = "Location flexible"
        user_privacy = getattr(profile, "location_privacy", "approximate") or "approximate"
        user_privacy = user_privacy.lower().strip()

        if user_lat is not None and user_lon is not None and profile:
            if user_privacy in {"hidden", "off"}:
                dist_km = None
                geo_bonus = 0.0
                distance_band = "Distance hidden by user"
            else:
                raw_lat = getattr(profile, "latitude", None)
                raw_lon = getattr(profile, "longitude", None)
                if raw_lat is not None and raw_lon is not None:
                    obf_lat, obf_lon, _ = obfuscate_location(raw_lat, raw_lon, loc_str, user_privacy)
                    if obf_lat is not None and obf_lon is not None:
                        calc_dist = haversine_distance(user_lat, user_lon, obf_lat, obf_lon)
                        distance_band = get_coarse_distance_band(calc_dist)
                        if calc_dist <= 25.0:
                            geo_bonus = 0.10
                        elif calc_dist <= 50.0:
                            geo_bonus = 0.05
                        if user_privacy == "exact":
                            dist_km = round(calc_dist, 1)
                        else:
                            dist_km = None

        display_loc = loc_str
        if user_privacy in {"hidden", "off", "city", "approximate"}:
            display_loc = loc_str.split(",")[0].strip() if loc_str and loc_str.lower() != "online" else "Online"

        entity_bonus = 0.10 if "user" in target_entities else 0.0
        shared_skills = [s for s in intent_skills if s in skills_str.lower()]
        skill_bonus = 0.08 if shared_skills else 0.0

        pers_bonus = 0.0
        if user_profile_emb and u_emb:
            prof_sim = cosine_similarity(user_profile_emb, u_emb)
            pers_bonus += max(0.0, prof_sim) * 0.08
        if joined_community_tags and any(t in skills_str.lower() or t in interests_str.lower() for t in joined_community_tags):
            pers_bonus += 0.04

        semantic_val = sem_sim * 0.50
        keyword_val = keyword_score * 0.25
        graph_val = graph_score * 0.15
        geo_val = geo_bonus
        category_val = entity_bonus + skill_bonus + pers_bonus
        raw_score = semantic_val + keyword_val + graph_val + geo_val + category_val
        score = min(0.99, max(0.10, raw_score))

        score, matching_factors, feedback_reasons, loc_relevance, is_filtered, feedback_delta = apply_feedback_and_matching(
            item_type="user",
            item_id=u.id,
            base_score=score,
            sem_sim=sem_sim,
            overlap=overlap,
            dist_km=dist_km,
            loc_str=display_loc,
            distance_band=distance_band,
        )

        matched_elements = sorted(list(overlap))
        reasons = list(feedback_reasons)
        reasons.append("ALIGN Peer")
        if shared_skills:
            reasons.append(f"skills: {', '.join(s.upper() if len(s)<=3 else s.capitalize() for s in shared_skills[:2])}")
        if sem_sim >= 0.35:
            reasons.append(f"{int(sem_sim * 100)}% semantic intent alignment")
        if matched_elements:
            reasons.append(f"shared: {', '.join(matched_elements[:3])}")
        if graph_score > 0.0:
            reasons.append(f"network link (+{int(graph_score * 100)}%)")
        reasons.append(loc_relevance)

        reason = " · ".join(reasons)

        matched_terms = [m.split(": ", 1)[-1] if ": " in m else m for m in matching_factors]
        score_breakdown = compute_shapley_score_breakdown(
            semantic_val=semantic_val,
            keyword_val=keyword_val,
            graph_val=graph_val,
            geo_val=geo_val,
            category_val=category_val,
            feedback_val=max(0.0, feedback_delta),
            final_score=score,
        )

        why_rec = build_xai_explanation(
            result_type="user",
            title=u.name,
            matched_terms=matching_factors,
            graph_path=graph_path,
            graph_details=graph_details,
            dist_km=dist_km,
            loc_str=display_loc,
            sem_sim=sem_sim,
            distance_band=distance_band,
        )

        skills_list = [s.strip() for s in skills_str.split(",") if s.strip()]

        if not is_filtered and (score >= 0.15 or len(overlap) > 0 or sem_sim >= 0.30):
            results.append({
                "result_type": "user",
                "id": u.id,
                "title": u.name,
                "description": bio_str or "ALIGN Community Member",
                "category": "Peer & Collaborator",
                "location": display_loc,
                "score": round(score, 4),
                "score_breakdown": score_breakdown,
                "matched_terms": matched_terms,
                "graph_path": graph_path,
                "reason": reason,
                "why_recommended": why_rec,
                "matching_factors": matching_factors,
                "location_relevance": loc_relevance,
                "source": "ALIGN",
                "is_verified": True,
                "distance_km": dist_km,
                "distance_band": distance_band,
                "tags": skills_str or interests_str,
                "avatar_url": profile.avatar_url if profile else None,
                "profile_url": None,
                "skills": skills_list,
            })

    # 5. Rank Collaborative Projects
    for prj in projects:
        text_for_sim = f"{prj.title} {prj.tagline} {prj.description} {prj.category} {prj.skills_needed} {prj.required_roles}".strip()
        prj_emb = getattr(prj, "embedding", None)
        if not prj_emb:
            prj_emb = generate_embedding(text_for_sim)

        sem_sim = cosine_similarity(query_emb, prj_emb)
        prj_tokens = tokens(text_for_sim)
        overlap = query_tokens & prj_tokens
        keyword_score = len(overlap) / max(1, len(query_tokens)) if query_tokens else 0.0

        entity_bonus = 0.10 if "project" in target_entities else 0.0
        shared_skills = [s for s in intent_skills if s in (getattr(prj, "skills_needed", "") or "").lower()]
        skill_bonus = 0.08 if shared_skills else 0.0

        pers_bonus = 0.0
        if user_profile_emb and prj_emb:
            prof_sim = cosine_similarity(user_profile_emb, prj_emb)
            pers_bonus += max(0.0, prof_sim) * 0.08

        semantic_val = sem_sim * 0.55
        keyword_val = keyword_score * 0.25
        graph_val = 0.0
        geo_val = 0.0
        category_val = entity_bonus + skill_bonus + pers_bonus
        raw_score = semantic_val + keyword_val + category_val
        score = min(0.99, max(0.10, raw_score))

        score, matching_factors, feedback_reasons, loc_relevance, is_filtered, feedback_delta = apply_feedback_and_matching(
            item_type="project",
            item_id=prj.id,
            base_score=score,
            sem_sim=sem_sim,
            overlap=overlap,
            dist_km=None,
            loc_str="Remote / Global",
        )

        reasons = list(feedback_reasons)
        reasons.append("Collaborative Project")
        if shared_skills:
            reasons.append(f"needs: {', '.join(shared_skills[:2])}")
        if sem_sim >= 0.35:
            reasons.append(f"{int(sem_sim * 100)}% semantic intent alignment")
        if overlap:
            reasons.append(f"matched: {', '.join(sorted(list(overlap))[:2])}")
        reasons.append(loc_relevance)

        reason = " · ".join(reasons)

        matched_terms = [m.split(": ", 1)[-1] if ": " in m else m for m in matching_factors]
        score_breakdown = compute_shapley_score_breakdown(
            semantic_val=semantic_val,
            keyword_val=keyword_val,
            graph_val=graph_val,
            geo_val=geo_val,
            category_val=category_val,
            feedback_val=max(0.0, feedback_delta),
            final_score=score,
        )

        why_rec = build_xai_explanation(
            result_type="project",
            title=prj.title,
            matched_terms=matching_factors,
            graph_path=None,
            graph_details={},
            dist_km=None,
            loc_str="Remote / Global",
            sem_sim=sem_sim,
        )

        if not is_filtered and (score >= 0.15 or len(overlap) > 0 or sem_sim >= 0.30):
            tagline = getattr(prj, "tagline", "") or ""
            desc = getattr(prj, "description", "") or ""
            full_desc = f"{tagline} · {desc}"[:250] if tagline else desc[:250]
            results.append({
                "result_type": "project",
                "id": prj.id,
                "title": prj.title,
                "description": full_desc,
                "category": prj.category,
                "location": "Collaborative / Remote",
                "score": round(score, 4),
                "score_breakdown": score_breakdown,
                "matched_terms": matched_terms,
                "graph_path": None,
                "reason": reason,
                "why_recommended": why_rec,
                "matching_factors": matching_factors,
                "location_relevance": "Collaborative / Remote",
                "source": "ALIGN Projects",
                "is_verified": True,
                "distance_km": None,
                "distance_band": None,
                "tags": getattr(prj, "skills_needed", ""),
            })

    # 6. Rank Opportunities (Hackathons, Fellowships, Internships)
    for opp in opportunities:
        text_for_sim = f"{opp.title} {opp.organization} {opp.opportunity_type} {opp.description} {opp.tags} {opp.location}".strip()
        opp_emb = getattr(opp, "embedding", None)
        if not opp_emb:
            opp_emb = generate_embedding(text_for_sim)

        sem_sim = cosine_similarity(query_emb, opp_emb)
        opp_tokens = tokens(text_for_sim)
        overlap = query_tokens & opp_tokens
        keyword_score = len(overlap) / max(1, len(query_tokens)) if query_tokens else 0.0

        pers_bonus = 0.0
        if user_profile_emb and opp_emb:
            prof_sim = cosine_similarity(user_profile_emb, opp_emb)
            pers_bonus += max(0.0, prof_sim) * 0.08

        entity_bonus = 0.10 if "opportunity" in target_entities else 0.0
        semantic_val = sem_sim * 0.55
        keyword_val = keyword_score * 0.25
        graph_val = 0.0
        geo_val = 0.0
        category_val = entity_bonus + pers_bonus
        raw_score = semantic_val + keyword_val + category_val
        score = min(0.99, max(0.10, raw_score))

        loc_str = getattr(opp, "location", "") or "Remote / Global"
        score, matching_factors, feedback_reasons, loc_relevance, is_filtered, feedback_delta = apply_feedback_and_matching(
            item_type="opportunity",
            item_id=opp.id,
            base_score=score,
            sem_sim=sem_sim,
            overlap=overlap,
            dist_km=None,
            loc_str=loc_str,
        )

        reasons = list(feedback_reasons)
        reasons.append(f"{opp.opportunity_type.title()} Opportunity")
        if sem_sim >= 0.35:
            reasons.append(f"{int(sem_sim * 100)}% semantic intent alignment")
        if overlap:
            reasons.append(f"matched: {', '.join(sorted(list(overlap))[:2])}")
        reasons.append(loc_relevance)

        reason = " · ".join(reasons)

        matched_terms = [m.split(": ", 1)[-1] if ": " in m else m for m in matching_factors]
        score_breakdown = compute_shapley_score_breakdown(
            semantic_val=semantic_val,
            keyword_val=keyword_val,
            graph_val=graph_val,
            geo_val=geo_val,
            category_val=category_val,
            feedback_val=max(0.0, feedback_delta),
            final_score=score,
        )

        why_rec = build_xai_explanation(
            result_type="opportunity",
            title=opp.title,
            matched_terms=matching_factors,
            graph_path=None,
            graph_details={},
            dist_km=None,
            loc_str=loc_str,
            sem_sim=sem_sim,
        )

        if not is_filtered and (score >= 0.15 or len(overlap) > 0 or sem_sim >= 0.30):
            results.append({
                "result_type": "opportunity",
                "id": opp.id,
                "title": f"{opp.title} · {opp.organization}",
                "description": (opp.description or "")[:250],
                "category": opp.opportunity_type.title(),
                "location": loc_str,
                "score": round(score, 4),
                "score_breakdown": score_breakdown,
                "matched_terms": matched_terms,
                "graph_path": None,
                "reason": reason,
                "why_recommended": why_rec,
                "matching_factors": matching_factors,
                "location_relevance": loc_relevance,
                "source": getattr(opp, "source", "") or "Verified External",
                "is_verified": True,
                "distance_km": None,
                "distance_band": None,
                "tags": getattr(opp, "tags", ""),
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]
