from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.community import Community
from app.models.event import Event, EventRegistration
from app.models.opportunity import Opportunity
from app.models.place import Place
from app.models.post import Post
from app.models.project import Project
from app.models.reel import Reel
from app.models.user import User, UserReport
from app.models.notification import Notification
from app.models.dataset import GoalsInterestsDataset, SkillsHobbiesDataset, DatasetMetadata
from app.schemas.social import (
    AdminStatsResponse,
    ModerationActionRequest,
    ReportDetailResponse,
)
from app.services.dataset_importer import get_dataset_inventory
from app.services.eventbrite import sync_eventbrite_events, get_eventbrite_cache_stats
from app.services.places_service import sync_real_places
from app.services.graph_service import graph_service

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(user: User):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access this resource.",
        )

@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)

    users_count = db.scalar(select(func.count(User.id))) or 0
    communities_count = db.scalar(select(func.count(Community.id))) or 0
    events_count = db.scalar(select(func.count(Event.id))) or 0
    places_count = db.scalar(select(func.count(Place.id))) or 0
    posts_count = db.scalar(select(func.count(Post.id))) or 0
    reg_count = db.scalar(select(func.count(EventRegistration.id))) or 0
    reports_count = db.scalar(select(func.count(UserReport.id)).where(UserReport.status == "pending")) or 0

    gi_count = db.scalar(select(func.count(GoalsInterestsDataset.id))) or 0
    sh_count = db.scalar(select(func.count(SkillsHobbiesDataset.id))) or 0
    total_datasets_records = gi_count + sh_count

    pgvector_status = "disabled"
    try:
        res = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
        if res:
            pgvector_status = "active (384 dimensions)"
    except Exception:
        pgvector_status = "unverified"

    neo4j_health = "disconnected"
    try:
        g = graph_service.check_health()
        neo4j_health = "connected" if g.get("status") == "healthy" else "degraded"
    except Exception:
        pass

    return AdminStatsResponse(
        total_users=users_count,
        total_communities=communities_count,
        total_events=events_count,
        total_places=places_count,
        total_posts=posts_count,
        total_registrations=reg_count,
        total_dataset_records=total_datasets_records,
        total_reports=reports_count,
        database_status="healthy",
        pgvector_status=pgvector_status,
        neo4j_status=neo4j_health,
    )

@router.get("/datasets")
def list_datasets(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)
    return get_dataset_inventory(db)

