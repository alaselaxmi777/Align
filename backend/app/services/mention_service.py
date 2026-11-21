import re
import logging
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.notification import Notification

logger = logging.getLogger(__name__)

MENTION_REGEX = re.compile(r"@([a-zA-Z0-9_]{2,30})")

def extract_mentions(text: str | None) -> list[str]:
    """Extracts unique mention handles (without '@') from text."""
    if not text:
        return []
    matches = MENTION_REGEX.findall(text)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for m in matches:
        low = m.lower()
        if low not in seen:
            seen.add(low)
            result.append(m)
    return result

def notify_mentions(
    db: Session,
    sender: User,
    text: str | None,
    item_type: str,
    item_id: int,
    link: str,
) -> list[Notification]:
    """
    Parses @mentions from text, resolves targeted users, and dispatches in-app notifications.
    """
    handles = extract_mentions(text)
    if not handles:
        return []

    notifications = []
    for handle in handles:
        clean_handle = handle.strip()
        # Find user by prefix or full match on name, or email prefix
        stmt = (
            select(User)
            .where(
                or_(
                    User.name.ilike(f"{clean_handle}%"),
                    User.name.ilike(f"%{clean_handle}%"),
                    User.email.ilike(f"{clean_handle}@%"),
                ),
                User.id != sender.id,
            )
            .limit(1)
        )
        target = db.scalar(stmt)
        if target:
            clean_excerpt = (text or "").replace("\n", " ").strip()
            if len(clean_excerpt) > 75:
                clean_excerpt = clean_excerpt[:72] + "..."

            notif = Notification(
                user_id=target.id,
                title=f"{sender.name} mentioned you",
                message=f"{sender.name} mentioned you in a {item_type}: \"{clean_excerpt}\"",
                link=link,
                is_read=False,
            )
            db.add(notif)
            notifications.append(notif)
            logger.info(f"Dispatched mention notification from User {sender.id} to User {target.id}")

    return notifications
