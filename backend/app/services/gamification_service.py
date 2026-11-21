import math
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.gamification import UserGamification, UserBadge, UserActivityLog

logger = logging.getLogger(__name__)

BADGE_DEFINITIONS = {
    "PIONEER": {
        "name": "Community Pioneer",
        "description": "Created an authentic community or interest circle on ALIGN.",
        "category": "community",
        "icon_name": "Sparkles",
    },
    "GOAL_CRUSHER": {
        "name": "Goal Crusher",
        "description": "Completed multiple learning or career milestones in a Goal Journey.",
        "category": "milestones",
        "icon_name": "Target",
    },
    "CONNECTOR": {
        "name": "Network Connector",
        "description": "Successfully established peer connections with like-minded creators.",
        "category": "networking",
        "icon_name": "Users",
    },
    "EXPLORER": {
        "name": "Curious Explorer",
        "description": "Discovered and bookmarked high-impact student & tech opportunities.",
        "category": "learning",
        "icon_name": "Compass",
    },
    "TEAM_PLAYER": {
        "name": "Collaboration Builder",
        "description": "Joined or published an active project collaboration team.",
        "category": "community",
        "icon_name": "Layers",
    },
    "STREAK_BUILDER": {
        "name": "Consistent Learner",
        "description": "Maintained an active discovery streak on ALIGN.",
        "category": "learning",
        "icon_name": "Flame",
    },
}

def get_or_create_gamification(db: Session, user_id: int) -> UserGamification:
    game = db.scalar(select(UserGamification).where(UserGamification.user_id == user_id))
    if not game:
        game = UserGamification(
            user_id=user_id,
            xp_points=100,  # Welcome bonus XP
            current_level=1,
            current_streak_days=1,
            community_contribution_points=10,
        )
        db.add(game)
        db.flush()
        # Add welcome activity log with dedup key
        db.add(
            UserActivityLog(
                gamification_id=game.id,
                action_type="account_creation",
                xp_awarded=100,
                description="Joined ALIGN Discovery Platform",
                dedup_key="welcome",
            )
        )
        # Unlock PIONEER badge on signup
        badge_meta = BADGE_DEFINITIONS["PIONEER"]
        db.add(
            UserBadge(
                gamification_id=game.id,
                badge_key="PIONEER",
                name=badge_meta["name"],
                description=badge_meta["description"],
                category=badge_meta["category"],
                icon_name=badge_meta["icon_name"],
            )
        )
        db.commit()
        db.refresh(game)
    else:
        # Check streak update
        now = datetime.now(timezone.utc)
        if game.last_activity_date:
            diff = now - game.last_activity_date
            if diff.days == 1:
                game.current_streak_days += 1
                if game.current_streak_days >= 3:
                    check_and_unlock_badge(db, game, "STREAK_BUILDER")
            elif diff.days > 1:
                game.current_streak_days = 1
        game.last_activity_date = now
        db.commit()

    return game

def award_xp(
    db: Session,
    user_id: int,
    action_type: str,
    points: int,
    description: str,
    dedup_key: str | None = None,
) -> dict:
    """Awards authentic XP with anti-duplicate protection, calculates level, logs activity, and checks badges."""
    game = get_or_create_gamification(db, user_id)

    if dedup_key:
        existing = db.scalar(
            select(UserActivityLog).where(
                (UserActivityLog.gamification_id == game.id) & (UserActivityLog.dedup_key == dedup_key)
            )
        )
        if existing:
            logger.info("Anti-duplicate reward triggered: user %s already rewarded for %s", user_id, dedup_key)
            return {
                "status": "duplicate",
                "xp_awarded": 0,
                "total_xp": game.xp_points,
                "level": game.current_level,
                "level_up": False,
                "streak_days": game.current_streak_days,
                "message": "Action already verified and rewarded.",
            }

    game.xp_points += points

    # Level calculation: Level = floor(sqrt(XP / 100)) + 1
    new_level = math.floor(math.sqrt(game.xp_points / 100)) + 1
    level_up = new_level > game.current_level
    game.current_level = new_level

    log = UserActivityLog(
        gamification_id=game.id,
        action_type=action_type,
        xp_awarded=points,
        description=description,
        dedup_key=dedup_key,
    )
    db.add(log)
    db.commit()
    db.refresh(game)

    # Dynamic badge checks based on verified actions
    if action_type in ("goal_milestone_completed", "milestone_completed"):
        check_and_unlock_badge(db, game, "GOAL_CRUSHER")
    elif action_type in ("peer_connected", "connection_accepted"):
        check_and_unlock_badge(db, game, "CONNECTOR")
    elif action_type in ("circle_joined", "community_joined", "bookmark_opportunity"):
        check_and_unlock_badge(db, game, "EXPLORER")
    elif action_type in ("project_published", "joined_team", "project_member_added"):
        check_and_unlock_badge(db, game, "TEAM_PLAYER")

    return {
        "status": "ok",
        "xp_awarded": points,
        "total_xp": game.xp_points,
        "level": game.current_level,
        "level_up": level_up,
        "streak_days": game.current_streak_days,
    }

def check_and_unlock_badge(db: Session, game: UserGamification, badge_key: str) -> bool:
    """Unlocks a badge if not already attained."""
    if badge_key not in BADGE_DEFINITIONS:
        return False

    existing = db.scalar(
        select(UserBadge).where(
            (UserBadge.gamification_id == game.id) & (UserBadge.badge_key == badge_key)
        )
    )
    if existing:
        return False

    badge_meta = BADGE_DEFINITIONS[badge_key]
    badge = UserBadge(
        gamification_id=game.id,
        badge_key=badge_key,
        name=badge_meta["name"],
        description=badge_meta["description"],
        category=badge_meta["category"],
        icon_name=badge_meta["icon_name"],
    )
    db.add(badge)
    # Badge award bonus XP
    game.xp_points += 50
    db.add(
        UserActivityLog(
            gamification_id=game.id,
            action_type="badge_unlocked",
            xp_awarded=50,
            description=f"Unlocked Badge: {badge_meta['name']}",
        )
    )
    db.commit()
    return True
