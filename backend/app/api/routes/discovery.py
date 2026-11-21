import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.api.deps import get_current_user_optional, get_current_user
from app.db.session import get_db
from app.models.community import Community, CommunityMembership
from app.models.event import Event
from app.models.place import Place
from app.models.user import User, Profile
from app.models.project import Project
from app.models.opportunity import Opportunity
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.saved import SavedItem
from app.models.instagram import SuggestedInterest
from app.schemas.catalog import (
    DiscoveryRequest,
    DiscoveryResult,
    RecommendationFeedbackCreate,
    RecommendationFeedbackResponse,
)
from app.services.discovery import discover
from app.services.embeddings import generate_embedding
from app.services.eventbrite import sync_eventbrite_events, purge_dummy_events
from app.services.github_service import fetch_github_people

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])

def fetch_pgvector_candidates(
    db: Session,
    model_cls,
    q_emb: list[float] | None = None,
    limit: int = 50,
    filter_clause = None,
) -> list:
    """
    Performs pgvector database-level approximate nearest neighbor retrieval using
    `ORDER BY embedding <=> :q LIMIT :limit`.
    Falls back gracefully to general database queries if embeddings are sparse.
    """
    stmt = select(model_cls)
    if hasattr(model_cls, "is_test"):
        stmt = stmt.where(model_cls.is_test == False)
    if filter_clause is not None:
        stmt = stmt.where(filter_clause)
    
    candidates = []
    if q_emb and hasattr(model_cls, "embedding"):
        try:
            vec_stmt = stmt.where(model_cls.embedding.isnot(None)).order_by(
                model_cls.embedding.cosine_distance(q_emb)
            ).limit(limit)
            candidates = list(db.scalars(vec_stmt))
        except Exception as exc:
            logger.debug(f"pgvector query fallback for {model_cls.__name__}: {exc}")
            candidates = []

    if len(candidates) < 15:
        existing_ids = {c.id for c in candidates}
        fallback_stmt = stmt.limit(limit)
        for item in db.scalars(fallback_stmt):
            if item.id not in existing_ids:
                candidates.append(item)
                if len(candidates) >= limit:
                    break
    return candidates

def get_user_personalization_signals(user: User | None, db: Session):
    """Extracts stated profile embedding, saved items categories, and joined community tags."""
    if not user:
        return None, set(), set()
    
    user_profile_emb = user.profile.embedding if user.profile else None
    
    saved_items = list(db.scalars(select(SavedItem).where(SavedItem.user_id == user.id)))
    saved_categories = {s.item_type for s in saved_items}
    
    joined_comms = list(db.scalars(
        select(Community)
        .join(CommunityMembership, Community.id == CommunityMembership.community_id)
        .where(CommunityMembership.user_id == user.id)
    ))
    joined_tags = {tag.strip().lower() for c in joined_comms for tag in (c.tags or "").split(",") if tag.strip()}
    joined_cats = {c.category.lower() for c in joined_comms if c.category}
    
    return user_profile_emb, saved_categories, joined_tags | joined_cats

