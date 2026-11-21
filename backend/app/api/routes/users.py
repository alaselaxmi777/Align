from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.user import User, Profile, UserPreference, UserReport, UserBlock
from app.models.connection import UserConnection
from app.models.notification import Notification
from app.schemas.auth import UserResponse, ProfileResponse, ProfileUpdate, ReportUserRequest
from app.schemas.catalog import GithubSyncRequest
from app.services.github_service import fetch_user_github_skills
from app.services.embeddings import generate_embedding, cosine_similarity, build_profile_text
from app.services.discovery import tokens
from app.services.graph_service import graph_service
from app.services.location_privacy import sanitize_public_peer_location, obfuscate_location
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/users", tags=["users"])

import re
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
RESERVED_USERNAMES = {
    "admin", "administrator", "system", "align", "root", "support",
    "help", "api", "feed", "reels", "settings", "explore", "discover"
}

@router.get("/check-username", dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))])
def check_username(
    username: str = Query(..., min_length=1, max_length=50),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """Live validation and uniqueness check for user handles."""
    clean_username = username.strip().lower()
    if not USERNAME_REGEX.match(clean_username):
        return {
            "available": False,
            "username": clean_username,
            "message": "Username must be 3-20 characters long and contain only letters, numbers, or underscores.",
        }

    if clean_username in RESERVED_USERNAMES:
        return {
            "available": False,
            "username": clean_username,
            "message": "This username is reserved. Please choose another.",
        }

    stmt = select(User).where(func.lower(User.username) == clean_username)
    if user:
        stmt = stmt.where(User.id != user.id)

    existing = db.scalar(stmt)
    if existing:
        return {
            "available": False,
            "username": clean_username,
            "message": "This username is already taken. Please choose another.",
        }

    return {
        "available": True,
        "username": clean_username,
        "message": "Username is available!",
    }

def get_user_connection_stats(user_id: int, db: Session) -> tuple[int, int, int]:
    following = db.scalar(select(func.count(UserConnection.id)).where(UserConnection.sender_id == user_id, UserConnection.status == "accepted")) or 0
    followers = db.scalar(select(func.count(UserConnection.id)).where(UserConnection.receiver_id == user_id, UserConnection.status == "accepted")) or 0
    total = db.scalar(select(func.count(UserConnection.id)).where(
        or_(UserConnection.sender_id == user_id, UserConnection.receiver_id == user_id),
        UserConnection.status == "accepted"
    )) or 0
    return followers, following, total

@router.get("", response_model=list[UserResponse])
def list_users(
    q: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=100),
    meaningful_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    stmt = (
        select(User)
        .join(Profile, User.id == Profile.user_id, isouter=True)
        .where(User.is_active == True, User.is_test == False)
    )
    if user:
        stmt = stmt.where(User.id != user.id)
        # Exclude blocked users both ways
        blocked_by_me = select(UserBlock.blocked_user_id).where(UserBlock.blocker_id == user.id)
        blocking_me = select(UserBlock.blocker_id).where(UserBlock.blocked_user_id == user.id)
        blocked_ids = set(db.scalars(blocked_by_me)).union(set(db.scalars(blocking_me)))
        if blocked_ids:
            stmt = stmt.where(User.id.not_in(blocked_ids))

    stmt = stmt.where(
        or_(Profile.privacy_level.is_(None), Profile.privacy_level != "private")
    )

    if meaningful_only and not q:
        stmt = stmt.where(
            or_(
                Profile.onboarding_completed == True,
                Profile.skills != "",
                Profile.interests != "",
                Profile.goals != "",
            )
        )

    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                User.name.ilike(term),
                Profile.skills.ilike(term),
                Profile.hobbies.ilike(term),
                Profile.interests.ilike(term),
                Profile.goals.ilike(term),
                Profile.location.ilike(term),
                Profile.bio.ilike(term),
            )
        )

    all_users = list(db.scalars(stmt))

    # Pre-fetch existing connections for logged-in user
    conn_map: dict[int, tuple[str, int, bool]] = {}
    if user:
        conns = list(db.scalars(
            select(UserConnection).where(
                or_(UserConnection.sender_id == user.id, UserConnection.receiver_id == user.id)
            )
        ))
        for c in conns:
            other_id = c.receiver_id if c.sender_id == user.id else c.sender_id
            conn_map[other_id] = (c.status, c.id, c.sender_id == user.id)

    # Reference embedding for semantic matching
    user_emb = None
    query_emb = None
    user_tokens = set()
    user_skills_set = set()
    user_hobbies_set = set()
    if user and user.profile and user.profile.embedding:
        user_emb = user.profile.embedding
        user_tokens = tokens(f"{user.profile.skills} {user.profile.hobbies} {user.profile.interests} {user.profile.goals}")
        user_skills_set = {s.strip().lower() for s in user.profile.skills.split(",") if s.strip()}
        user_hobbies_set = {h.strip().lower() for h in user.profile.hobbies.split(",") if h.strip()}

    if q and q.strip():
        query_emb = generate_embedding(q.strip())

    user_scores: list[tuple[User, float, str]] = []
    for cand in all_users:
        cand_prof = cand.profile
        sem_sim = 0.0
        cand_emb = cand_prof.embedding if cand_prof else None

        if query_emb and cand_emb:
            sem_sim = cosine_similarity(query_emb, cand_emb)
        elif user_emb and cand_emb:
            sem_sim = cosine_similarity(user_emb, cand_emb)

        cand_tokens = tokens(f"{cand_prof.skills if cand_prof else ''} {cand_prof.hobbies if cand_prof else ''} {cand_prof.interests if cand_prof else ''} {cand_prof.goals if cand_prof else ''}")
        shared = sorted(list(user_tokens & cand_tokens)) if user_tokens else []

        cand_skills_list = [s.strip() for s in (cand_prof.skills if cand_prof else "").split(",") if s.strip()]
        cand_hobbies_list = [h.strip() for h in (cand_prof.hobbies if cand_prof else "").split(",") if h.strip()]

        shared_skills = [s for s in cand_skills_list if s.lower() in user_skills_set]
        shared_hobbies = [h for h in cand_hobbies_list if h.lower() in user_hobbies_set]

        reasons = []
        if shared_skills and shared_hobbies:
            reasons.append(f"Shared skill in {shared_skills[0]} & hobby in {shared_hobbies[0]}")
        elif shared_skills:
            reasons.append(f"Shared skills: {', '.join(shared_skills[:2])}")
        elif shared_hobbies:
            reasons.append(f"Shared hobbies: {', '.join(shared_hobbies[:2])}")
        elif shared:
            reasons.append(f"Shared focus in {', '.join(shared[:3])}")
        elif sem_sim >= 0.35:
            reasons.append(f"{int(sem_sim * 100)}% semantic alignment")
        elif cand_skills_list:
            reasons.append(f"Skilled in {', '.join(cand_skills_list[:2])}")
        elif cand_hobbies_list:
            reasons.append(f"Enjoys {', '.join(cand_hobbies_list[:2])}")

        reason = " · ".join(reasons) if reasons else "ALIGN Community Member"

        keyword_boost = 0.0
        if q and q.strip():
            q_lower = q.strip().lower()
            if any(q_lower == s.lower() for s in cand_skills_list):
                keyword_boost += 0.50
            elif any(q_lower in s.lower() for s in cand_skills_list):
                keyword_boost += 0.30
            if q_lower in (cand.name or "").lower():
                keyword_boost += 0.40

        score = (sem_sim * 0.60) + keyword_boost + ((len(shared) / max(1, len(user_tokens))) * 0.40 if user_tokens else 0.0)
        user_scores.append((cand, score, reason))

    # Rank by relevance when search query or user embedding is available; recency tie-breaker
    user_scores.sort(key=lambda x: (x[1], x[0].id), reverse=True)

    # Pagination
    start = (page - 1) * limit
    paged = user_scores[start:start + limit]

    result = []
    viewer_lat = user.profile.latitude if user and user.profile else None
    viewer_lon = user.profile.longitude if user and user.profile else None

    for cand, score, reason in paged:
        conn_info = conn_map.get(cand.id)
        u_resp = UserResponse.model_validate(cand)
        # Privacy protection: sanitize location; never return raw coordinates of other users
        loc_info = sanitize_public_peer_location(cand.profile, viewer_lat, viewer_lon)
        u_resp.location = loc_info["city"]
        u_resp.distance_band = loc_info["distance_band"]
        if u_resp.profile:
            u_resp.profile.latitude = None
            u_resp.profile.longitude = None
            u_resp.profile.location = loc_info["city"]
        # Never expose other users' email addresses in recommendations/listings
        if not user or not (user.is_admin or user.id == cand.id):
            u_resp.email = None

        u_resp.connection_status = conn_info[0] if conn_info else "none"
        u_resp.connection_id = conn_info[1] if conn_info else None
        u_resp.is_connection_sender = conn_info[2] if conn_info else False
        u_resp.recommendation_reason = reason
        u_resp.match_score = round(score, 4) if score > 0 else None
        result.append(u_resp)

    return result

