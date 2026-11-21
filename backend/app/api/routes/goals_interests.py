import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dataset import GoalsInterestsDataset, GoalMaster, InterestMaster
from app.schemas.dataset import (
    GoalMasterResponse,
    InterestMasterResponse,
    GoalInterestDatasetItem,
    CategorySummary,
    GoalsInterestsStatsResponse,
)

logger = logging.getLogger("align.goals_interests")
router = APIRouter(tags=["goals-and-interests"])

# --- GOALS ENDPOINTS ---

@router.get("/goals", response_model=List[GoalMasterResponse])
def list_goals(
    category: Optional[str] = Query(None, description="Filter by goal category"),
    q: Optional[str] = Query(None, description="Search term for goal name or description"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    stmt = select(GoalMaster)
    if category:
        stmt = stmt.where(GoalMaster.category.ilike(f"%{category.strip()}%"))
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(GoalMaster.type.ilike(term), GoalMaster.description.ilike(term)))

    stmt = stmt.order_by(GoalMaster.category.asc(), GoalMaster.type.asc())
    offset = (page - 1) * limit
    return list(db.scalars(stmt.offset(offset).limit(limit)))


@router.get("/goals/categories", response_model=List[CategorySummary])
def get_goal_categories(db: Session = Depends(get_db)):
    cats = list(db.execute(
        select(GoalMaster.category, func.count(GoalMaster.id))
        .group_by(GoalMaster.category)
        .order_by(GoalMaster.category.asc())
    ))
    summaries = []
    for cat, count in cats:
        sample_types = list(db.scalars(
            select(GoalMaster.type)
            .where(GoalMaster.category == cat)
            .order_by(GoalMaster.type.asc())
            .limit(5)
        ))
        summaries.append(CategorySummary(category=cat, count=count, sample_types=sample_types))
    return summaries


@router.get("/goals/search", response_model=List[GoalInterestDatasetItem])
def search_goals(
    q: Optional[str] = Query(None, description="Search keyword in goal type, description, or expanded description"),
    category: Optional[str] = Query(None, description="Category filter"),
    life_context: Optional[str] = Query(None, description="Life context filter (e.g. Personal life, Career)"),
    timeline: Optional[str] = Query(None, description="Timeline / engagement level filter"),
    priority: Optional[str] = Query(None, description="Priority / setting filter"),
    motivation: Optional[str] = Query(None, description="Primary motivation filter"),
    min_popularity: Optional[int] = Query(None, ge=1, le=10, description="Minimum popularity score"),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(GoalsInterestsDataset).where(GoalsInterestsDataset.record_type == "Goal")

    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            GoalsInterestsDataset.type.ilike(term),
            GoalsInterestsDataset.description.ilike(term),
            GoalsInterestsDataset.expanded_record_description.ilike(term),
        ))
    if category:
        stmt = stmt.where(GoalsInterestsDataset.category.ilike(f"%{category.strip()}%"))
    if life_context:
        stmt = stmt.where(GoalsInterestsDataset.life_context.ilike(f"%{life_context.strip()}%"))
    if timeline:
        stmt = stmt.where(GoalsInterestsDataset.timeline_engagement_level.ilike(f"%{timeline.strip()}%"))
    if priority:
        stmt = stmt.where(GoalsInterestsDataset.priority_setting.ilike(f"%{priority.strip()}%"))
    if motivation:
        stmt = stmt.where(GoalsInterestsDataset.primary_motivation.ilike(f"%{motivation.strip()}%"))
    if min_popularity is not None:
        stmt = stmt.where(GoalsInterestsDataset.popularity_score >= min_popularity)

    stmt = stmt.order_by(GoalsInterestsDataset.popularity_score.desc(), GoalsInterestsDataset.id.asc())
    offset = (page - 1) * limit
    return list(db.scalars(stmt.offset(offset).limit(limit)))


# --- INTERESTS ENDPOINTS ---

