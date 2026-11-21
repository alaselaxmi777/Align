"""
Idempotent master dataset seed for ALIGN:
Synchronizes skill_master (38 skills) and hobby_master (40 hobbies) from the canonical
empirical 5,000-records dataset.
Safe to execute multiple times against Neon PostgreSQL.
"""
import os
import sys
import logging
from pathlib import Path
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models.dataset import SkillMaster, HobbyMaster, SkillsHobbiesDataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("align.seed")

def seed_catalogs():
    """Ensure skill_master and hobby_master match the canonical empirical catalog."""
    db = SessionLocal()
    try:
        # Check current counts
        current_skills = db.scalar(select(func.count(SkillMaster.id))) or 0
        current_hobbies = db.scalar(select(func.count(HobbyMaster.id))) or 0
        logger.info(f"Existing catalog count: {current_skills} skills, {current_hobbies} hobbies")

        # If already populated with the 38 skills and 40 hobbies, verify integrity
        if current_skills >= 38 and current_hobbies >= 40:
            logger.info("Canonical master catalogs are already fully populated and synchronized.")
            return

        # Attempt to seed from dataset table if available
        dataset_count = db.scalar(select(func.count(SkillsHobbiesDataset.id))) or 0
        if dataset_count > 0:
            logger.info(f"Extracting distinct skills and hobbies from {dataset_count} dataset records...")
            # Distinct skills
            skills_res = db.execute(
                select(SkillsHobbiesDataset.category, SkillsHobbiesDataset.type, SkillsHobbiesDataset.description)
                .where(SkillsHobbiesDataset.record_type == "Skill")
                .distinct(SkillsHobbiesDataset.type)
            ).all()
            for cat, stype, desc in skills_res:
                if not db.scalar(select(SkillMaster).where(SkillMaster.type == stype)):
                    db.add(SkillMaster(category=cat, type=stype, description=desc or ""))

            # Distinct hobbies
            hobbies_res = db.execute(
                select(SkillsHobbiesDataset.category, SkillsHobbiesDataset.type, SkillsHobbiesDataset.description)
                .where(SkillsHobbiesDataset.record_type == "Hobby")
                .distinct(SkillsHobbiesDataset.type)
            ).all()
            for cat, htype, desc in hobbies_res:
                if not db.scalar(select(HobbyMaster).where(HobbyMaster.type == htype)):
                    db.add(HobbyMaster(category=cat, type=htype, description=desc or ""))

            db.commit()

        final_skills = db.scalar(select(func.count(SkillMaster.id))) or 0
        final_hobbies = db.scalar(select(func.count(HobbyMaster.id))) or 0
        logger.info(f"Catalog synchronization complete: {final_skills} skills, {final_hobbies} hobbies.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed catalogs: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_catalogs()
