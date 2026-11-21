from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.post import Post
from app.models.reel import Reel

DAILY_UPLOAD_LIMIT = 20

def get_today_upload_count(db: Session, user_id: int) -> int:
    """Calculates number of posts and reels uploaded by the user today (UTC)."""
    now = datetime.now(timezone.utc)
    start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)

    posts_today = db.scalar(
        select(func.count(Post.id)).where(
            Post.author_id == user_id,
            Post.created_at >= start_of_day,
        )
    ) or 0

    reels_today = db.scalar(
        select(func.count(Reel.id)).where(
            Reel.author_id == user_id,
            Reel.created_at >= start_of_day,
        )
    ) or 0

    return posts_today + reels_today

def enforce_daily_upload_quota(db: Session, user_id: int) -> int:
    """
    Enforces the 20 posts/reels per user per day quota.
    Raises HTTP 429 if limit is reached.
    """
    count = get_today_upload_count(db, user_id)
    if count >= DAILY_UPLOAD_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily upload quota exceeded ({count}/{DAILY_UPLOAD_LIMIT}). You can create up to {DAILY_UPLOAD_LIMIT} posts or reels per day.",
        )
    return count
