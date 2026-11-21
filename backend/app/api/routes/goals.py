import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.goal_journey import GoalJourney, GoalMilestone
from app.services.goal_journey_service import generate_goal_journey
from app.services.gamification_service import award_xp

router = APIRouter(prefix="/goals", tags=["goals"])

class GoalGenerateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    timeframe: str = Field(default="3-6 months")
    category: str = Field(default="Career & Learning")

def serialize_journey(journey: GoalJourney) -> dict:
    total_milestones = len(journey.milestones)
    completed_count = sum(1 for m in journey.milestones if m.is_completed)
    progress = int(round((completed_count / total_milestones) * 100)) if total_milestones > 0 else 0

    return {
        "id": journey.id,
        "title": journey.title,
        "target_category": journey.target_category,
        "timeframe": journey.timeframe,
        "description": journey.description,
        "status": journey.status,
        "progress_percentage": progress,
        "total_milestones": total_milestones,
        "completed_milestones": completed_count,
        "created_at": journey.created_at,
        "milestones": [
            {
                "id": m.id,
                "step_order": m.step_order,
                "title": m.title,
                "description": m.description,
                "estimated_weeks": m.estimated_weeks,
                "is_completed": m.is_completed,
                "completed_at": m.completed_at,
                "resources": json.loads(m.recommended_resources) if m.recommended_resources else [],
                "recommended_communities": json.loads(m.recommended_communities_json) if m.recommended_communities_json else [],
                "recommended_events": json.loads(m.recommended_events_json) if m.recommended_events_json else [],
                "recommended_peers": json.loads(m.recommended_peers_json) if m.recommended_peers_json else [],
            }
            for m in journey.milestones
        ],
    }

@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_new_goal_journey(
    payload: GoalGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    journey = generate_goal_journey(
        db=db,
        user=user,
        goal_title=payload.title,
        timeframe=payload.timeframe,
        category=payload.category,
    )
    return serialize_journey(journey)

@router.get("/my")
def get_my_goal_journeys(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    journeys = list(
        db.scalars(
            select(GoalJourney)
            .where(GoalJourney.user_id == user.id)
            .order_by(GoalJourney.created_at.desc())
        )
    )
    return [serialize_journey(j) for j in journeys]

@router.get("/{journey_id}")
def get_journey_by_id(
    journey_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    j = db.get(GoalJourney, journey_id)
    if not j or j.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal Journey not found")
    return serialize_journey(j)

@router.patch("/{journey_id}/milestones/{milestone_id}")
def toggle_milestone_completion(
    journey_id: int,
    milestone_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    j = db.get(GoalJourney, journey_id)
    if not j or j.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal Journey not found")

    m = next((m for m in j.milestones if m.id == milestone_id), None)
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    m.is_completed = not m.is_completed
    m.completed_at = datetime.now(timezone.utc) if m.is_completed else None

    # Award XP if completed
    xp_res = None
    if m.is_completed:
        xp_res = award_xp(db, user.id, "milestone_completed", 50, f"Completed Milestone: {m.title[:35]}")

    # Recalculate journey progress
    total = len(j.milestones)
    comp = sum(1 for item in j.milestones if item.is_completed)
    j.progress_percentage = int(round((comp / total) * 100)) if total > 0 else 0
    if j.progress_percentage == 100:
        j.status = "completed"
        award_xp(db, user.id, "journey_completed", 150, f"Completed Entire Goal Journey: {j.title[:30]}")
    elif j.progress_percentage > 0:
        j.status = "in_progress"
    else:
        j.status = "not_started"

    db.commit()
    db.refresh(j)

    return {
        "milestone_id": m.id,
        "is_completed": m.is_completed,
        "journey_progress": j.progress_percentage,
        "journey_status": j.status,
        "gamification": xp_res,
    }

@router.delete("/{journey_id}")
def delete_goal_journey(
    journey_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    j = db.get(GoalJourney, journey_id)
    if not j or j.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal Journey not found")

    db.delete(j)
    db.commit()
    return {"status": "ok", "message": "Goal Journey deleted successfully."}
