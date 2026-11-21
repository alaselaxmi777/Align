from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_current_user_optional, get_current_admin
from app.db.session import get_db
from app.models.event import Event, EventRegistration
from app.models.notification import Notification
from app.models.user import User
from app.schemas.catalog import EventCreate, EventResponse, EventRegisterRequest
from app.services.embeddings import generate_embedding
from app.services.eventbrite import sync_eventbrite_events, purge_dummy_events
from app.services.gamification_service import award_xp
from app.services.graph_service import graph_service

router = APIRouter(prefix="/events", tags=["events"])

def populate_event_response(event: Event, user: User | None, db: Session) -> EventResponse:
    count = db.scalar(
        select(func.count(EventRegistration.id)).where(
            EventRegistration.event_id == event.id,
            EventRegistration.status == "registered"
        )
    ) or 0
    is_reg = False
    if user:
        is_reg = bool(
            db.scalar(
                select(func.count(EventRegistration.id)).where(
                    EventRegistration.event_id == event.id,
                    EventRegistration.user_id == user.id,
                    EventRegistration.status == "registered"
                )
            ) > 0
        )
    res = EventResponse.model_validate(event)
    res.registered_count = count
    res.is_registered = is_reg
    res.is_external = bool((event.source or "").strip().lower() == "eventbrite")
    res.is_expired = bool(event.starts_at and event.starts_at < datetime.now(timezone.utc))
    return res

@router.get("", response_model=list[EventResponse])
def list_events(
    q: str | None = Query(default=None, max_length=120),
    upcoming_only: bool = True,
    min_relevance: float = Query(default=0.40, ge=0.0, le=1.0),
    category: str | None = Query(default=None, max_length=80),
    location: str | None = Query(default=None, max_length=100),
    source: str | None = Query(default=None, max_length=50),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    # Automatically clean up dummy events
    try:
        purge_dummy_events(db)
    except Exception:
        pass

    # If database has no events, auto-ingest real-time events from Eventbrite
    try:
        total_evts = db.scalar(select(func.count(Event.id)).where(Event.is_cancelled == False)) or 0
        if total_evts == 0:
            sync_eventbrite_events(db, query="tech", purge_dummy=False)
    except Exception:
        pass

    stmt = select(Event).where(Event.is_cancelled == False)
    if upcoming_only:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(or_(Event.starts_at.is_(None), Event.starts_at >= now))
    if category:
        stmt = stmt.where(Event.category.ilike(f"%{category.strip()}%"))
    if location:
        stmt = stmt.where(Event.location.ilike(f"%{location.strip()}%"))
    if source:
        stmt = stmt.where(Event.source.ilike(f"%{source.strip()}%"))
    if date_from:
        stmt = stmt.where(Event.starts_at >= date_from)
    if date_to:
        stmt = stmt.where(Event.starts_at <= date_to)
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Event.title.ilike(term),
                Event.description.ilike(term),
                Event.category.ilike(term),
                Event.location.ilike(term),
            )
        )
    stmt = stmt.order_by(Event.starts_at.asc().nullslast(), Event.created_at.desc()).limit(limit)
    items = list(db.scalars(stmt))
    return [populate_event_response(e, user, db) for e in items]

