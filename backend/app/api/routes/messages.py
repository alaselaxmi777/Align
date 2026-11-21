from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.message import Message
from app.models.user import User, UserBlock
from app.models.notification import Notification
from app.schemas.social import MessageCreate, MessageResponse

router = APIRouter(prefix="/messages", tags=["messages"])

@router.get("/conversations")
def get_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Returns list of distinct conversation threads with partners, latest message snippet,
    timestamp, and unread message count.
    """
    # Fetch all messages involving the user ordered latest first
    all_msgs = list(db.scalars(
        select(Message)
        .where(or_(Message.sender_id == user.id, Message.receiver_id == user.id))
        .order_by(desc(Message.created_at))
    ))

    conversations: dict[int, dict] = {}
    for m in all_msgs:
        partner_id = m.receiver_id if m.sender_id == user.id else m.sender_id
        if partner_id not in conversations:
            partner = m.receiver if m.sender_id == user.id else m.sender
            conversations[partner_id] = {
                "partner_id": partner_id,
                "partner_name": partner.name if partner else "ALIGN Member",
                "partner_avatar": partner.profile.avatar_url if (partner and partner.profile) else None,
                "last_message": m.content,
                "last_message_at": m.created_at,
                "unread_count": 0,
            }

        # Count unread if current user is receiver
        if m.receiver_id == user.id and not m.is_read:
            conversations[partner_id]["unread_count"] += 1

    return list(conversations.values())

@router.get("", response_model=list[MessageResponse])
def get_messages(
    other_user_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Message)
    if other_user_id is not None:
        stmt = stmt.where(
            or_(
                (Message.sender_id == user.id) & (Message.receiver_id == other_user_id),
                (Message.sender_id == other_user_id) & (Message.receiver_id == user.id),
            )
        )
    else:
        stmt = stmt.where(or_(Message.sender_id == user.id, Message.receiver_id == user.id))

    stmt = stmt.order_by(desc(Message.created_at)).limit(limit)
    messages = list(db.scalars(stmt))

    results: list[MessageResponse] = []
    for m in messages:
        # Mark as read if user is the receiver
        if m.receiver_id == user.id and not m.is_read:
            m.is_read = True

        results.append(
            MessageResponse(
                id=m.id,
                sender_id=m.sender_id,
                receiver_id=m.receiver_id,
                content=m.content,
                is_read=m.is_read,
                created_at=m.created_at,
                sender_name=m.sender.name if m.sender else None,
                receiver_name=m.receiver.name if m.receiver else None,
            )
        )
    db.commit()
    return results

@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def send_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.receiver_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a message to yourself."
        )

    receiver = db.get(User, payload.receiver_id)
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient user not found."
        )

    # Enforce user blocking checks: neither party can message if blocked
    is_blocked = (db.scalar(
        select(func.count(UserBlock.id)).where(
            or_(
                (UserBlock.blocker_id == user.id) & (UserBlock.blocked_user_id == payload.receiver_id),
                (UserBlock.blocker_id == payload.receiver_id) & (UserBlock.blocked_user_id == user.id),
            )
        )
    ) or 0) > 0

    if is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot send message to this user. A block is active between these accounts."
        )

    msg = Message(
        sender_id=user.id,
        receiver_id=payload.receiver_id,
        content=payload.content.strip(),
        is_read=False,
    )
    db.add(msg)

    # Trigger notification for receiver
    snippet = payload.content.strip()[:40]
    notif = Notification(
        user_id=payload.receiver_id,
        title=f"New Message from {user.name}",
        message=f'"{snippet}..."' if len(payload.content.strip()) > 40 else f'"{snippet}"',
        link="/messages",
    )
    db.add(notif)

    db.commit()
    db.refresh(msg)

    return MessageResponse(
        id=msg.id,
        sender_id=msg.sender_id,
        receiver_id=msg.receiver_id,
        content=msg.content,
        is_read=msg.is_read,
        created_at=msg.created_at,
        sender_name=user.name,
        receiver_name=receiver.name,
    )

@router.get("/unread/count")
def get_unread_messages_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Returns total unread 1:1 incoming messages count for authenticated user."""
    count = db.scalar(
        select(func.count(Message.id)).where(
            (Message.receiver_id == user.id) & (~Message.is_read)
        )
    ) or 0
    return {"unread_count": count}

@router.patch("/{message_id}/read")
def mark_message_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    msg = db.get(Message, message_id)
    if not msg or msg.receiver_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    msg.is_read = True
    db.commit()
    return {"status": "ok", "message": "Message marked as read"}

@router.post("/{other_user_id}/read")
def mark_conversation_as_read(
    other_user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Marks all incoming messages from other_user_id as read."""
    unread_msgs = list(
        db.scalars(
            select(Message).where(
                (Message.sender_id == other_user_id)
                & (Message.receiver_id == user.id)
                & (~Message.is_read)
            )
        )
    )
    for m in unread_msgs:
        m.is_read = True
    db.commit()
    return {"status": "ok", "marked_read_count": len(unread_msgs)}
