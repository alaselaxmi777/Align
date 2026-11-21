import html
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.post import Post, PostLike, PostComment, PostMedia
from app.models.user import User
from app.models.connection import UserConnection
from app.models.community import Community
from app.models.notification import Notification
from app.schemas.social import (
    PostCreate,
    PostResponse,
    PostAuthor,
    PostMediaItem,
    CommentCreate,
    CommentResponse,
    ShareRequest,
)
from app.services.embeddings import generate_embedding
from app.services.quota_service import enforce_daily_upload_quota
from app.services.mention_service import notify_mentions
from app.services.storage_service import storage_service
from app.services.feed_ranker import (
    rank_feed_posts,
    score_and_rank_post,
    get_user_graph_context,
)
from app.models.message import Message
from app.models.user import UserBlock

router = APIRouter(prefix="/feed", tags=["feed"])

def get_connected_user_ids(db: Session, user_id: int) -> set[int]:
    s1 = set(db.scalars(select(UserConnection.receiver_id).where(UserConnection.sender_id == user_id, UserConnection.status == "accepted")).all())
    s2 = set(db.scalars(select(UserConnection.sender_id).where(UserConnection.receiver_id == user_id, UserConnection.status == "accepted")).all())
    return s1 | s2

def serialize_post(
    p: Post,
    user: User | None,
    db: Session,
    score: float | None = None,
    score_breakdown: dict[str, float] | None = None,
    why_recommended: str | None = None,
) -> PostResponse:
    author_data = None
    if p.author:
        author_data = PostAuthor(
            id=p.author.id,
            name=p.author.name,
            avatar_url=p.author.profile.avatar_url if p.author.profile else None,
        )
    comm_name = p.community.name if p.community else None

    likes_count = db.scalar(select(func.count(PostLike.id)).where(PostLike.post_id == p.id)) or 0
    comments_count = db.scalar(select(func.count(PostComment.id)).where(PostComment.post_id == p.id)) or 0

    is_liked = False
    if user:
        is_liked = (db.scalar(select(func.count(PostLike.id)).where(PostLike.post_id == p.id, PostLike.user_id == user.id)) or 0) > 0

    media_items = [
        PostMediaItem(
            id=m.id,
            position=m.position,
            media_type=m.media_type,
            original_url=m.original_url,
            feed_url=m.feed_url,
            thumbnail_url=m.thumbnail_url,
            width=m.width,
            height=m.height,
            alt_text=m.alt_text,
        )
        for m in p.media
    ]

    return PostResponse(
        id=p.id,
        author_id=p.author_id,
        community_id=p.community_id,
        content=p.content,
        image_url=p.image_url or (media_items[0].feed_url if media_items else None),
        visibility=p.visibility,
        location_area=p.location_area,
        is_pinned=p.is_pinned,
        media=media_items,
        created_at=p.created_at,
        author=author_data,
        community_name=comm_name,
        likes_count=likes_count,
        comments_count=comments_count,
        is_liked=is_liked,
        score=score,
        score_breakdown=score_breakdown,
        why_recommended=why_recommended,
    )

