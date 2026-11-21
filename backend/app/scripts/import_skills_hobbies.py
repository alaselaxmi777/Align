import os
import sys
import logging
from typing import Any, Dict, List, Tuple
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import engine, SessionLocal
from app.models.dataset import SkillsHobbiesDataset, SkillMaster, HobbyMaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("align.importer")

DEFAULT_WORKBOOK_PATHS = [
    "skills_and_hobbies_5000_records.xlsx",
    "/app/skills_and_hobbies_5000_records.xlsx",
    "d:/Align final/Align/skills_and_hobbies_5000_records.xlsx",
    "../skills_and_hobbies_5000_records.xlsx",
]

def find_workbook_path(explicit_path: str | None = None) -> str:
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path
    for p in DEFAULT_WORKBOOK_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        "Could not find 'skills_and_hobbies_5000_records.xlsx' in common workspace locations."
    )

def clean_str(val: Any) -> str | None:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None

def validate_and_parse_record(row: Dict[str, Any], idx: int) -> Tuple[Dict[str, Any] | None, str | None]:
    record_id = clean_str(row.get("Record ID"))
    record_type = clean_str(row.get("Record Type"))
    category = clean_str(row.get("Category"))
    type_name = clean_str(row.get("Type"))
    description = clean_str(row.get("Description"))
    application_context = clean_str(row.get("Application Context"))
    proficiency_level = clean_str(row.get("Proficiency / Engagement Level"))
    setting = clean_str(row.get("Setting"))
    frequency = clean_str(row.get("Frequency"))
    primary_motivation = clean_str(row.get("Primary Motivation"))
    expanded_desc = clean_str(row.get("Expanded Record Description"))

    raw_score = row.get("Popularity Score (1-10)")
    try:
        popularity_score = int(raw_score)
        if popularity_score < 1 or popularity_score > 10:
            return None, f"Row {idx}: popularity_score {popularity_score} outside [1, 10]"
    except (ValueError, TypeError):
        return None, f"Row {idx}: invalid popularity_score {raw_score}"

    required_fields = {
        "Record ID": record_id,
        "Record Type": record_type,
        "Category": category,
        "Type": type_name,
        "Description": description,
        "Application Context": application_context,
        "Proficiency / Engagement Level": proficiency_level,
        "Setting": setting,
        "Expanded Record Description": expanded_desc,
    }
    for field_name, field_val in required_fields.items():
        if not field_val:
            return None, f"Row {idx}: Missing mandatory field '{field_name}'"

    if record_type not in ("Skill", "Hobby"):
        return None, f"Row {idx}: Unexpected record_type '{record_type}' (expected Skill or Hobby)"

    parsed = {
        "record_id": record_id,
        "record_type": record_type,
        "category": category,
        "type": type_name,
        "description": description,
        "application_context": application_context,
        "proficiency_engagement_level": proficiency_level,
        "setting": setting,
        "frequency": frequency,
        "primary_motivation": primary_motivation,
        "popularity_score": popularity_score,
        "expanded_record_description": expanded_desc,
    }
    return parsed, None

