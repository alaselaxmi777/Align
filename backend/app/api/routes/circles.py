from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, select
from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.user import User, Profile
from app.models.circle import (
    InterestCircle,
    CircleMembership,
    CircleDiscussion,
    CircleDiscussionReply,
    CircleActivity,
)
from app.services.embeddings import generate_embedding, cosine_similarity
from app.services.gamification_service import award_xp, check_and_unlock_badge, get_or_create_gamification
from app.services.graph_service import graph_service

router = APIRouter(prefix="/circles", tags=["circles"])

class CircleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    tagline: str = Field(default="", max_length=255)
    description: str = Field(min_length=5, max_length=3000)
    category: str = "Technology"
    tags: str = ""
    max_members: int = Field(default=25, ge=2, le=100)
    is_private: bool = False
    image_url: str | None = None

class DiscussionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=3, max_length=5000)

class ReplyCreate(BaseModel):
    content: str = Field(min_length=1, max_length=3000)

class ActivityCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    activity_type: str = "discussion"
    scheduled_at: datetime
    location_or_link: str = "Online"

def serialize_circle(circle: InterestCircle, user: User | None, db: Session) -> dict:
    mem_count = len(circle.memberships)
    is_mem = False
    is_admin = False
    if user:
        m = next((m for m in circle.memberships if m.user_id == user.id), None)
        if m:
            is_mem = True
            is_admin = (m.role == "admin" or circle.created_by_id == user.id)

    return {
        "id": circle.id,
        "name": circle.name,
        "tagline": circle.tagline,
        "description": circle.description,
        "category": circle.category,
        "tags": [t.strip() for t in circle.tags.split(",") if t.strip()],
        "max_members": circle.max_members,
        "member_count": mem_count,
        "is_private": circle.is_private,
        "image_url": circle.image_url,
        "created_by_id": circle.created_by_id,
        "creator_name": circle.creator.name if circle.creator else "ALIGN Member",
        "is_member": is_mem,
        "is_admin": is_admin,
        "discussions_count": len(circle.discussions),
        "activities_count": len(circle.activities),
        "created_at": circle.created_at,
    }

@router.get("")
def list_circles(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    stmt = select(InterestCircle).order_by(InterestCircle.created_at.desc())
    if category:
        stmt = stmt.where(InterestCircle.category.ilike(f"%{category.strip()}%"))
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                InterestCircle.name.ilike(term),
                InterestCircle.tagline.ilike(term),
                InterestCircle.description.ilike(term),
                InterestCircle.tags.ilike(term),
            )
        )
    stmt = stmt.limit(limit)
    circles = list(db.scalars(stmt))
    return [serialize_circle(c, user, db) for c in circles]