@router.post(
    "/search",
    response_model=list[DiscoveryResult],
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def search(
    payload: DiscoveryRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    # Query Eventbrite API if user requested external live events and token is configured
    if payload.query and len(payload.query.strip()) >= 2 and settings.eventbrite_private_token:
        try:
            clean_query = payload.query.strip()[:60]
            sync_eventbrite_events(db=db, query=clean_query, purge_dummy=False)
        except Exception as exc:
            logger.debug(f"Eventbrite query skipped or failed: {exc}")

    # Generate query vector for pgvector ANN database retrieval
    q_emb = generate_embedding(payload.query) if payload.query else None

    # Retrieve candidates using pgvector cosine distance at database level
    communities = fetch_pgvector_candidates(db, Community, q_emb=q_emb, limit=50)
    events = fetch_pgvector_candidates(db, Event, q_emb=q_emb, limit=50, filter_clause=(Event.is_cancelled == False))
    places = fetch_pgvector_candidates(db, Place, q_emb=q_emb, limit=50)
    projects = fetch_pgvector_candidates(db, Project, q_emb=q_emb, limit=50, filter_clause=(Project.status != "archived"))
    opportunities = fetch_pgvector_candidates(db, Opportunity, q_emb=q_emb, limit=50)

    # Fetch real registered ALIGN peers
    users_stmt = select(User).join(Profile, User.id == Profile.user_id, isouter=True).where(User.is_active == True, User.is_test == False)
    if user:
        users_stmt = users_stmt.where(User.id != user.id)
    users_stmt = users_stmt.where(or_(Profile.privacy_level.is_(None), Profile.privacy_level != "private"))
    align_users = list(db.scalars(users_stmt))

    # User recommendation feedback loop
    user_feedback_map = {}
    if user:
        fb_list = list(db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.user_id == user.id)))
        user_feedback_map = {(f.item_type, f.item_id): f.feedback for f in fb_list}

    # Extract user profile personalization signals
    user_profile_emb, saved_categories, joined_tags = get_user_personalization_signals(user, db)

    # Inferred Instagram interests
    instagram_interests = set()
    if user:
        accepted_ig = list(db.scalars(
            select(SuggestedInterest.interest).where(
                SuggestedInterest.user_id == user.id,
                SuggestedInterest.source == "instagram",
                SuggestedInterest.status == "accepted",
            )
        ))
        instagram_interests = {i.lower().strip() for i in accepted_ig if i}

    user_lat = payload.user_lat
    user_lon = payload.user_lon
    if user_lat is None and user and user.profile and user.profile.latitude is not None:
        user_lat = user.profile.latitude
        user_lon = user.profile.longitude

    return discover(
        query=payload.query,
        communities=communities,
        events=events,
        places=places,
        people=None,
        users=align_users,
        projects=projects,
        opportunities=opportunities,
        limit=payload.limit,
        user_lat=user_lat,
        user_lon=user_lon,
        preferred_category=payload.category,
        current_user_id=user.id if user else None,
        user_feedback_map=user_feedback_map,
        user_profile_emb=user_profile_emb,
        saved_categories=saved_categories,
        joined_community_tags=joined_tags,
        instagram_interests=instagram_interests,
    )