@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    text_content = f"{payload.title} {payload.description} {payload.category} {payload.location}"
    emb = generate_embedding(text_content)
    item = Event(
        **payload.model_dump(),
        created_by_id=user.id,
        embedding=emb,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return populate_event_response(item, user, db)

@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return populate_event_response(event, user, db)

@router.post("/{event_id}/register")
@router.post("/{event_id}/rsvp")
def register_for_event(
    event_id: int,
    payload: EventRegisterRequest | None = None,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.is_cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This event has been cancelled.")

    # Determine attendee user: either authenticated user or create/find attendee by email
    target_user = user
    if not target_user:
        if payload and payload.email:
            email_clean = payload.email.strip().lower()
            target_user = db.scalar(select(User).where(User.email == email_clean))
            if not target_user:
                name_clean = (payload.name or payload.email.split("@")[0]).strip()
                target_user = User(
                    name=name_clean,
                    email=email_clean,
                    password_hash=None,
                    is_active=True,
                    is_verified=True,
                )
                db.add(target_user)
                db.flush()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please log in or provide your Name and Email to register for this event."
            )

    # Check capacity limit
    if event.capacity is not None:
        current_count = db.scalar(
            select(func.count(EventRegistration.id)).where(
                EventRegistration.event_id == event_id,
                EventRegistration.status == "registered"
            )
        ) or 0
        if current_count >= event.capacity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event is already at full capacity.")

    existing = db.scalar(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == target_user.id,
        )
    )
    ticket_code = f"ALIGN-EVT-{event.id:04d}-{target_user.id:04d}"

    if existing:
        if existing.status == "registered":
            return {
                "status": "ok",
                "message": "You are already registered for this event.",
                "ticket_code": ticket_code,
                "event_id": event.id,
                "event_title": event.title,
                "attendee_name": target_user.name,
                "attendee_email": target_user.email,
                "starts_at": event.starts_at.isoformat() if event.starts_at else None,
                "location": event.location,
            }
        existing.status = "registered"
        db.commit()
        return {
            "status": "ok",
            "message": "Re-registered for event successfully!",
            "ticket_code": ticket_code,
            "event_id": event.id,
            "event_title": event.title,
            "attendee_name": target_user.name,
            "attendee_email": target_user.email,
            "starts_at": event.starts_at.isoformat() if event.starts_at else None,
            "location": event.location,
        }

    reg = EventRegistration(
        user_id=target_user.id,
        event_id=event.id,
        status="registered"
    )
    db.add(reg)

    # Award authentic XP with anti-duplicate dedup key
    award_xp(db, target_user.id, "event_registered", 30, f"Registered for event: {event.title[:30]}", dedup_key=f"event_rsvp:{event.id}:{target_user.id}")

    # Send confirmation notification to registrant
    db.add(
        Notification(
            user_id=target_user.id,
            title="Event Registration Confirmed 🎟️",
            message=f"You are registered for '{event.title}'.",
            link="/events",
        )
    )

    # Notify event host if host exists and is distinct
    if event.created_by_id and event.created_by_id != target_user.id:
        db.add(
            Notification(
                user_id=event.created_by_id,
                title="New Event Registration",
                message=f"{target_user.name} registered for your event '{event.title}'.",
                link="/events",
            )
        )

    db.commit()

    # Real-time sync to Neo4j Knowledge Graph
    try:
        graph_service.sync_event_registration(target_user.id, event.id, registered=True, status="registered")
    except Exception:
        pass

    return {
        "status": "success",
        "message": "Successfully registered for event!",
        "ticket_code": ticket_code,
        "event_id": event.id,
        "event_title": event.title,
        "attendee_name": target_user.name,
        "attendee_email": target_user.email,
        "starts_at": event.starts_at.isoformat() if event.starts_at else None,
        "location": event.location,
        "ticket_count": payload.ticket_count if payload else 1
    }

@router.post("/{event_id}/cancel")
def cancel_registration(
    event_id: int,
    email: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target_user_id = user.id
    if email and user.is_admin:
        found_u = db.scalar(select(User).where(User.email == email.strip().lower()))
        if found_u:
            target_user_id = found_u.id
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User with specified email not found.")
    elif email and not user.is_admin and email.strip().lower() != user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to cancel registrations for other users."
        )

    existing = db.scalar(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == target_user_id,
        )
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not registered for this event.")

    db.delete(existing)
    db.commit()

    # Real-time sync to Neo4j Knowledge Graph
    try:
        graph_service.sync_event_registration(target_user_id, event_id, registered=False)
    except Exception:
        pass

    return {"status": "ok", "message": "Event registration cancelled successfully."}

@router.post("/purge-dummy")
def purge_dummy_events_endpoint(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = purge_dummy_events(db)
    return {"status": "ok", "purged": count, "message": f"Successfully purged {count} dummy events."}

@router.post("/sync/eventbrite")
def sync_events_from_eventbrite(
    q: str = Query(default="tech", max_length=100),
    location: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = sync_eventbrite_events(db=db, query=q, location=location, purge_dummy=True)
    return result

