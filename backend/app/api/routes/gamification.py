from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, select
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.gamification import UserGamification, UserBadge, UserActivityLog
from app.services.gamification_service import get_or_create_gamification

router = APIRouter(prefix="/gamification", tags=["gamification"])

@router.get("/me")
def get_my_gamification_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    game = get_or_create_gamification(db, user.id)

    # Next level XP requirement: next_level = current_level + 1; required_xp = (next_level - 1)^2 * 100
    next_level = game.current_level + 1
    xp_for_next = ((next_level - 1) ** 2) * 100
    xp_for_current = ((game.current_level - 1) ** 2) * 100
    level_progress = int(
        round(
            ((game.xp_points - xp_for_current) / max(1, (xp_for_next - xp_for_current))) * 100
        )
    )
    level_progress = max(0, min(100, level_progress))

    return {
        "user_id": user.id,
        "name": user.name,
        "avatar_url": user.profile.avatar_url if user.profile else None,
        "xp_points": game.xp_points,
        "current_level": game.current_level,
        "next_level": next_level,
        "xp_for_next_level": xp_for_next,
        "level_progress_percentage": level_progress,
        "current_streak_days": game.current_streak_days,
        "community_contribution_points": game.community_contribution_points,
        "badges": [
            {
                "id": b.id,
                "badge_key": b.badge_key,
                "name": b.name,
                "description": b.description,
                "category": b.category,
                "icon_name": b.icon_name,
                "unlocked_at": b.unlocked_at,
            }
            for b in game.badges
        ],
        "recent_activities": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "xp_awarded": a.xp_awarded,
                "description": a.description,
                "created_at": a.created_at,
            }
            for a in game.activity_logs[:8]
        ],
    }

@router.get("/history")
def get_xp_history(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Returns authentic XP transaction history with anti-duplicate verified audit logs.
    """
    game = get_or_create_gamification(db, user.id)

    total_count = db.scalar(
        select(func.count(UserActivityLog.id)).where(UserActivityLog.gamification_id == game.id)
    ) or 0

    logs = list(
        db.scalars(
            select(UserActivityLog)
            .where(UserActivityLog.gamification_id == game.id)
            .order_by(desc(UserActivityLog.created_at))
            .offset(offset)
            .limit(limit)
        )
    )

    return {
        "user_id": user.id,
        "total_xp": game.xp_points,
        "current_level": game.current_level,
        "total_transactions": total_count,
        "items": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "xp_awarded": a.xp_awarded,
                "description": a.description,
                "dedup_key": a.dedup_key,
                "created_at": a.created_at,
            }
            for a in logs
        ],
    }

@router.get("/leaderboard")
def get_gamification_leaderboard(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    top_players = list(
        db.scalars(
            select(UserGamification)
            .join(User, UserGamification.user_id == User.id)
            .where(User.is_test == False, User.is_active == True)
            .order_by(desc(UserGamification.xp_points))
            .limit(limit)
        )
    )

    results = []
    for rank, p in enumerate(top_players, 1):
        results.append({
            "rank": rank,
            "user_id": p.user_id,
            "name": p.user.name if p.user else "ALIGN Creator",
            "avatar_url": p.user.profile.avatar_url if (p.user and p.user.profile) else None,
            "level": p.current_level,
            "xp_points": p.xp_points,
            "streak_days": p.current_streak_days,
            "badges_count": len(p.badges),
            "is_me": (p.user_id == user.id),
        })

    return results