@router.get(
    "/search",
    response_model=list[DiscoveryResult],
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def search_get(
    q: str = "",
    category: str | None = None,
    location: str | None = None,
    limit: int = 30,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    req = DiscoveryRequest(query=q, category=category, location=location, limit=limit)
    return search(req, db, user)

@router.get("/recommendations", response_model=list[DiscoveryResult])
def personalized_recommendations(
    limit: int = 16,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Computes real-time intent-based recommendations tailored to the authenticated user's profile,
    synthesizing their stated interests, skills, goals, location, and past recommendation feedback.
    """
    profile = user.profile
    if not profile or not (profile.interests or profile.skills or profile.hobbies or profile.goals):
        intent_query = f"{user.name} learning exploring communities"
    else:
        intent_query = f"{profile.interests} {profile.skills} {profile.hobbies} {profile.goals} {profile.preferred_activities}".strip()

    # Automatically purge dummy data & ensure real-time events exist
    try:
        purge_dummy_events(db)
        evt_count = db.scalar(select(func.count(Event.id)).where(Event.is_cancelled == False)) or 0
        if evt_count < 5:
            sync_eventbrite_events(db=db, query="tech", purge_dummy=False)
    except Exception as exc:
        logger.warning(f"Error during recommendation event sync: {exc}")

    # Generate embedding for intent query for pgvector ANN database retrieval
    q_emb = generate_embedding(intent_query)

    # Retrieve candidates using pgvector cosine distance at database level
    communities = fetch_pgvector_candidates(db, Community, q_emb=q_emb, limit=50)
    events = fetch_pgvector_candidates(db, Event, q_emb=q_emb, limit=50, filter_clause=(Event.is_cancelled == False))
    places = fetch_pgvector_candidates(db, Place, q_emb=q_emb, limit=50)
    projects = fetch_pgvector_candidates(db, Project, q_emb=q_emb, limit=50, filter_clause=(Project.status != "archived"))
    opportunities = fetch_pgvector_candidates(db, Opportunity, q_emb=q_emb, limit=50)

    # Real ALIGN users
    users_stmt = (
        select(User)
        .join(Profile, User.id == Profile.user_id, isouter=True)
        .where(User.is_active == True, User.is_test == False, User.id != user.id)
        .where(or_(Profile.privacy_level.is_(None), Profile.privacy_level != "private"))
    )
    align_users = list(db.scalars(users_stmt))

    # User recommendation feedback loop
    fb_list = list(db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.user_id == user.id)))
    user_feedback_map = {(f.item_type, f.item_id): f.feedback for f in fb_list}

    # Extract user profile personalization signals
    user_profile_emb, saved_categories, joined_tags = get_user_personalization_signals(user, db)

    # Inferred Instagram interests
    instagram_interests = set()
    accepted_ig = list(db.scalars(
        select(SuggestedInterest.interest).where(
            SuggestedInterest.user_id == user.id,
            SuggestedInterest.source == "instagram",
            SuggestedInterest.status == "accepted",
        )
    ))
    instagram_interests = {i.lower().strip() for i in accepted_ig if i}

    return discover(
        query=intent_query,
        communities=communities,
        events=events,
        places=places,
        people=None,
        users=align_users,
        projects=projects,
        opportunities=opportunities,
        limit=limit,
        user_lat=profile.latitude if profile else None,
        user_lon=profile.longitude if profile else None,
        current_user_id=user.id,
        user_feedback_map=user_feedback_map,
        user_profile_emb=user_profile_emb,
        saved_categories=saved_categories,
        joined_community_tags=joined_tags,
        instagram_interests=instagram_interests,
    )

@router.post("/feedback", response_model=RecommendationFeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_recommendation_feedback(
    payload: RecommendationFeedbackCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Submits user feedback on a recommended entity:
    - relevant: Boosts future ranking of similar entities and domains.
    - not_relevant: Down-ranks or excludes this item and penalizes related patterns.
    - already_done: Flags item as completed and removes it from proactive suggestions.
    - save_for_later: Adds item to user's saved items collection and maintains high priority.
    """
    existing = db.scalar(
        select(RecommendationFeedback).where(
            RecommendationFeedback.user_id == user.id,
            RecommendationFeedback.item_type == payload.item_type,
            RecommendationFeedback.item_id == payload.item_id,
        )
    )

    if existing:
        existing.feedback = payload.feedback
        existing.notes = payload.notes
        db.commit()
        db.refresh(existing)
        target = existing
    else:
        new_fb = RecommendationFeedback(
            user_id=user.id,
            item_type=payload.item_type,
            item_id=payload.item_id,
            feedback=payload.feedback,
            notes=payload.notes,
        )
        db.add(new_fb)
        db.commit()
        db.refresh(new_fb)
        target = new_fb

    # If feedback is 'save_for_later', ensure item is also in saved_items
    if payload.feedback == "save_for_later":
        saved_existing = db.scalar(
            select(SavedItem).where(
                SavedItem.user_id == user.id,
                SavedItem.item_type == payload.item_type,
                SavedItem.item_id == payload.item_id,
            )
        )
        if not saved_existing:
            db.add(SavedItem(user_id=user.id, item_type=payload.item_type, item_id=payload.item_id))
            db.commit()

    return target

@router.get("/feedback", response_model=list[RecommendationFeedbackResponse])
def get_user_recommendation_feedbacks(
    item_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieves all recommendation feedback recorded by the authenticated user."""
    stmt = select(RecommendationFeedback).where(RecommendationFeedback.user_id == user.id)
    if item_type:
        stmt = stmt.where(RecommendationFeedback.item_type == item_type)
    stmt = stmt.order_by(RecommendationFeedback.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))