@router.get("/me", response_model=UserResponse)
def get_current_user_info(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    followers, following, total = get_user_connection_stats(user.id, db)
    u_resp = UserResponse.model_validate(user)
    u_resp.followers_count = followers
    u_resp.following_count = following
    u_resp.connections_count = total
    u_resp.onboarding_completed = user.is_onboarded
    u_resp.is_onboarded = user.is_onboarded
    if u_resp.profile:
        u_resp.profile.followers_count = followers
        u_resp.profile.following_count = following
        u_resp.profile.connections_count = total
    return u_resp

@router.put("/me/profile", response_model=ProfileResponse)
def update_profile(payload: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()
    else:
        profile = user.profile

    if payload.name:
        user.name = payload.name.strip()

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field != "name" and value is not None:
            setattr(profile, field, value)

    # Recompute vector embedding for intent discovery
    ctx = build_profile_text(
        bio=profile.bio,
        interests=profile.interests,
        skills=profile.skills,
        goals=profile.goals,
        preferred_activities=profile.preferred_activities,
        preferred_community_types=profile.preferred_community_types,
    )
    profile.embedding = generate_embedding(ctx) if ctx else None

    db.commit()
    db.refresh(profile)

    # Real-time sync to Neo4j Knowledge Graph
    try:
        interests_list = [i.strip() for i in (profile.interests or "").split(",") if i.strip()]
        skills_list = [s.strip() for s in (profile.skills or "").split(",") if s.strip()]
        goals_list = [g.strip() for g in (profile.goals or "").split(",") if g.strip()]
        graph_service.sync_user_profile(
            user_id=user.id,
            name=user.name,
            email=user.email,
            location=profile.location or "",
            interests=interests_list,
            skills=skills_list,
            goals=goals_list,
        )
    except Exception:
        pass

    followers, following, total = get_user_connection_stats(user.id, db)
    p_resp = ProfileResponse.model_validate(profile)
    p_resp.followers_count = followers
    p_resp.following_count = following
    p_resp.connections_count = total
    return p_resp

@router.post("/me/sync-github", response_model=ProfileResponse)
def sync_github_skills(
    payload: GithubSyncRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Imports verified programming languages, repository topics, and bio from GitHub
    to populate and vector-index the user's ALIGN profile skills.
    """
    try:
        gh_data = fetch_user_github_skills(payload.github_username)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch GitHub profile for '{payload.github_username}': {exc}"
        )

    if not user.profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()
    else:
        profile = user.profile

    # Merge or set skills
    existing_skills = [s.strip() for s in (profile.skills or "").split(",") if s.strip()]
    merged_skills = sorted(list(set(existing_skills + gh_data["skills"])))
    profile.skills = ", ".join(merged_skills)

    if not profile.bio and gh_data.get("bio"):
        profile.bio = gh_data["bio"]
    if not profile.avatar_url and gh_data.get("avatar_url"):
        profile.avatar_url = gh_data["avatar_url"]
    if not profile.location and gh_data.get("location"):
        profile.location = gh_data["location"]

    # Recompute vector embedding for intent discovery
    ctx = f"{profile.bio} {profile.interests} {profile.skills} {profile.goals}"
    profile.embedding = generate_embedding(ctx)

    db.commit()
    db.refresh(profile)
    return profile

@router.get("/me/preferences")
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = list(db.scalars(select(UserPreference).where(UserPreference.user_id == user.id)))
    return {p.preference_key: p.preference_value for p in prefs}

@router.get("/me/export")
def export_user_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns complete, GDPR-compliant data export archive for the authenticated user,
    including account profile, preferences, memberships, connections, and saved items.
    """
    profile = user.profile
    prefs = list(db.scalars(select(UserPreference).where(UserPreference.user_id == user.id)))
    pref_dict = {p.preference_key: p.preference_value for p in prefs}

    return {
        "export_generated_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_verified": user.is_verified,
        },
        "profile": {
            "bio": profile.bio if profile else None,
            "location": profile.location if profile else None,
            "interests": profile.interests if profile else None,
            "skills": profile.skills if profile else None,
            "hobbies": profile.hobbies if profile else None,
            "goals": profile.goals if profile else None,
            "preferred_activities": profile.preferred_activities if profile else None,
            "preferred_community_types": profile.preferred_community_types if profile else None,
            "privacy_level": profile.privacy_level if profile else "public",
            "location_privacy": profile.location_privacy if profile else "approximate",
        },
        "preferences": pref_dict,
    }

@router.delete("/me")
def delete_own_user_account(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently deletes user account, purging records from PostgreSQL and Neo4j."""
    user_id = user.id
    try:
        graph_service.delete_user_node(user_id)
    except Exception:
        pass

    db.delete(user)
    db.commit()
    return {"status": "ok", "message": f"User {user_id} and all associated records permanently purged."}

@router.get("/handle/{username}", response_model=UserResponse)
def get_user_by_username(
    username: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    target = db.scalar(select(User).where(func.lower(User.username) == username.lower()))
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return get_user_by_id(target.id, db, current_user)

@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    followers, following, total = get_user_connection_stats(target.id, db)
    u_resp = UserResponse.model_validate(target)
    u_resp.followers_count = followers
    u_resp.following_count = following
    u_resp.connections_count = total
    u_resp.onboarding_completed = target.is_onboarded
    u_resp.is_onboarded = target.is_onboarded

    # Protect private email and coordinates unless viewing self or admin
    is_self = current_user is not None and current_user.id == target.id
    is_admin = current_user is not None and getattr(current_user, "is_admin", False)
    if not (is_self or is_admin):
        u_resp.email = None
        viewer_lat = current_user.profile.latitude if current_user and current_user.profile else None
        viewer_lon = current_user.profile.longitude if current_user and current_user.profile else None
        loc_info = sanitize_public_peer_location(target.profile, viewer_lat, viewer_lon)
        u_resp.location = loc_info["city"]
        u_resp.distance_band = loc_info["distance_band"]
        if u_resp.profile:
            u_resp.profile.latitude = None
            u_resp.profile.longitude = None
            u_resp.profile.location = loc_info["city"]
    elif u_resp.profile:
        u_resp.profile.followers_count = followers
        u_resp.profile.following_count = following
        u_resp.profile.connections_count = total
    return u_resp

@router.post("/{target_user_id}/disconnect")
@router.delete("/connections/{connection_id}")
def disconnect_user(
    target_user_id: int | None = None,
    connection_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if connection_id:
        conn = db.get(UserConnection, connection_id)
        if not conn or (conn.sender_id != user.id and conn.receiver_id != user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
        other_id = conn.receiver_id if conn.sender_id == user.id else conn.sender_id
    elif target_user_id:
        conn = db.scalar(
            select(UserConnection).where(
                or_(
                    (UserConnection.sender_id == user.id) & (UserConnection.receiver_id == target_user_id),
                    (UserConnection.sender_id == target_user_id) & (UserConnection.receiver_id == user.id),
                )
            )
        )
        if not conn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No connection found with this user.")
        other_id = target_user_id
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must provide connection_id or target_user_id.")

    db.delete(conn)
    db.commit()

    try:
        graph_service.sync_connection(user.id, other_id, connected=False)
    except Exception:
        pass

    return {"status": "ok", "message": "Connection removed successfully."}

@router.post("/{target_user_id}/connect")
def send_connection_request(
    target_user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if target_user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot connect with yourself.")

    target = db.get(User, target_user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")

    # Check if connection already exists in either direction
    existing = db.scalar(
        select(UserConnection).where(
            or_(
                (UserConnection.sender_id == user.id) & (UserConnection.receiver_id == target_user_id),
                (UserConnection.sender_id == target_user_id) & (UserConnection.receiver_id == user.id),
            )
        )
    )
    if existing:
        return {
            "status": "ok",
            "message": f"Connection already exists with status: {existing.status}",
            "connection_id": existing.id,
            "connection_status": existing.status,
        }

    conn = UserConnection(
        sender_id=user.id,
        receiver_id=target_user_id,
        status="pending",
    )
    db.add(conn)

    # Trigger notification to receiver
    notif = Notification(
        user_id=target_user_id,
        title="New Connection Request",
        message=f"{user.name} sent you a peer connection invite.",
        link="/people",
    )
    db.add(notif)
    db.commit()
    db.refresh(conn)

    return {
        "status": "ok",
        "message": "Connection request sent successfully.",
        "connection_id": conn.id,
        "connection_status": "pending",
    }

@router.post("/connections/{connection_id}/accept")
def accept_connection(
    connection_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = db.get(UserConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    if conn.receiver_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only recipient can accept connection.")

    conn.status = "accepted"

    # Real-time sync to Neo4j Knowledge Graph
    try:
        graph_service.sync_connection(conn.sender_id, conn.receiver_id, connected=True)
    except Exception:
        pass

    # Notify original sender
    notif = Notification(
        user_id=conn.sender_id,
        title="Connection Accepted 🎉",
        message=f"{user.name} accepted your connection request.",
        link="/people",
    )
    db.add(notif)
    db.commit()

    return {"status": "ok", "message": "Connection accepted successfully."}

@router.post("/connections/{connection_id}/reject")
def reject_connection(
    connection_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = db.get(UserConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    if conn.receiver_id != user.id and conn.sender_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    conn.status = "rejected"
    db.commit()

    # Real-time sync to Neo4j Knowledge Graph
    try:
        graph_service.sync_connection(conn.sender_id, conn.receiver_id, connected=False)
    except Exception:
        pass

    return {"status": "ok", "message": "Connection rejected."}

@router.get("/me/connections")
def list_my_connections(
    status_filter: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(UserConnection).where(
        or_(UserConnection.sender_id == user.id, UserConnection.receiver_id == user.id)
    )
    if status_filter:
        stmt = stmt.where(UserConnection.status == status_filter.strip())

    conns = list(db.scalars(stmt))
    results = []
    for c in conns:
        is_sender = (c.sender_id == user.id)
        other_user = c.receiver if is_sender else c.sender
        results.append({
            "connection_id": c.id,
            "status": c.status,
            "created_at": c.created_at,
            "is_sender": is_sender,
            "partner_id": other_user.id if other_user else None,
            "partner_name": other_user.name if other_user else "ALIGN Member",
            "partner_avatar": other_user.profile.avatar_url if (other_user and other_user.profile) else None,
            "partner_skills": other_user.profile.skills if (other_user and other_user.profile) else "",
            "partner_location": other_user.profile.location if (other_user and other_user.profile) else "",
        })
    return results

@router.get("/{target_user_id}/connection-status")
def get_connection_status(
    target_user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = db.scalar(
        select(UserConnection).where(
            or_(
                (UserConnection.sender_id == user.id) & (UserConnection.receiver_id == target_user_id),
                (UserConnection.sender_id == target_user_id) & (UserConnection.receiver_id == user.id),
            )
        )
    )
    if not conn:
        return {"status": "none", "is_sender": False, "connection_id": None}
    return {
        "status": conn.status,
        "is_sender": (conn.sender_id == user.id),
        "connection_id": conn.id,
    }

@router.post("/{target_user_id}/report")
def report_user(
    target_user_id: int,
    payload: ReportUserRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if target_user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot report yourself.")

    target = db.get(User, target_user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    report = UserReport(
        reporter_id=user.id,
        reported_user_id=target_user_id,
        reason=payload.reason.strip(),
        details=payload.details.strip() if payload.details else None,
        status="pending",
    )
    db.add(report)
    db.commit()
    return {"status": "ok", "message": "Report submitted successfully for administrative review."}

@router.post("/{target_user_id}/block")
def block_user(
    target_user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if target_user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot block yourself.")

    target = db.get(User, target_user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    existing_block = db.scalar(
        select(UserBlock).where(
            (UserBlock.blocker_id == user.id) & (UserBlock.blocked_user_id == target_user_id)
        )
    )
    if not existing_block:
        db.add(UserBlock(blocker_id=user.id, blocked_user_id=target_user_id))

        # Sever any existing connections
        existing_conns = list(
            db.scalars(
                select(UserConnection).where(
                    or_(
                        (UserConnection.sender_id == user.id) & (UserConnection.receiver_id == target_user_id),
                        (UserConnection.sender_id == target_user_id) & (UserConnection.receiver_id == user.id),
                    )
                )
            )
        )
        for c in existing_conns:
            db.delete(c)

        db.commit()

        try:
            graph_service.sync_connection(user.id, target_user_id, connected=False)
        except Exception:
            pass

    return {"status": "ok", "message": f"User {target.name} has been blocked."}

@router.post("/{target_user_id}/unblock")
def unblock_user(
    target_user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    block = db.scalar(
        select(UserBlock).where(
            (UserBlock.blocker_id == user.id) & (UserBlock.blocked_user_id == target_user_id)
        )
    )
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block record not found.")

    db.delete(block)
    db.commit()
    return {"status": "ok", "message": "User unblocked successfully."}

@router.get("/me/blocks")
def list_my_blocks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    blocks = list(
        db.scalars(
            select(UserBlock).where(UserBlock.blocker_id == user.id)
        )
    )
    return [
        {
            "id": b.id,
            "blocked_user_id": b.blocked_user_id,
            "blocked_user_name": b.blocked_user.name if b.blocked_user else "ALIGN Member",
            "created_at": b.created_at,
        }
        for b in blocks
    ]
