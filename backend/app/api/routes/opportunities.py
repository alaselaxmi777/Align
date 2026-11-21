from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, select
from app.api.deps import get_current_user, get_current_user_optional, get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.models.opportunity import Opportunity, OpportunityBookmark
from app.services.opportunities_service import (
    deactivate_expired_opportunities,
    import_opportunities_from_csv,
    ingest_github_opportunities,
    ingest_kaggle_opportunities,
    seed_verified_opportunities,
)
from app.services.embeddings import generate_embedding
from app.services.gamification_service import award_xp, check_and_unlock_badge, get_or_create_gamification

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

class OpportunityCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    organization: str = Field(min_length=2, max_length=160)
    opportunity_type: str = "hackathon"
    description: str = Field(min_length=10, max_length=4000)
    location: str = "Remote / Global"
    is_remote: bool = True
    deadline: datetime | None = None
    stipend_or_prize: str | None = None
    apply_url: str = Field(min_length=5, max_length=500)
    tags: str = ""
    source: str = "ALIGN Community"

    @field_validator("apply_url")
    @classmethod
    def validate_apply_url(cls, v: str) -> str:
        trimmed = (v or "").strip()
        if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise ValueError("apply_url must use http:// or https:// scheme")
        return trimmed

def serialize_opportunity(opp: Opportunity, user: User | None) -> dict:
    is_bookmarked = False
    if user:
        is_bookmarked = any(b.user_id == user.id for b in opp.bookmarks)

    days_left = None
    now = datetime.now(timezone.utc)
    if opp.deadline:
        diff = opp.deadline - now
        days_left = diff.days

    return {
        "id": opp.id,
        "title": opp.title,
        "organization": opp.organization,
        "org": opp.organization,
        "opportunity_type": opp.opportunity_type,
        "type": opp.opportunity_type,
        "description": opp.description,
        "location": opp.location,
        "is_remote": opp.is_remote,
        "remote_eligible": opp.is_remote,
        "deadline": opp.deadline,
        "days_left": days_left,
        "stipend_or_prize": opp.stipend_or_prize,
        "reward": opp.stipend_or_prize,
        "apply_url": opp.apply_url,
        "source_url": opp.apply_url,
        "tags": [t.strip() for t in opp.tags.split(",") if t.strip()],
        "source": opp.source,
        "is_active": opp.is_active,
        "last_verified_at": opp.last_verified_at,
        "is_bookmarked": is_bookmarked,
        "bookmarks_count": len(opp.bookmarks),
        "created_at": opp.created_at,
    }

class CSVImportPayload(BaseModel):
    csv_content: str

@router.get("")
def list_opportunities(
    q: str | None = Query(default=None, max_length=120),
    type: str | None = Query(default=None, max_length=50),
    is_remote: bool | None = None,
    limit: int = Query(default=24, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    # Auto-seed verified opportunities if table is empty
    count = db.scalar(select(func.count(Opportunity.id))) or 0
    if count == 0:
        seed_verified_opportunities(db)

    now = datetime.now(timezone.utc)
    # Hide expired opportunities and only query active rows
    stmt = (
        select(Opportunity)
        .where(Opportunity.is_active == True)
        .where(or_(Opportunity.deadline.is_(None), Opportunity.deadline >= now))
        .order_by(Opportunity.deadline.asc().nullslast(), Opportunity.created_at.desc())
    )
    if type:
        stmt = stmt.where(Opportunity.opportunity_type == type.strip().lower())
    if is_remote is not None:
        stmt = stmt.where(Opportunity.is_remote == is_remote)
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Opportunity.title.ilike(term),
                Opportunity.organization.ilike(term),
                Opportunity.description.ilike(term),
                Opportunity.tags.ilike(term),
                Opportunity.location.ilike(term),
            )
        )
    stmt = stmt.limit(limit)
    items = list(db.scalars(stmt))
    return [serialize_opportunity(o, user) for o in items]

@router.post("", status_code=status.HTTP_201_CREATED)
def create_opportunity(
    payload: OpportunityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ctx = f"{payload.title} {payload.organization} {payload.opportunity_type} {payload.description} {payload.tags}"
    emb = generate_embedding(ctx)

    opp = Opportunity(
        title=payload.title.strip(),
        organization=payload.organization.strip(),
        opportunity_type=payload.opportunity_type.lower(),
        description=payload.description.strip(),
        location=payload.location,
        is_remote=payload.is_remote,
        deadline=payload.deadline,
        stipend_or_prize=payload.stipend_or_prize,
        apply_url=payload.apply_url.strip(),
        tags=payload.tags,
        source=payload.source,
        embedding=emb,
    )
    db.add(opp)
    award_xp(db, user.id, "opportunity_shared", 40, f"Shared opportunity: {opp.title[:30]}")
    db.commit()
    db.refresh(opp)
    return serialize_opportunity(opp, user)

@router.post("/{opportunity_id}/bookmark")
def toggle_bookmark_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    opp = db.get(Opportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    existing = db.scalar(
        select(OpportunityBookmark).where(
            (OpportunityBookmark.opportunity_id == opportunity_id) & (OpportunityBookmark.user_id == user.id)
        )
    )
    if existing:
        db.delete(existing)
        db.commit()
        return {"status": "ok", "is_bookmarked": False, "message": "Bookmark removed."}

    bm = OpportunityBookmark(user_id=user.id, opportunity_id=opp.id)
    db.add(bm)
    award_xp(db, user.id, "opportunity_saved", 10, "Bookmarked opportunity")
    game = get_or_create_gamification(db, user.id)
    check_and_unlock_badge(db, game, "EXPLORER")
    db.commit()
    return {"status": "ok", "is_bookmarked": True, "message": "Opportunity saved!"}

@router.get("/my/bookmarks")
def get_my_bookmarked_opportunities(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bookmarks = list(
        db.scalars(
            select(OpportunityBookmark)
            .where(OpportunityBookmark.user_id == user.id)
            .order_by(OpportunityBookmark.created_at.desc())
        )
    )
    return [serialize_opportunity(b.opportunity, user) for b in bookmarks if b.opportunity]

@router.post("/import-csv")
def import_opportunities_csv(
    payload: CSVImportPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Admin endpoint to bulk import verified opportunities from CSV text."""
    if not (user.is_admin or user.role == "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can import CSV opportunities.")
    return import_opportunities_from_csv(payload.csv_content, db)

@router.post("/sync/kaggle")
def sync_kaggle_competitions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Admin endpoint to ingest competitive machine learning challenges from Kaggle."""
    return ingest_kaggle_opportunities(db)

@router.post("/sync/github")
def sync_github_hackathons(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Admin endpoint to ingest open developer hackathons and bounties from GitHub."""
    return ingest_github_opportunities(db)

@router.post("/deactivate-expired")
def deactivate_expired(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Scheduled/maintenance endpoint to deactivate past opportunities."""
    count = deactivate_expired_opportunities(db)
    return {"status": "success", "deactivated_count": count}
