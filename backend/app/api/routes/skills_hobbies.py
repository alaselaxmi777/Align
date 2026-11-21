import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dataset import SkillsHobbiesDataset, SkillMaster, HobbyMaster
from app.schemas.dataset import (
    SkillMasterResponse,
    HobbyMasterResponse,
    SkillHobbyDatasetItem,
    CategorySummary,
    DatasetStatsResponse,
)

logger = logging.getLogger("align.skills_hobbies")
router = APIRouter(tags=["skills-and-hobbies"])

# --- SKILLS ENDPOINTS ---

@router.get("/skills", response_model=List[SkillMasterResponse])
def list_skills(
    response: Response,
    category: Optional[str] = Query(None, description="Filter by skill category"),
    q: Optional[str] = Query(None, description="Search term for skill name or description"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    total_count = db.scalar(select(func.count(SkillMaster.id))) or 0
    if total_count == 0:
        logger.warning("SkillMaster catalog is empty. Run seed_master_data.py to populate.")
    response.headers["X-Total-Catalog"] = str(total_count)
    stmt = select(SkillMaster)
    if category:
        stmt = stmt.where(SkillMaster.category.ilike(f"%{category.strip()}%"))
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(SkillMaster.type.ilike(term), SkillMaster.description.ilike(term)))
    
    stmt = stmt.order_by(SkillMaster.category.asc(), SkillMaster.type.asc())
    offset = (page - 1) * limit
    results = list(db.scalars(stmt.offset(offset).limit(limit)))
    return results

@router.get("/skills/categories", response_model=List[CategorySummary])
def get_skill_categories(db: Session = Depends(get_db)):
    cats = list(db.execute(
        select(SkillMaster.category, func.count(SkillMaster.id))
        .group_by(SkillMaster.category)
        .order_by(SkillMaster.category.asc())
    ))
    summaries = []
    for cat, count in cats:
        sample_types = list(db.scalars(
            select(SkillMaster.type)
            .where(SkillMaster.category == cat)
            .order_by(SkillMaster.type.asc())
            .limit(5)
        ))
        summaries.append(CategorySummary(category=cat, count=count, sample_types=sample_types))
    return summaries

@router.get("/skills/search", response_model=List[SkillHobbyDatasetItem])
def search_skills(
    q: Optional[str] = Query(None, description="Search keyword in skill type, description, or expanded description"),
    category: Optional[str] = Query(None, description="Category filter"),
    context: Optional[str] = Query(None, description="Application context filter (e.g. Remote work, Career transition)"),
    proficiency: Optional[str] = Query(None, description="Proficiency level (Beginner, Intermediate, Advanced, Expert)"),
    setting: Optional[str] = Query(None, description="Setting (Individual, Group or team)"),
    min_popularity: Optional[int] = Query(None, ge=1, le=10, description="Minimum popularity score"),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(SkillsHobbiesDataset).where(SkillsHobbiesDataset.record_type == "Skill")
    
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            SkillsHobbiesDataset.type.ilike(term),
            SkillsHobbiesDataset.description.ilike(term),
            SkillsHobbiesDataset.expanded_record_description.ilike(term),
        ))
    if category:
        stmt = stmt.where(SkillsHobbiesDataset.category.ilike(f"%{category.strip()}%"))
    if context:
        stmt = stmt.where(SkillsHobbiesDataset.application_context.ilike(f"%{context.strip()}%"))
    if proficiency:
        stmt = stmt.where(SkillsHobbiesDataset.proficiency_engagement_level.ilike(f"%{proficiency.strip()}%"))
    if setting:
        stmt = stmt.where(SkillsHobbiesDataset.setting.ilike(f"%{setting.strip()}%"))
    if min_popularity is not None:
        stmt = stmt.where(SkillsHobbiesDataset.popularity_score >= min_popularity)

    stmt = stmt.order_by(SkillsHobbiesDataset.popularity_score.desc(), SkillsHobbiesDataset.id.asc())
    offset = (page - 1) * limit
    return list(db.scalars(stmt.offset(offset).limit(limit)))

# --- HOBBIES ENDPOINTS ---

