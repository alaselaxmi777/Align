import html
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, desc, or_, and_
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.user import User, UserBlock
from app.models.reel import Reel, ReelLike, ReelComment
from app.models.connection import UserConnection
from app.models.notification import Notification
from app.models.message import Message
from app.schemas.social import ShareRequest
from app.services.embeddings import generate_embedding
from app.services.quota_service import enforce_daily_upload_quota
from app.services.storage_service import storage_service
from app.services.mention_service import notify_mentions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reels", tags=["reels"])

def get_connected_user_ids(db: Session, user_id: int) -> set[int]:
    s1 = set(db.scalars(select(UserConnection.receiver_id).where(UserConnection.sender_id == user_id, UserConnection.status == "accepted")).all())
    s2 = set(db.scalars(select(UserConnection.sender_id).where(UserConnection.receiver_id == user_id, UserConnection.status == "accepted")).all())
    return s1 | s2

class ReelCommentResponse(BaseModel):
    id: int
    reel_id: int
    user_id: int
    user_name: str
    user_avatar: Optional[str] = None
    content: str
    parent_id: Optional[int] = None
    replies: list["ReelCommentResponse"] = Field(default_factory=list)
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ReelCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    parent_id: Optional[int] = None

class ReelResponse(BaseModel):
    id: int
    title: str
    author_id: int
    author_name: str
    author_avatar: Optional[str] = None
    category: str
    video_url: str
    thumbnail_url: str
    views_count: str
    likes_count: int
    comments_count: int
    duration_seconds: Optional[float] = None
    visibility: str = "public"
    audio_track: Optional[str] = None
    caption: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    is_liked: bool = False
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ReelCreate(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    category: str = Field(default="Technology")
    video_url: str
    thumbnail_url: str
    duration_seconds: Optional[float] = Field(default=None, ge=0.0, le=90.0)
    visibility: str = Field(default="public", pattern="^(public|connections_only)$")
    audio_track: Optional[str] = None
    caption: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

def _format_views(count: int) -> str:
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    elif count == 1:
        return "1 view"
    else:
        return f"{count} views"

def _serialize_reel(reel: Reel, user_id: Optional[int], db: Session) -> ReelResponse:
    likes_count = db.scalar(select(func.count(ReelLike.id)).where(ReelLike.reel_id == reel.id)) or 0
    comments_count = db.scalar(select(func.count(ReelComment.id)).where(ReelComment.reel_id == reel.id)) or 0
    is_liked = False
    if user_id:
        is_liked = (db.scalar(select(func.count(ReelLike.id)).where(
            ReelLike.reel_id == reel.id, ReelLike.user_id == user_id
        )) or 0) > 0

    tags_list = [t.strip() for t in reel.tags.split(",") if t.strip()] if reel.tags else []

    return ReelResponse(
        id=reel.id,
        title=reel.title,
        author_id=reel.author_id,
        author_name=reel.author_name,
        author_avatar=reel.author_avatar,
        category=reel.category,
        video_url=reel.video_url,
        thumbnail_url=reel.thumbnail_url,
        views_count=_format_views(reel.views_count),
        likes_count=likes_count,
        comments_count=comments_count,
        duration_seconds=reel.duration_seconds,
        visibility=reel.visibility,
        audio_track=reel.audio_track,
        caption=reel.caption,
        tags=tags_list,
        is_liked=is_liked,
        created_at=reel.created_at,
    )

@router.get("", response_model=list[ReelResponse])
def get_reels(
    category: Optional[str] = None,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    stmt = select(Reel)
    if not user or getattr(user, "role", "user") != "admin":
        stmt = stmt.where(Reel.is_hidden == False)

    # Privacy filtering: public reels visible to all; connections_only only visible to author and accepted connections
    if not user:
        stmt = stmt.where(Reel.visibility == "public")
    else:
        connected_ids = get_connected_user_ids(db, user.id)
        allowed_authors = connected_ids | {user.id}
        stmt = stmt.where(
            or_(
                Reel.visibility == "public",
                and_(Reel.visibility == "connections_only", Reel.author_id.in_(allowed_authors)),
            )
        )

    if category and category.strip().lower() != "all":
        stmt = stmt.where(Reel.category.ilike(f"%{category.strip()}%"))

    stmt = stmt.order_by(desc(Reel.created_at)).limit(limit)
    reels = list(db.scalars(stmt))

    uid = user.id if user else None
    return [_serialize_reel(r, uid, db) for r in reels]

@router.post("", response_model=ReelResponse, status_code=status.HTTP_201_CREATED)
def create_reel(
    payload: ReelCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Enforce daily upload quota (20 posts/reels per user per day)
    enforce_daily_upload_quota(db, user.id)

    if payload.duration_seconds is not None and payload.duration_seconds > 90.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reel duration cannot exceed 90 seconds.",
        )

    avatar = user.profile.avatar_url if user.profile else None
    tags_str = ",".join(t.strip() for t in payload.tags if t.strip())

    embed_text = f"{payload.title} {payload.category} {payload.caption or ''} {tags_str}".strip()
    embedding = None
    try:
        embedding = generate_embedding(embed_text)
    except Exception as exc:
        logger.warning(f"Could not compute embedding for reel '{payload.title}': {exc}")

    reel = Reel(
        title=payload.title.strip(),
        category=payload.category.strip() or "Technology",
        video_url=payload.video_url.strip(),
        thumbnail_url=payload.thumbnail_url.strip(),
        duration_seconds=payload.duration_seconds,
        visibility=payload.visibility,
        embedding=embedding,
        author_id=user.id,
        author_name=user.name,
        author_avatar=avatar,
        caption=html.escape(payload.caption.strip()) if payload.caption else None,
        audio_track=payload.audio_track.strip() if payload.audio_track else f"Original Audio · {user.name}",
        tags=tags_str,
        views_count=0,
    )
    db.add(reel)

    # Dispatched mention notifications
    notify_mentions(db, user, f"{payload.title} {payload.caption or ''}", "reel", reel.id, f"/reels?id={reel.id}")

    db.commit()
    db.refresh(reel)

    return _serialize_reel(reel, user.id, db)

@router.post("/{reel_id}/view")
def record_reel_view(
    reel_id: int,
    db: Session = Depends(get_db),
):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    reel.views_count = (reel.views_count or 0) + 1
    db.commit()
    db.refresh(reel)
    return {
        "status": "ok",
        "reel_id": reel.id,
        "views_count": reel.views_count,
        "formatted_views": _format_views(reel.views_count),
    }

@router.post("/{reel_id}/like")
def toggle_reel_like(
    reel_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    existing_like = db.scalar(
        select(ReelLike).where(ReelLike.reel_id == reel_id, ReelLike.user_id == user.id)
    )

    if existing_like:
        db.delete(existing_like)
        is_liked = False
    else:
        new_like = ReelLike(reel_id=reel_id, user_id=user.id)
        db.add(new_like)
        is_liked = True

    db.commit()

    total_likes = db.scalar(select(func.count(ReelLike.id)).where(ReelLike.reel_id == reel_id)) or 0
    return {
        "status": "ok",
        "reel_id": reel_id,
        "is_liked": is_liked,
        "likes_count": total_likes,
    }

@router.get("/{reel_id}/comments", response_model=list[ReelCommentResponse])
def get_reel_comments(
    reel_id: int,
    db: Session = Depends(get_db),
):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    all_comments = list(
        db.scalars(
            select(ReelComment)
            .where(ReelComment.reel_id == reel_id)
            .order_by(ReelComment.created_at.asc())
        )
    )

    # Build 1-level reply tree
    top_level: list[ReelCommentResponse] = []
    replies_map: dict[int, list[ReelCommentResponse]] = {}

    for c in all_comments:
        avatar = c.user.profile.avatar_url if c.user and c.user.profile else None
        item = ReelCommentResponse(
            id=c.id,
            reel_id=c.reel_id,
            user_id=c.user_id,
            user_name=c.user.name if c.user else "Community Member",
            user_avatar=avatar,
            content=c.content,
            parent_id=c.parent_id,
            created_at=c.created_at,
            replies=[],
        )
        if c.parent_id is None:
            top_level.append(item)
        else:
            replies_map.setdefault(c.parent_id, []).append(item)

    for item in top_level:
        item.replies = replies_map.get(item.id, [])

    return top_level

@router.post("/{reel_id}/comments", response_model=ReelCommentResponse, status_code=status.HTTP_201_CREATED)
def add_reel_comment(
    reel_id: int,
    payload: ReelCommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    effective_parent_id = None
    if payload.parent_id:
        parent = db.get(ReelComment, payload.parent_id)
        if not parent or parent.reel_id != reel_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found")
        # Enforce 1-level nesting: flatten reply to reply to top-level parent
        effective_parent_id = parent.parent_id if parent.parent_id is not None else parent.id

    comment = ReelComment(
        reel_id=reel_id,
        user_id=user.id,
        content=html.escape(payload.content.strip()),
        parent_id=effective_parent_id,
    )
    db.add(comment)

    # Notify reel author if not current user
    if reel.author_id != user.id:
        notif = Notification(
            user_id=reel.author_id,
            title="New Comment on Your Reel",
            message=f"{user.name} commented on your reel: \"{payload.content[:40]}...\"",
            link=f"/reels?id={reel_id}",
        )
        db.add(notif)

    # Notify parent comment author if reply and not current user and not reel author
    if effective_parent_id:
        parent_comm = db.get(ReelComment, effective_parent_id)
        if parent_comm and parent_comm.user_id != user.id and parent_comm.user_id != reel.author_id:
            notif_reply = Notification(
                user_id=parent_comm.user_id,
                title="New Reply to Your Reel Comment",
                message=f"{user.name} replied to your reel comment: \"{payload.content[:40]}...\"",
                link=f"/reels?id={reel_id}",
            )
            db.add(notif_reply)

    # Dispatched mention notifications
    notify_mentions(db, user, payload.content, "reel comment", reel_id, f"/reels?id={reel_id}")

    db.commit()
    db.refresh(comment)

    avatar = user.profile.avatar_url if user.profile else None
    return ReelCommentResponse(
        id=comment.id,
        reel_id=comment.reel_id,
        user_id=comment.user_id,
        user_name=user.name,
        user_avatar=avatar,
        content=comment.content,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
        replies=[],
    )

@router.post("/{reel_id}/share")
def share_reel_to_dm(
    reel_id: int,
    payload: ShareRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    if payload.recipient_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share a reel with yourself.")

    recipient = db.get(User, payload.recipient_id)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient user not found.")

    # Blocking check
    is_blocked = (db.scalar(
        select(func.count(UserBlock.id)).where(
            or_(
                (UserBlock.blocker_id == user.id) & (UserBlock.blocked_user_id == payload.recipient_id),
                (UserBlock.blocker_id == payload.recipient_id) & (UserBlock.blocked_user_id == user.id),
            )
        )
    ) or 0) > 0
    if is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot message this user.")

    # Privacy check: If connections_only, ensure sender and recipient are connected
    if reel.visibility == "connections_only":
        connected = get_connected_user_ids(db, user.id)
        if payload.recipient_id not in connected:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot share a connections-only reel with someone who is not your connection.",
            )

    snippet = reel.title[:80].replace("\n", " ").strip()
    if payload.note and payload.note.strip():
        msg_text = f"{payload.note.strip()}\n\n🎬 Shared reel: \"{snippet}\"\n/reels?id={reel.id}"
    else:
        msg_text = f"🎬 Shared a reel: \"{snippet}\"\n/reels?id={reel.id}"

    msg = Message(
        sender_id=user.id,
        receiver_id=payload.recipient_id,
        content=msg_text,
    )
    db.add(msg)

    notif = Notification(
        user_id=payload.recipient_id,
        title=f"{user.name} shared a reel with you",
        message=f"{user.name} sent you a reel in direct messages.",
        link=f"/messages?other_user_id={user.id}",
    )
    db.add(notif)
    db.commit()

    return {"status": "ok", "reel_id": reel.id, "message_id": msg.id, "recipient_id": payload.recipient_id}

class EditReelRequest(BaseModel):
    caption: str = Field(..., min_length=1, max_length=500)

@router.put("/{reel_id}", response_model=ReelResponse)
def edit_reel(
    reel_id: int,
    payload: EditReelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    if reel.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this reel")

    reel.caption = html.escape(payload.caption.strip())
    db.commit()
    db.refresh(reel)
    return _serialize_reel(reel, user.id, db)

@router.delete("/{reel_id}", status_code=status.HTTP_200_OK)
def delete_reel(
    reel_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reel = db.get(Reel, reel_id)
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    if reel.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this reel")

    # Clean up video and poster thumbnail from storage bucket
    if reel.video_url:
        storage_service.delete_file(reel.video_url)
    if reel.thumbnail_url:
        storage_service.delete_file(reel.thumbnail_url)

    db.delete(reel)
    db.commit()
    return {"status": "ok", "message": "Reel deleted successfully"}