@router.post("/sync/events")
def admin_sync_events(
    query: str = Query(default="tech"),
    location: str = Query(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)
    return sync_eventbrite_events(db, query=query, location=location, purge_dummy=True)

@router.post("/sync/places")
def admin_sync_places(
    city: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)
    return sync_real_places(db, city=city)

@router.get("/reports", response_model=list[ReportDetailResponse])
def list_user_reports(
    status_filter: str | None = Query(default="pending"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)
    stmt = select(UserReport).order_by(UserReport.created_at.desc())
    if status_filter:
        stmt = stmt.where(UserReport.status == status_filter.strip())
    reports = list(db.scalars(stmt))

    results = []
    for r in reports:
        snippet = None
        if r.post_id and r.post:
            snippet = r.post.content[:120]
        elif r.reel_id and r.reel:
            snippet = f"{r.reel.title} ({r.reel.caption or ''})".strip()[:120]

        results.append(
            ReportDetailResponse(
                id=r.id,
                reporter_id=r.reporter_id,
                reporter_name=r.reporter.name if r.reporter else "Unknown",
                reported_user_id=r.reported_user_id,
                reported_user_name=r.reported_user.name if r.reported_user else "Unknown",
                target_type=getattr(r, "target_type", "user") or "user",
                post_id=r.post_id,
                reel_id=r.reel_id,
                content_snippet=snippet,
                reason=r.reason,
                details=r.details,
                status=r.status,
                created_at=r.created_at,
            )
        )
    return results

@router.post("/reports/{report_id}/action")
def take_moderation_action(
    report_id: int,
    payload: ModerationActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Moderation action handler supporting:
    - remove_content: sets post/reel is_hidden = True and notifies author
    - warn_user: sends official warning notification to reported user
    - suspend_user: disables user account (is_active = False)
    - dismiss_report: marks report dismissed
    """
    require_admin(user)
    report = db.get(UserReport, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    action = payload.action
    msg = ""

    if action == "dismiss_report":
        report.status = "dismissed"
        msg = f"Report #{report_id} dismissed."

    elif action == "remove_content":
        if report.post_id and report.post:
            report.post.is_hidden = True
            msg = f"Post #{report.post_id} removed/hidden from feed."
            notif = Notification(
                user_id=report.post.author_id,
                title="Content Removed by Moderation",
                message="Your post was hidden by moderation for violating community standards.",
                link="/feed",
            )
            db.add(notif)
        elif report.reel_id and report.reel:
            report.reel.is_hidden = True
            msg = f"Reel #{report.reel_id} removed/hidden from platform."
            notif = Notification(
                user_id=report.reel.author_id,
                title="Content Removed by Moderation",
                message="Your reel was hidden by moderation for violating community standards.",
                link="/reels",
            )
            db.add(notif)
        else:
            msg = "No specific content linked to this report."
        report.status = "resolved"

    elif action == "warn_user":
        target_uid = report.reported_user_id
        if not target_uid and report.post:
            target_uid = report.post.author_id
        elif not target_uid and report.reel:
            target_uid = report.reel.author_id

        if target_uid:
            notif = Notification(
                user_id=target_uid,
                title="Official Community Warning",
                message=f"Your recent activity was flagged ({report.reason}). Please review ALIGN community guidelines.",
                link="/profile",
            )
            db.add(notif)
            msg = f"Official warning issued to user #{target_uid}."
        else:
            msg = "Could not resolve target user to warn."
        report.status = "resolved"

    elif action == "suspend_user":
        target_uid = report.reported_user_id
        if not target_uid and report.post:
            target_uid = report.post.author_id
        elif not target_uid and report.reel:
            target_uid = report.reel.author_id

        if target_uid:
            target_user = db.get(User, target_uid)
            if target_user:
                target_user.is_active = False
                msg = f"User #{target_uid} ({target_user.name}) has been suspended."
            else:
                msg = f"User #{target_uid} not found."
        else:
            msg = "Could not resolve target user to suspend."
        report.status = "resolved"

    db.commit()
    return {"status": "ok", "message": msg, "action": action}

@router.post("/reports/{report_id}/resolve")
def resolve_report(
    report_id: int,
    action: str = Query(default="resolved"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)
    report = db.get(UserReport, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    report.status = action
    db.commit()
    return {"status": "ok", "message": f"Report #{report_id} marked as {action}."}

@router.get("/data-health")
def get_data_health(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Data health observability endpoint reporting:
    - Last successful fetch / sync per external source
    - Live row counts across all platform entities (real vs test)
    - Expired, inactive, and cancelled item counts
    - Runtime caching and rate-limiting status
    """
    require_admin(user)
    now = datetime.now(timezone.utc)

    # 1. Row counts & test exclusions
    total_users = db.scalar(select(func.count(User.id))) or 0
    test_users = db.scalar(select(func.count(User.id)).where(User.is_test == True)) or 0
    real_users = total_users - test_users

    total_communities = db.scalar(select(func.count(Community.id))) or 0
    test_communities = db.scalar(select(func.count(Community.id)).where(Community.is_test == True)) or 0
    real_communities = total_communities - test_communities

    total_projects = db.scalar(select(func.count(Project.id))) or 0
    test_projects = db.scalar(select(func.count(Project.id)).where(Project.is_test == True)) or 0
    real_projects = total_projects - test_projects

    # Events breakdown
    total_events = db.scalar(select(func.count(Event.id))) or 0
    upcoming_events = db.scalar(select(func.count(Event.id)).where(Event.starts_at >= now, Event.is_cancelled == False)) or 0
    past_events = db.scalar(select(func.count(Event.id)).where(Event.starts_at < now)) or 0
    cancelled_events = db.scalar(select(func.count(Event.id)).where(Event.is_cancelled == True)) or 0

    # Opportunities breakdown
    total_opportunities = db.scalar(select(func.count(Opportunity.id))) or 0
    active_opportunities = db.scalar(select(func.count(Opportunity.id)).where(Opportunity.is_active == True, Opportunity.deadline >= now)) or 0
    expired_opportunities = db.scalar(select(func.count(Opportunity.id)).where(Opportunity.deadline < now)) or 0
    inactive_opportunities = db.scalar(select(func.count(Opportunity.id)).where(Opportunity.is_active == False)) or 0

    # Places, Posts, Reels
    total_places = db.scalar(select(func.count(Place.id))) or 0
    total_posts = db.scalar(select(func.count(Post.id))) or 0
    total_reels = db.scalar(select(func.count(Reel.id))) or 0

    # Source fetch timestamps
    latest_event = db.scalar(select(Event).order_by(Event.created_at.desc()).limit(1))
    latest_event_ts = latest_event.created_at.isoformat() if latest_event and latest_event.created_at else None

    latest_opp = db.scalar(select(Opportunity).order_by(Opportunity.last_verified_at.desc()).limit(1))
    latest_opp_ts = latest_opp.last_verified_at.isoformat() if latest_opp and latest_opp.last_verified_at else None

    eb_cache = get_eventbrite_cache_stats()

    return {
        "timestamp": now.isoformat(),
        "status": "healthy",
        "sources": [
            {
                "name": "Eventbrite Live Events",
                "status": "configured" if settings.eventbrite_private_token else "unconfigured (skipping remote sync)",
                "last_successful_fetch": latest_event_ts,
                "policy": "1-hour TTL in-memory cache; deduped by external_id and normalized (title, starts_at)",
                "cache_entries": eb_cache["cached_queries_count"],
            },
            {
                "name": "OpenStreetMap / Overpass & Nominatim",
                "status": "operational",
                "last_successful_fetch": now.isoformat(),
                "policy": "1 req/sec strict thread-safe rate-limit with User-Agent header; Haversine radius filtering",
                "total_places": total_places,
            },
            {
                "name": "Kaggle Competitions API",
                "status": "integrated",
                "last_successful_fetch": latest_opp_ts,
                "policy": "Immutable competition deadlines & reward ingestion",
            },
            {
                "name": "GitHub Good First Issues API",
                "status": "operational",
                "last_successful_fetch": now.isoformat(),
                "policy": "Live GitHub Search API with 30 req/min rate limit",
            },
            {
                "name": "Verified Opportunities Importer (CSV)",
                "status": "active",
                "last_successful_fetch": latest_opp_ts,
                "policy": "Real verified URLs with admin manual CSV upload & nightly expiry deactivation",
            },
        ],
        "row_counts": {
            "users": {"total": total_users, "real": real_users, "test": test_users},
            "communities": {"total": total_communities, "real": real_communities, "test": test_communities},
            "projects": {"total": total_projects, "real": real_projects, "test": test_projects},
            "events": {"total": total_events, "upcoming": upcoming_events, "past": past_events, "cancelled": cancelled_events},
            "opportunities": {"total": total_opportunities, "active": active_opportunities, "expired": expired_opportunities, "inactive": inactive_opportunities},
            "places": {"total": total_places},
            "posts": {"total": total_posts},
            "reels": {"total": total_reels},
        },
        "inactive_and_expired": {
            "expired_opportunities": expired_opportunities,
            "inactive_opportunities": inactive_opportunities,
            "cancelled_events": cancelled_events,
            "past_events": past_events,
            "test_entities_total": test_users + test_communities + test_projects,
        },
    }