@router.get("/hobbies", response_model=List[HobbyMasterResponse])
def list_hobbies(
    response: Response,
    category: Optional[str] = Query(None, description="Filter by hobby category"),
    q: Optional[str] = Query(None, description="Search term for hobby name or description"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total_count = db.scalar(select(func.count(HobbyMaster.id))) or 0
    if total_count == 0:
        logger.warning("HobbyMaster catalog is empty. Run seed_master_data.py to populate.")
    response.headers["X-Total-Catalog"] = str(total_count)
    stmt = select(HobbyMaster)
    if category:
        stmt = stmt.where(HobbyMaster.category.ilike(f"%{category.strip()}%"))
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(HobbyMaster.type.ilike(term), HobbyMaster.description.ilike(term)))
    
    stmt = stmt.order_by(HobbyMaster.category.asc(), HobbyMaster.type.asc())
    offset = (page - 1) * limit
    return list(db.scalars(stmt.offset(offset).limit(limit)))

@router.get("/hobbies/categories", response_model=List[CategorySummary])
def get_hobby_categories(db: Session = Depends(get_db)):
    cats = list(db.execute(
        select(HobbyMaster.category, func.count(HobbyMaster.id))
        .group_by(HobbyMaster.category)
        .order_by(HobbyMaster.category.asc())
    ))
    summaries = []
    for cat, count in cats:
        sample_types = list(db.scalars(
            select(HobbyMaster.type)
            .where(HobbyMaster.category == cat)
            .order_by(HobbyMaster.type.asc())
            .limit(5)
        ))
        summaries.append(CategorySummary(category=cat, count=count, sample_types=sample_types))
    return summaries

@router.get("/hobbies/search", response_model=List[SkillHobbyDatasetItem])
def search_hobbies(
    q: Optional[str] = Query(None, description="Search keyword in hobby type, description, or expanded description"),
    category: Optional[str] = Query(None, description="Category filter"),
    context: Optional[str] = Query(None, description="Application context filter"),
    engagement: Optional[str] = Query(None, description="Engagement level (Beginner, Intermediate, Advanced, Expert)"),
    setting: Optional[str] = Query(None, description="Setting (Individual, Group or team)"),
    frequency: Optional[str] = Query(None, description="Frequency (Daily, Weekly, Monthly, Occasionally)"),
    motivation: Optional[str] = Query(None, description="Primary motivation (e.g. Creativity, Mindfulness, Social connection)"),
    min_popularity: Optional[int] = Query(None, ge=1, le=10),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(SkillsHobbiesDataset).where(SkillsHobbiesDataset.record_type == "Hobby")
    
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            SkillsHobbiesDataset.type.ilike(term),
            SkillsHobbiesDataset.description.ilike(term),
            SkillsHobbiesDataset.expanded_record_description.ilike(term),
        ))
    if category:
        stmt = stmt.where(SkillsHobbiesDataset.category.ilike(f"%{category.strip()}%"))
    if context:
        stmt = stmt.where(SkillsHobbiesDataset.application_context.ilike(f"%{context.strip()}%"))
    if engagement:
        stmt = stmt.where(SkillsHobbiesDataset.proficiency_engagement_level.ilike(f"%{engagement.strip()}%"))
    if setting:
        stmt = stmt.where(SkillsHobbiesDataset.setting.ilike(f"%{setting.strip()}%"))
    if frequency:
        stmt = stmt.where(SkillsHobbiesDataset.frequency.ilike(f"%{frequency.strip()}%"))
    if motivation:
        stmt = stmt.where(SkillsHobbiesDataset.primary_motivation.ilike(f"%{motivation.strip()}%"))
    if min_popularity is not None:
        stmt = stmt.where(SkillsHobbiesDataset.popularity_score >= min_popularity)

    stmt = stmt.order_by(SkillsHobbiesDataset.popularity_score.desc(), SkillsHobbiesDataset.id.asc())
    offset = (page - 1) * limit
    return list(db.scalars(stmt.offset(offset).limit(limit)))

# --- DATASET STATS & FACETS ---

@router.get("/dataset/stats", response_model=DatasetStatsResponse)
def get_dataset_stats(db: Session = Depends(get_db)):
    total_records = db.scalar(select(func.count(SkillsHobbiesDataset.id))) or 0
    skills_count = db.scalar(select(func.count(SkillsHobbiesDataset.id)).where(SkillsHobbiesDataset.record_type == "Skill")) or 0
    hobbies_count = db.scalar(select(func.count(SkillsHobbiesDataset.id)).where(SkillsHobbiesDataset.record_type == "Hobby")) or 0
    skill_types_count = db.scalar(select(func.count(SkillMaster.id))) or 0
    hobby_types_count = db.scalar(select(func.count(HobbyMaster.id))) or 0

    cats = list(db.execute(
        select(SkillsHobbiesDataset.category, func.count(SkillsHobbiesDataset.id))
        .group_by(SkillsHobbiesDataset.category)
        .order_by(func.count(SkillsHobbiesDataset.id).desc())
    ))
    cat_summaries = []
    for cat, count in cats:
        sample_types = list(db.scalars(
            select(SkillsHobbiesDataset.type)
            .where(SkillsHobbiesDataset.category == cat)
            .distinct()
            .limit(4)
        ))
        cat_summaries.append(CategorySummary(category=cat, count=count, sample_types=sample_types))

    return DatasetStatsResponse(
        total_records=total_records,
        skills_count=skills_count,
        hobbies_count=hobbies_count,
        skill_types_count=skill_types_count,
        hobby_types_count=hobby_types_count,
        categories=cat_summaries,
    )

@router.get("/dataset/facets")
def get_dataset_facets(db: Session = Depends(get_db)):
    """Returns unique facet values to power frontend dynamic filters."""
    contexts = list(db.scalars(select(SkillsHobbiesDataset.application_context).distinct().order_by(SkillsHobbiesDataset.application_context.asc())))
    proficiencies = list(db.scalars(select(SkillsHobbiesDataset.proficiency_engagement_level).distinct().order_by(SkillsHobbiesDataset.proficiency_engagement_level.asc())))
    settings_list = list(db.scalars(select(SkillsHobbiesDataset.setting).distinct().order_by(SkillsHobbiesDataset.setting.asc())))
    frequencies = [f for f in db.scalars(select(SkillsHobbiesDataset.frequency).distinct().order_by(SkillsHobbiesDataset.frequency.asc())) if f]
    motivations = [m for m in db.scalars(select(SkillsHobbiesDataset.primary_motivation).distinct().order_by(SkillsHobbiesDataset.primary_motivation.asc())) if m]

    return {
        "contexts": contexts,
        "proficiencies": proficiencies,
        "settings": settings_list,
        "frequencies": frequencies,
        "motivations": motivations,
    }
