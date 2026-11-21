import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, UserReport
from app.models.post import Post
from app.models.reel import Reel
from app.schemas.social import CreateReportRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("", status_code=status.HTTP_201_CREATED)
def submit_report(
    payload: CreateReportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Submits a content or user safety report for moderation review.
    Supported targets: post, reel, user, comment.
    """
    target_type = payload.target_type.lower().strip()
    target_id = payload.target_id
    reason = payload.reason.strip()
    details = payload.details.strip() if payload.details else None

    reported_user_id = None
    post_id = None
    reel_id = None

    if target_type == "post":
        post = db.get(Post, target_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        if post.author_id == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot report your own post.")
        reported_user_id = post.author_id
        post_id = post.id

    elif target_type == "reel":
        reel = db.get(Reel, target_id)
        if not reel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")
        if reel.author_id == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot report your own reel.")
        reported_user_id = reel.author_id
        reel_id = reel.id

    elif target_type == "user":
        target_user = db.get(User, target_id)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if target_user.id == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot report yourself.")
        reported_user_id = target_user.id

    elif target_type == "comment":
        # Can be attached to user report
        reported_user_id = None

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target_type: {target_type}",
        )

    report = UserReport(
        reporter_id=user.id,
        reported_user_id=reported_user_id,
        target_type=target_type,
        post_id=post_id,
        reel_id=reel_id,
        reason=reason,
        details=details,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    logger.info(
        "User %s created report #%s on %s:%s (reason: %s)",
        user.id,
        report.id,
        target_type,
        target_id,
        reason,
    )

    return {
        "status": "ok",
        "message": "Report submitted successfully for administrative review.",
        "report_id": report.id,
        "target_type": target_type,
        "target_id": target_id,
    }
