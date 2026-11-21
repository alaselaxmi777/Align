import os
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from app.models.dataset import (
    DatasetMetadata,
    SkillsHobbiesDataset,
    SkillMaster,
    HobbyMaster,
    GoalsInterestsDataset,
    GoalMaster,
    InterestMaster,
)

logger = logging.getLogger(__name__)

def ensure_default_dataset_metadata(db: Session) -> list[dict]:
    """Ensures registered benchmark datasets are properly indexed in metadata."""
    sh_count = db.scalar(select(func.count(SkillsHobbiesDataset.id))) or 0
    gi_count = db.scalar(select(func.count(GoalsInterestsDataset.id))) or 0

    results = []

    # 1. Goals & Interests
    gi_meta = db.scalar(select(DatasetMetadata).where(DatasetMetadata.dataset_name == "Goals & Interests Dataset"))
    if not gi_meta:
        gi_meta = DatasetMetadata(
            dataset_name="Goals & Interests Dataset",
            version="v1.0",
            source_filename="goals_and_interests_10000_records.xlsx",
            total_records=gi_count,
            record_types="Goal, Interest",
            status="ready" if gi_count > 0 else "pending",
            notes="10,000 empirical goal and interest taxonomy records across 20 distinct life categories.",
        )
        db.add(gi_meta)
    else:
        gi_meta.total_records = gi_count
        gi_meta.status = "ready" if gi_count > 0 else "pending"

    # 2. Skills & Hobbies
    sh_meta = db.scalar(select(DatasetMetadata).where(DatasetMetadata.dataset_name == "Skills & Hobbies Dataset"))
    if not sh_meta:
        sh_meta = DatasetMetadata(
            dataset_name="Skills & Hobbies Dataset",
            version="v1.0",
            source_filename="skills_and_hobbies_5000_records.xlsx",
            total_records=sh_count,
            record_types="Skill, Hobby",
            status="ready" if sh_count > 0 else "pending",
            notes="5,000 structured skill and hobby profile taxonomy records with proficiency scores.",
        )
        db.add(sh_meta)
    else:
        sh_meta.total_records = sh_count
        sh_meta.status = "ready" if sh_count > 0 else "pending"

    db.commit()

    for m in [gi_meta, sh_meta]:
        results.append({
            "id": m.id,
            "dataset_name": m.dataset_name,
            "version": m.version,
            "source_filename": m.source_filename,
            "total_records": m.total_records,
            "record_types": m.record_types,
            "status": m.status,
            "imported_at": m.imported_at,
            "notes": m.notes,
        })
    return results

def get_dataset_inventory(db: Session) -> list[dict]:
    """Returns metadata for all imported datasets."""
    ensure_default_dataset_metadata(db)
    items = list(db.scalars(select(DatasetMetadata).order_by(DatasetMetadata.id.asc())))
    return [
        {
            "id": m.id,
            "dataset_name": m.dataset_name,
            "version": m.version,
            "source_filename": m.source_filename,
            "total_records": m.total_records,
            "record_types": m.record_types,
            "status": m.status,
            "imported_at": m.imported_at,
            "notes": m.notes,
        }
        for m in items
    ]