def import_skills_and_hobbies(excel_path: str | None = None) -> Dict[str, Any]:
    file_path = find_workbook_path(excel_path)
    logger.info("Reading Excel workbook from: %s", file_path)

    # Load sheets via pandas
    xls = pd.ExcelFile(file_path)
    sheet_names = xls.sheet_names
    logger.info("Discovered sheets: %s", sheet_names)

    if "5000 Records" not in sheet_names:
        raise ValueError("Workbook is missing required sheet '5000 Records'")

    df_records = pd.read_excel(xls, sheet_name="5000 Records")
    df_skills = pd.read_excel(xls, sheet_name="Skill Master") if "Skill Master" in sheet_names else None
    df_hobbies = pd.read_excel(xls, sheet_name="Hobby Master") if "Hobby Master" in sheet_names else None

    logger.info("Loaded sheet '5000 Records' with %d rows", len(df_records))

    valid_records: List[Dict[str, Any]] = []
    skipped_records: List[str] = []
    seen_record_ids = set()

    for idx, row in df_records.iterrows():
        parsed, err = validate_and_parse_record(row.to_dict(), idx + 2)
        if err:
            skipped_records.append(err)
            continue
        rec_id = parsed["record_id"]
        if rec_id in seen_record_ids:
            skipped_records.append(f"Row {idx+2}: Duplicate Record ID '{rec_id}' encountered in file")
            continue
        seen_record_ids.add(rec_id)
        valid_records.append(parsed)

    logger.info("Validation complete: %d valid records, %d skipped/invalid", len(valid_records), len(skipped_records))

    # Parse Master sheets
    skill_masters: List[Dict[str, Any]] = []
    seen_skills = set()
    if df_skills is not None:
        for _, row in df_skills.iterrows():
            cat = clean_str(row.get("Category"))
            typ = clean_str(row.get("Type"))
            desc = clean_str(row.get("Description"))
            if cat and typ and desc and typ not in seen_skills:
                seen_skills.add(typ)
                skill_masters.append({"category": cat, "type": typ, "description": desc})

    hobby_masters: List[Dict[str, Any]] = []
    seen_hobbies = set()
    if df_hobbies is not None:
        for _, row in df_hobbies.iterrows():
            cat = clean_str(row.get("Category"))
            typ = clean_str(row.get("Type"))
            desc = clean_str(row.get("Description"))
            if cat and typ and desc and typ not in seen_hobbies:
                seen_hobbies.add(typ)
                hobby_masters.append({"category": cat, "type": typ, "description": desc})

    logger.info("Master sheets parsed: %d skills, %d hobbies", len(skill_masters), len(hobby_masters))

    # Perform atomic transactional upsert
    dataset_upserted = 0
    skill_master_upserted = 0
    hobby_master_upserted = 0

    with SessionLocal() as db:
        with db.begin():
            # 1. Upsert Skill Master
            for sm in skill_masters:
                db.execute(
                    text("""
                        INSERT INTO skill_master (category, type, description, created_at)
                        VALUES (:category, :type, :description, NOW())
                        ON CONFLICT (type) DO UPDATE
                        SET category = EXCLUDED.category,
                            description = EXCLUDED.description;
                    """),
                    sm
                )
                skill_master_upserted += 1

            # 2. Upsert Hobby Master
            for hm in hobby_masters:
                db.execute(
                    text("""
                        INSERT INTO hobby_master (category, type, description, created_at)
                        VALUES (:category, :type, :description, NOW())
                        ON CONFLICT (type) DO UPDATE
                        SET category = EXCLUDED.category,
                            description = EXCLUDED.description;
                    """),
                    hm
                )
                hobby_master_upserted += 1

            # 3. Upsert SkillsHobbiesDataset (batch execution for high performance)
            batch_size = 500
            for i in range(0, len(valid_records), batch_size):
                batch = valid_records[i : i + batch_size]
                db.execute(
                    text("""
                        INSERT INTO skills_hobbies_dataset (
                            record_id, record_type, category, type, description,
                            application_context, proficiency_engagement_level, setting,
                            frequency, primary_motivation, popularity_score,
                            expanded_record_description, created_at
                        )
                        VALUES (
                            :record_id, :record_type, :category, :type, :description,
                            :application_context, :proficiency_engagement_level, :setting,
                            :frequency, :primary_motivation, :popularity_score,
                            :expanded_record_description, NOW()
                        )
                        ON CONFLICT (record_id) DO UPDATE
                        SET record_type = EXCLUDED.record_type,
                            category = EXCLUDED.category,
                            type = EXCLUDED.type,
                            description = EXCLUDED.description,
                            application_context = EXCLUDED.application_context,
                            proficiency_engagement_level = EXCLUDED.proficiency_engagement_level,
                            setting = EXCLUDED.setting,
                            frequency = EXCLUDED.frequency,
                            primary_motivation = EXCLUDED.primary_motivation,
                            popularity_score = EXCLUDED.popularity_score,
                            expanded_record_description = EXCLUDED.expanded_record_description;
                    """),
                    batch
                )
                dataset_upserted += len(batch)

    logger.info(
        "Import successfully finished! Dataset records: %d, Skill Masters: %d, Hobby Masters: %d",
        dataset_upserted,
        skill_master_upserted,
        hobby_master_upserted
    )

    return {
        "status": "success",
        "file_path": file_path,
        "dataset_records_imported": dataset_upserted,
        "skill_masters_imported": skill_master_upserted,
        "hobby_masters_imported": hobby_master_upserted,
        "skipped_records_count": len(skipped_records),
        "skipped_records": skipped_records,
    }

if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    res = import_skills_and_hobbies(path_arg)
    print("\n--- IMPORT SUMMARY ---")
    print(f"Status: {res['status']}")
    print(f"Dataset Records: {res['dataset_records_imported']}")
    print(f"Skill Masters: {res['skill_masters_imported']}")
    print(f"Hobby Masters: {res['hobby_masters_imported']}")
    print(f"Skipped / Invalid: {res['skipped_records_count']}")
    if res['skipped_records']:
        for s in res['skipped_records'][:10]:
            print(f"  - {s}")