@router.post("", status_code=status.HTTP_201_CREATED)
def create_circle(
    payload: CircleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ctx = f"{payload.name} {payload.tagline} {payload.description} {payload.category} {payload.tags}"
    emb = generate_embedding(ctx)

    circle = InterestCircle(
        name=payload.name.strip(),
        tagline=payload.tagline.strip(),
        description=payload.description.strip(),
        category=payload.category,
        tags=payload.tags,
        max_members=payload.max_members,
        is_private=payload.is_private,
        image_url=payload.image_url,
        created_by_id=user.id,
        embedding=emb,
    )
    db.add(circle)
    db.flush()

    # Creator membership
    mem = CircleMembership(user_id=user.id, circle_id=circle.id, role="admin")
    db.add(mem)

    # Award XP & Badge
    award_xp(db, user.id, "circle_created", 75, f"Founded Interest Circle: {circle.name[:30]}")
    game = get_or_create_gamification(db, user.id)
    check_and_unlock_badge(db, game, "PIONEER")

    db.commit()
    db.refresh(circle)
    return serialize_circle(circle, user, db)

@router.get("/{circle_id}")
def get_circle_details(
    circle_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    circle = db.get(InterestCircle, circle_id)
    if not circle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found")

    data = serialize_circle(circle, user, db)
    data["members"] = [
        {
            "id": m.user.id,
            "name": m.user.name,
            "avatar_url": m.user.profile.avatar_url if m.user.profile else None,
            "skills": m.user.profile.skills if m.user.profile else "",
            "role": m.role,
            "joined_at": m.joined_at,
        }
        for m in circle.memberships
    ]
    return data

@router.post("/{circle_id}/join")
def join_circle(
    circle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    circle = db.get(InterestCircle, circle_id)
    if not circle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found")

    existing = db.scalar(
        select(CircleMembership).where(
            (CircleMembership.circle_id == circle_id) & (CircleMembership.user_id == user.id)
        )
    )
    if existing:
        return {"status": "ok", "message": "You are already a member of this Circle."}

    if len(circle.memberships) >= circle.max_members:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Circle has reached its capacity limit.")

    mem = CircleMembership(user_id=user.id, circle_id=circle.id, role="member")
    db.add(mem)
    award_xp(db, user.id, "circle_joined", 25, f"Joined Interest Circle: {circle.name[:30]}")
    db.commit()

    return {"status": "ok", "message": f"Successfully joined {circle.name}!"}

@router.post("/{circle_id}/leave")
def leave_circle(
    circle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mem = db.scalar(
        select(CircleMembership).where(
            (CircleMembership.circle_id == circle_id) & (CircleMembership.user_id == user.id)
        )
    )
    if not mem:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not a member of this Circle.")

    db.delete(mem)
    db.commit()
    return {"status": "ok", "message": "Left Circle successfully."}

@router.get("/{circle_id}/discussions")
def list_discussions(
    circle_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    discs = list(
        db.scalars(
            select(CircleDiscussion)
            .where(CircleDiscussion.circle_id == circle_id)
            .order_by(CircleDiscussion.created_at.desc())
        )
    )
    return [
        {
            "id": d.id,
            "title": d.title,
            "content": d.content,
            "author_id": d.author_id,
            "author_name": d.author.name if d.author else "ALIGN Member",
            "author_avatar": d.author.profile.avatar_url if (d.author and d.author.profile) else None,
            "created_at": d.created_at,
            "replies_count": len(d.replies),
        }
        for d in discs
    ]

@router.post("/{circle_id}/discussions", status_code=status.HTTP_201_CREATED)
def create_discussion(
    circle_id: int,
    payload: DiscussionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    circle = db.get(InterestCircle, circle_id)
    if not circle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found")

    if circle.is_private:
        is_member = (db.scalar(
            select(func.count(CircleMembership.id)).where(
                CircleMembership.circle_id == circle.id,
                CircleMembership.user_id == user.id,
            )
        ) or 0) > 0
        if not (is_member or user.is_admin or circle.created_by_id == user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a member of this private circle to start discussions."
            )

    disc = CircleDiscussion(
        circle_id=circle.id,
        author_id=user.id,
        title=payload.title.strip(),
        content=payload.content.strip(),
    )
    db.add(disc)
    award_xp(db, user.id, "discussion_started", 15, f"Started discussion in {circle.name[:25]}")
    db.commit()
    db.refresh(disc)
    return {
        "id": disc.id,
        "title": disc.title,
        "content": disc.content,
        "author_name": user.name,
        "created_at": disc.created_at,
        "replies_count": 0,
    }

@router.get("/{circle_id}/discussions/{disc_id}/replies")
def get_discussion_replies(
    circle_id: int,
    disc_id: int,
    db: Session = Depends(get_db),
):
    disc = db.get(CircleDiscussion, disc_id)
    if not disc or disc.circle_id != circle_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")

    return [
        {
            "id": r.id,
            "content": r.content,
            "author_id": r.author_id,
            "author_name": r.author.name if r.author else "ALIGN Member",
            "author_avatar": r.author.profile.avatar_url if (r.author and r.author.profile) else None,
            "created_at": r.created_at,
        }
        for r in disc.replies
    ]

@router.post("/{circle_id}/discussions/{disc_id}/replies", status_code=status.HTTP_201_CREATED)
def post_discussion_reply(
    circle_id: int,
    disc_id: int,
    payload: ReplyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    disc = db.get(CircleDiscussion, disc_id)
    if not disc or disc.circle_id != circle_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")

    circle = disc.circle
    if circle and circle.is_private:
        is_member = (db.scalar(
            select(func.count(CircleMembership.id)).where(
                CircleMembership.circle_id == circle.id,
                CircleMembership.user_id == user.id,
            )
        ) or 0) > 0
        if not (is_member or user.is_admin or circle.created_by_id == user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a member of this private circle to reply to discussions."
            )

    reply = CircleDiscussionReply(
        discussion_id=disc.id,
        author_id=user.id,
        content=payload.content.strip(),
    )
    db.add(reply)
    award_xp(db, user.id, "discussion_reply", 5, "Replied in circle discussion")
    db.commit()
    db.refresh(reply)
    return {
        "id": reply.id,
        "content": reply.content,
        "author_id": user.id,
        "author_name": user.name,
        "author_avatar": user.profile.avatar_url if user.profile else None,
        "created_at": reply.created_at,
    }

@router.get("/{circle_id}/activities")
def list_activities(
    circle_id: int,
    db: Session = Depends(get_db),
):
    acts = list(
        db.scalars(
            select(CircleActivity)
            .where(CircleActivity.circle_id == circle_id)
            .order_by(CircleActivity.scheduled_at.asc())
        )
    )
    return [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "activity_type": a.activity_type,
            "scheduled_at": a.scheduled_at,
            "location_or_link": a.location_or_link,
            "creator_name": a.creator.name if a.creator else "Member",
            "created_at": a.created_at,
        }
        for a in acts
    ]

@router.post("/{circle_id}/activities", status_code=status.HTTP_201_CREATED)
def schedule_activity(
    circle_id: int,
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    circle = db.get(InterestCircle, circle_id)
    if not circle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found")

    act = CircleActivity(
        circle_id=circle.id,
        creator_id=user.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        activity_type=payload.activity_type,
        scheduled_at=payload.scheduled_at,
        location_or_link=payload.location_or_link.strip(),
    )
    db.add(act)
    award_xp(db, user.id, "activity_scheduled", 30, f"Scheduled activity in {circle.name[:25]}")
    db.commit()
    db.refresh(act)
    return {
        "id": act.id,
        "title": act.title,
        "scheduled_at": act.scheduled_at,
        "location_or_link": act.location_or_link,
        "activity_type": act.activity_type,
    }