@router.get("", response_model=list[PostResponse])
def get_feed(
    community_id: int | None = None,
    author_id: int | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    stmt = select(Post).join(User, Post.author_id == User.id).where(User.is_test == False)
    if not user or getattr(user, "role", "user") != "admin":
        stmt = stmt.where(Post.is_hidden == False)
    if community_id is not None:
        stmt = stmt.where(Post.community_id == community_id)
    if author_id is not None:
        stmt = stmt.where(Post.author_id == author_id)

    # Privacy and visibility filter
    if not user:
        stmt = stmt.where(Post.visibility == "public")
    elif getattr(user, "role", "user") != "admin":
        connected_ids = get_connected_user_ids(db, user.id)
        allowed_authors = connected_ids | {user.id}
        stmt = stmt.where(
            or_(
                Post.visibility == "public",
                Post.author_id.in_(allowed_authors),
            )
        )

    # Candidate pool: up to 100 posts for ranking
    candidate_limit = max(limit * 2, 60)
    stmt = stmt.order_by(desc(Post.created_at)).limit(candidate_limit)
    candidates = list(db.scalars(stmt))

    # Apply 6-factor hybrid ranker with SHAP attributions
    ranked_tuples = rank_feed_posts(candidates, user, db)

    # Slice to requested limit and serialize
    result = []
    for p, score, breakdown, why in ranked_tuples[:limit]:
        result.append(serialize_post(p, user, db, score=score, score_breakdown=breakdown, why_recommended=why))
    return result

@router.get("/{post_id}", response_model=PostResponse)
def get_post_detail(
    post_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    post = db.get(Post, post_id)
    if not post or (post.author and post.author.is_test):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.is_hidden and (not user or getattr(user, "role", "user") != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Enforce connection privacy
    if post.visibility == "connections_only":
        if not user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This post is visible to connections only.")
        if user.id != post.author_id and getattr(user, "role", "user") != "admin":
            connected_ids = get_connected_user_ids(db, user.id)
            if post.author_id not in connected_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This post is visible to connections only.")

    score, breakdown, why = None, None, None
    if user:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        connected_ids, peer_ids = get_user_graph_context(db, user.id)
        score, breakdown, why = score_and_rank_post(post, user, connected_ids, peer_ids, now, db)

    return serialize_post(post, user, db, score=score, score_breakdown=breakdown, why_recommended=why)

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Enforce daily upload quota (20 posts/reels per user per day)
    enforce_daily_upload_quota(db, user.id)

    if payload.community_id:
        comm = db.get(Community, payload.community_id)
        if not comm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")

    # Compute multilingual semantic embedding for caption
    caption_text = f"{payload.content.strip()} {payload.location_area or ''}".strip()
    embedding_vec = generate_embedding(caption_text)

    # Primary image fallback
    primary_image_url = payload.image_url
    if not primary_image_url and payload.media_items:
        primary_image_url = payload.media_items[0].feed_url

    clean_content = html.escape(payload.content.strip())
    new_post = Post(
        author_id=user.id,
        community_id=payload.community_id,
        content=clean_content,
        image_url=primary_image_url,
        visibility=payload.visibility,
        location_area=payload.location_area.strip() if payload.location_area else None,
        embedding=embedding_vec,
    )
    db.add(new_post)
    db.flush()

    # Save multi-image carousel items
    for idx, item in enumerate(payload.media_items):
        media_entry = PostMedia(
            post_id=new_post.id,
            position=idx,
            media_type=item.media_type,
            original_url=item.original_url,
            feed_url=item.feed_url,
            thumbnail_url=item.thumbnail_url,
            width=item.width,
            height=item.height,
            alt_text=item.alt_text,
        )
        db.add(media_entry)

    # Dispatched mention notifications
    notify_mentions(db, user, payload.content, "post", new_post.id, f"/feed?post={new_post.id}")

    db.commit()
    db.refresh(new_post)
    return serialize_post(new_post, user, db)

@router.post("/{post_id}/like")
def toggle_like(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing_like = db.scalar(
        select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user.id)
    )

    if existing_like:
        db.delete(existing_like)
        db.commit()
        is_liked = False
    else:
        new_like = PostLike(post_id=post_id, user_id=user.id)
        db.add(new_like)
        if post.author_id != user.id:
            notif = Notification(
                user_id=post.author_id,
                title="New Like on Your Post",
                message=f"{user.name} liked your update.",
                link="/feed",
            )
            db.add(notif)
        db.commit()
        is_liked = True

    count = db.scalar(select(func.count(PostLike.id)).where(PostLike.post_id == post_id)) or 0
    return {"status": "ok", "is_liked": is_liked, "likes_count": count}

@router.get("/{post_id}/comments", response_model=list[CommentResponse])
def get_comments(post_id: int, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    all_comments = list(db.scalars(
        select(PostComment).where(PostComment.post_id == post_id).order_by(PostComment.created_at.asc())
    ))

    # Build 1-level reply tree
    top_level: list[CommentResponse] = []
    replies_map: dict[int, list[CommentResponse]] = {}

    for c in all_comments:
        author_name = c.author.name if c.author else "ALIGN Member"
        author_avatar = c.author.profile.avatar_url if (c.author and c.author.profile) else None
        item = CommentResponse(
            id=c.id,
            post_id=c.post_id,
            author_id=c.author_id,
            content=c.content,
            parent_id=c.parent_id,
            created_at=c.created_at,
            author_name=author_name,
            author_avatar=author_avatar,
            replies=[],
        )
        if c.parent_id is None:
            top_level.append(item)
        else:
            replies_map.setdefault(c.parent_id, []).append(item)

    for item in top_level:
        item.replies = replies_map.get(item.id, [])

    return top_level

@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    post_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    effective_parent_id = None
    if payload.parent_id:
        parent = db.get(PostComment, payload.parent_id)
        if not parent or parent.post_id != post_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found")
        # Enforce 1-level nesting: flatten reply to reply to top-level parent
        effective_parent_id = parent.parent_id if parent.parent_id is not None else parent.id

    clean_comment = html.escape(payload.content.strip())
    comment = PostComment(
        post_id=post_id,
        author_id=user.id,
        content=clean_comment,
        parent_id=effective_parent_id,
    )
    db.add(comment)

    # Notify post author if not current user
    if post.author_id != user.id:
        notif = Notification(
            user_id=post.author_id,
            title="New Comment on Your Post",
            message=f"{user.name} commented: \"{payload.content[:40]}...\"",
            link=f"/feed?post={post_id}",
        )
        db.add(notif)

    # Notify parent comment author if not current user and not post author
    if effective_parent_id:
        parent_comm = db.get(PostComment, effective_parent_id)
        if parent_comm and parent_comm.author_id != user.id and parent_comm.author_id != post.author_id:
            notif_reply = Notification(
                user_id=parent_comm.author_id,
                title="New Reply to Your Comment",
                message=f"{user.name} replied to your comment: \"{payload.content[:40]}...\"",
                link=f"/feed?post={post_id}",
            )
            db.add(notif_reply)

    # Dispatched mention notifications
    notify_mentions(db, user, payload.content, "comment", post_id, f"/feed?post={post_id}")

    db.commit()
    db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author_id=comment.author_id,
        content=comment.content,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
        author_name=user.name,
        author_avatar=user.profile.avatar_url if user.profile else None,
        replies=[],
    )

@router.post("/{post_id}/pin")
def toggle_pin_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only pin your own posts.")

    if post.is_pinned:
        post.is_pinned = False
        db.commit()
        return {"status": "ok", "post_id": post.id, "is_pinned": False, "message": "Post unpinned from profile."}

    # Check pin count limit (max 3)
    pinned_count = db.scalar(
        select(func.count(Post.id)).where(Post.author_id == user.id, Post.is_pinned == True)
    ) or 0
    if pinned_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only pin up to 3 posts to your profile. Please unpin an existing post first.",
        )

    post.is_pinned = True
    db.commit()
    return {"status": "ok", "post_id": post.id, "is_pinned": True, "message": "Post pinned to profile."}

@router.post("/{post_id}/share")
def share_post_to_dm(
    post_id: int,
    payload: ShareRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if payload.recipient_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share a post with yourself.")

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
    if post.visibility == "connections_only":
        connected = get_connected_user_ids(db, user.id)
        if payload.recipient_id not in connected:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot share a connections-only post with someone who is not your connection.",
            )

    snippet = post.content[:80].replace("\n", " ").strip()
    if payload.note and payload.note.strip():
        msg_text = f"{payload.note.strip()}\n\n🔗 Shared post: \"{snippet}\"\n/feed?post={post.id}"
    else:
        msg_text = f"🔗 Shared a post: \"{snippet}\"\n/feed?post={post.id}"

    msg = Message(
        sender_id=user.id,
        receiver_id=payload.recipient_id,
        content=msg_text,
    )
    db.add(msg)

    notif = Notification(
        user_id=payload.recipient_id,
        title=f"{user.name} shared a post with you",
        message=f"{user.name} sent you a post in direct messages.",
        link=f"/messages?other_user_id={user.id}",
    )
    db.add(notif)
    db.commit()

    return {"status": "ok", "post_id": post.id, "message_id": msg.id, "recipient_id": payload.recipient_id}

class EditPostRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    visibility: Optional[str] = None

@router.put("/{post_id}", response_model=PostResponse)
def edit_post(
    post_id: int,
    payload: EditPostRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post or (post.is_hidden and not user.is_admin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    if post.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own posts.")

    post.content = html.escape(payload.content.strip())
    if payload.visibility in {"public", "connections_only"}:
        post.visibility = payload.visibility

    try:
        from app.services.embeddings import generate_embedding
        post.embedding = generate_embedding(post.content)
    except Exception as exc:
        pass

    db.commit()
    db.refresh(post)
    return serialize_post(post, user, db)

@router.delete("/{post_id}", status_code=status.HTTP_200_OK)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    if post.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own posts.")

    # Clean up associated media files from cloud storage bucket
    for m in post.media:
        if m.original_url:
            storage_service.delete_file(m.original_url)
        if m.feed_url:
            storage_service.delete_file(m.feed_url)
        if m.thumbnail_url:
            storage_service.delete_file(m.thumbnail_url)
    if post.image_url:
        storage_service.delete_file(post.image_url)

    db.delete(post)
    db.commit()
    return {"status": "ok", "message": "Post deleted successfully."}