@router.get("/interests", response_model=List[InterestMasterResponse])
def list_interests(
    category: Optional[str] = Query(None, description="Filter by interest category"),
    q: Optional[str] = Query(None, description="Search term for interest name or description"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(InterestMaster)
    if category:
        stmt = stmt.where(InterestMaster.category.ilike(f"%{category.strip()}%"))
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(InterestMaster.type.ilike(term), InterestMaster.description.ilike(term)))

    stmt = stmt.order_by(InterestMaster.category.asc(), InterestMaster.type.asc())
    offset = (page - 1) * limit
    return list(db.scalars(stmt.offset(offset).limit(limit)))


@router.get("/interests/categories", response_model=List[CategorySummary])
def get_interest_categories(db: Session = Depends(get_db)):
    cats = list(db.execute(
        select(InterestMaster.category, func.count(InterestMaster.id))
        .group_by(InterestMaster.category)
        .order_by(InterestMaster.category.asc())
    ))
    summaries = []
    for cat, count in cats:
        sample_types = list(db.scalars(
            select(InterestMaster.type)
            .where(InterestMaster.category == cat)
            .order_by(InterestMaster.type.asc())
            .limit(5)
        ))
        summaries.append(CategorySummary(category=cat, count=count, sample_types=sample_types))
    return summaries


@router.get("/interests/search", response_model=List[GoalInterestDatasetItem])
def search_interests(
    q: Optional[str] = Query(None, description="Search keyword in interest type, description, or expanded description"),
    category: Optional[str] = Query(None, description="Category filter"),
    life_context: Optional[str] = Query(None, description="Life context filter"),
    timeline: Optional[str] = Query(None, description="Timeline / engagement level filter"),
    setting: Optional[str] = Query(None, description="Priority / setting filter"),
    frequency: Optional[str] = Query(None, description="Status / frequency filter"),
    motivation: Optional[str] = Query(None, description="Primary motivation filter"),
    min_popularity: Optional[int] = Query(None, ge=1, le=10),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(GoalsInterestsDataset).where(GoalsInterestsDataset.record_type == "Interest")

    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            GoalsInterestsDataset.type.ilike(term),
            GoalsInterestsDataset.description.ilike(term),
            GoalsInterestsDataset.expanded_record_description.ilike(term),
        ))
    if category:
        stmt = stmt.where(GoalsInterestsDataset.category.ilike(f"%{category.strip()}%"))
    if life_context:
        stmt = stmt.where(GoalsInterestsDataset.life_context.ilike(f"%{life_context.strip()}%"))
    if timeline:
        stmt = stmt.where(GoalsInterestsDataset.timeline_engagement_level.ilike(f"%{timeline.strip()}%"))
    if setting:
        stmt = stmt.where(GoalsInterestsDataset.priority_setting.ilike(f"%{setting.strip()}%"))
    if frequency:
        stmt = stmt.where(GoalsInterestsDataset.status_frequency.ilike(f"%{frequency.strip()}%"))
    if motivation:
        stmt = stmt.where(GoalsInterestsDataset.primary_motivation.ilike(f"%{motivation.strip()}%"))
    if min_popularity is not None:
        stmt = stmt.where(GoalsInterestsDataset.popularity_score >= min_popularity)

    stmt = stmt.order_by(GoalsInterestsDataset.popularity_score.desc(), GoalsInterestsDataset.id.asc())
    offset = (page - 1) * limit
    return list(db.scalars(stmt.offset(offset).limit(limit)))


# --- GOALS & INTERESTS DATASET STATS & FACETS ---

@router.get("/goals-interests/stats", response_model=GoalsInterestsStatsResponse)
def get_gi_stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(GoalsInterestsDataset.id))) or 0
    goals_count = db.scalar(
        select(func.count(GoalsInterestsDataset.id)).where(GoalsInterestsDataset.record_type == "Goal")
    ) or 0
    interests_count = db.scalar(
        select(func.count(GoalsInterestsDataset.id)).where(GoalsInterestsDataset.record_type == "Interest")
    ) or 0
    goal_types_count = db.scalar(select(func.count(GoalMaster.id))) or 0
    interest_types_count = db.scalar(select(func.count(InterestMaster.id))) or 0

    cats = list(db.execute(
        select(GoalsInterestsDataset.category, func.count(GoalsInterestsDataset.id))
        .group_by(GoalsInterestsDataset.category)
        .order_by(func.count(GoalsInterestsDataset.id).desc())
    ))
    cat_summaries = []
    for cat, count in cats:
        sample_types = list(db.scalars(
            select(GoalsInterestsDataset.type)
            .where(GoalsInterestsDataset.category == cat)
            .distinct()
            .limit(4)
        ))
        cat_summaries.append(CategorySummary(category=cat, count=count, sample_types=sample_types))

    return GoalsInterestsStatsResponse(
        total_records=total,
        goals_count=goals_count,
        interests_count=interests_count,
        goal_types_count=goal_types_count,
        interest_types_count=interest_types_count,
        categories=cat_summaries,
    )


@router.get("/goals-interests/facets")
def get_gi_facets(db: Session = Depends(get_db)):
    """Returns unique facet values to power frontend dynamic filters."""
    life_contexts = list(db.scalars(
        select(GoalsInterestsDataset.life_context).distinct()
        .where(GoalsInterestsDataset.life_context.isnot(None))
        .order_by(GoalsInterestsDataset.life_context.asc())
    ))
    timelines = list(db.scalars(
        select(GoalsInterestsDataset.timeline_engagement_level).distinct()
        .where(GoalsInterestsDataset.timeline_engagement_level.isnot(None))
        .order_by(GoalsInterestsDataset.timeline_engagement_level.asc())
    ))
    priorities = list(db.scalars(
        select(GoalsInterestsDataset.priority_setting).distinct()
        .where(GoalsInterestsDataset.priority_setting.isnot(None))
        .order_by(GoalsInterestsDataset.priority_setting.asc())
    ))
    frequencies = list(db.scalars(
        select(GoalsInterestsDataset.status_frequency).distinct()
        .where(GoalsInterestsDataset.status_frequency.isnot(None))
        .order_by(GoalsInterestsDataset.status_frequency.asc())
    ))
    motivations = list(db.scalars(
        select(GoalsInterestsDataset.primary_motivation).distinct()
        .where(GoalsInterestsDataset.primary_motivation.isnot(None))
        .order_by(GoalsInterestsDataset.primary_motivation.asc())
    ))

    return {
        "life_contexts": life_contexts,
        "timelines": timelines,
        "priorities": priorities,
        "frequencies": frequencies,
        "motivations": motivations,
    }
