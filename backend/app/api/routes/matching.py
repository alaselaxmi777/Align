from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.matching_service import get_smart_matches_for_user

router = APIRouter(prefix="/matching", tags=["matching"])

@router.get("/peers")
def get_smart_peer_matches(
    limit: int = Query(default=15, ge=1, le=50),
    min_score: int = Query(default=20, ge=0, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    matches = get_smart_matches_for_user(
        db=db,
        current_user=user,
        limit=limit,
        min_score=max(min_score, 20),
    )
    return {
        "user_id": user.id,
        "total_matched": len(matches),
        "results": matches,
    }
