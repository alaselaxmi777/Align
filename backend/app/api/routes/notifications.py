from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.catalog import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("", response_model=list[NotificationResponse])
def get_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = list(db.scalars(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())
    ))
    return items

@router.get("/unread/count")
def get_unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.scalar(
        select(func.count(Notification.id)).where(
            (Notification.user_id == user.id) & (~Notification.is_read)
        )
    ) or 0
    return {"unread_count": count}

@router.post("/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    unread = list(
        db.scalars(
            select(Notification).where(
                (Notification.user_id == user.id) & (~Notification.is_read)
            )
        )
    )
    for n in unread:
        n.is_read = True
    db.commit()
    return {"status": "ok", "marked_read_count": len(unread)}

@router.put("/{notification_id}/read")
@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"status": "ok", "message": "Notification marked as read"}

@router.delete("/{notification_id}")
def delete_notification(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.get(Notification, notification_id)
    if not notif or notif.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    db.delete(notif)
    db.commit()
    return {"status": "ok", "message": "Notification deleted successfully"}
