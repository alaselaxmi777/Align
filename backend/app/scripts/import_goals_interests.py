import os
import sys
import logging
from typing import Any, Dict, List, Tuple
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import engine, SessionLocal
from app.models.dataset import GoalsInterestsDataset, GoalMaster, InterestMaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("align.importer.goals_interests")

DEFAULT_WORKBOOK_PATHS = [
    "goals_and_interests_10000_records.xlsx",
    "/app/goals_and_interests_10000_records.xlsx",
    "d:/Align final/Align/backend/goals_and_interests_10000_records.xlsx",
    "../goals_and_interests_10000_records.xlsx",
]


def find_workbook_path(explicit_path: str | None = None) -> str:
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path
    for p in DEFAULT_WORKBOOK_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        "Could not find 'goals_and_interests_10000_records.xlsx' in common workspace locations."
    )


def clean_str(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and __import__("math").isnan(val)):
        return None
    try:
        import math
        if isinstance(val, float) and math.isnan(val):
            return None
    except Exception:
        pass
    s = str(val).strip()
    return s if s else None


def validate_and_parse_record(row: Dict[str, Any], idx: int) -> Tuple[Dict[str, Any] | None, str | None]:
    record_id = clean_str(row.get("Record ID"))
    record_type = clean_str(row.get("Record Type"))
    category = clean_str(row.get("Category"))
    type_name = clean_str(row.get("Type"))
    description = clean_str(row.get("Description"))
    life_context = clean_str(row.get("Life Context"))
    timeline_engagement = clean_str(row.get("Timeline / Engagement Level"))
    priority_setting = clean_str(row.get("Priority / Setting"))
    status_frequency = clean_str(row.get("Status / Frequency"))
    primary_motivation = clean_str(row.get("Primary Motivation"))
    expanded_desc = clean_str(row.get("Expanded Record Description"))

    raw_score = row.get("Popularity Score (1-10)")
    try:
        popularity_score = int(raw_score)
        if popularity_score < 1 or popularity_score > 10:
            return None, f"Row {idx}: popularity_score {popularity_score} outside [1, 10]"
    except (ValueError, TypeError):
        return None, f"Row {idx}: invalid popularity_score {raw_score!r}"

    required_fields = {
        "Record ID": record_id,
        "Record Type": record_type,
        "Category": category,
        "Type": type_name,
        "Description": description,
        "Expanded Record Description": expanded_desc,
    }
    for field_name, field_val in required_fields.items():
        if not field_val:
            return None, f"Row {idx}: Missing mandatory field '{field_name}'"

    if record_type not in ("Goal", "Interest"):
        return None, f"Row {idx}: Unexpected record_type '{record_type}' (expected Goal or Interest)"

    parsed = {
        "record_id": record_id,
        "record_type": record_type,
        "category": category,
        "type": type_name,
        "description": description,
        "life_context": life_context,
        "timeline_engagement_level": timeline_engagement,
        "priority_setting": priority_setting,
        "status_frequency": status_frequency,
        "primary_motivation": primary_motivation,
        "popularity_score": popularity_score,
        "expanded_record_description": expanded_desc,
    }
    return parsed, None


def import_goals_and_interests(excel_path: str | None = None) -> Dict[str, Any]:
    file_path = find_workbook_path(excel_path)
    logger.info("Reading Excel workbook from: %s", file_path)

    xls = pd.ExcelFile(file_path)
    sheet_names = xls.sheet_names
    logger.info("Discovered sheets: %s", sheet_names)

    if "10000 Records" not in sheet_names:
        raise ValueError("Workbook is missing required sheet '10000 Records'")

    df_records = pd.read_excel(xls, sheet_name="10000 Records")
    df_goals = pd.read_excel(xls, sheet_name="Goal Master") if "Goal Master" in sheet_names else None
    df_interests = pd.read_excel(xls, sheet_name="Interest Master") if "Interest Master" in sheet_names else None

    logger.info("Loaded sheet '10000 Records' with %d rows", len(df_records))

    valid_records: List[Dict[str, Any]] = []
    skipped_records: List[str] = []
    seen_record_ids: set = set()

    for idx, row in df_records.iterrows():
        parsed, err = validate_and_parse_record(row.to_dict(), idx + 2)
        if err:
            skipped_records.append(err)
            continue
        rec_id = parsed["record_id"]
        if rec_id in seen_record_ids:
            skipped_records.append(f"Row {idx+2}: Duplicate Record ID '{rec_id}' in file")
            continue
        seen_record_ids.add(rec_id)
        valid_records.append(parsed)

    logger.info(
        "Validation complete: %d valid records, %d skipped/invalid",
        len(valid_records), len(skipped_records)
    )

    # Parse Goal Master
    goal_masters: List[Dict[str, Any]] = []
    seen_goals: set = set()
    if df_goals is not None:
        for _, row in df_goals.iterrows():
            cat = clean_str(row.get("Category"))
            typ = clean_str(row.get("Type"))
            desc = clean_str(row.get("Description"))
            if cat and typ and desc and typ not in seen_goals:
                seen_goals.add(typ)
                goal_masters.append({"category": cat, "type": typ, "description": desc})

    # Parse Interest Master
    interest_masters: List[Dict[str, Any]] = []
    seen_interests: set = set()
    if df_interests is not None:
        for _, row in df_interests.iterrows():
            cat = clean_str(row.get("Category"))
            typ = clean_str(row.get("Type"))
            desc = clean_str(row.get("Description"))
            if cat and typ and desc and typ not in seen_interests:
                seen_interests.add(typ)
                interest_masters.append({"category": cat, "type": typ, "description": desc})

    logger.info(
        "Master sheets parsed: %d goals, %d interests",
        len(goal_masters), len(interest_masters)
    )

    dataset_upserted = 0
    goal_master_upserted = 0
    interest_master_upserted = 0

    with SessionLocal() as db:
        with db.begin():
            # 1. Upsert Goal Master
            for gm in goal_masters:
                db.execute(
                    text("""
                        INSERT INTO goal_master (category, type, description, created_at)
                        VALUES (:category, :type, :description, NOW())
                        ON CONFLICT (type) DO UPDATE
                        SET category = EXCLUDED.category,
                            description = EXCLUDED.description;
                    """),
                    gm
                )
                goal_master_upserted += 1

            # 2. Upsert Interest Master
            for im in interest_masters:
                db.execute(
                    text("""
                        INSERT INTO interest_master (category, type, description, created_at)
                        VALUES (:category, :type, :description, NOW())
                        ON CONFLICT (type) DO UPDATE
                        SET category = EXCLUDED.category,
                            description = EXCLUDED.description;
                    """),
                    im
                )
                interest_master_upserted += 1

            # 3. Upsert GoalsInterestsDataset in batches
            batch_size = 500
            for i in range(0, len(valid_records), batch_size):
                batch = valid_records[i : i + batch_size]
                db.execute(
                    text("""
                        INSERT INTO goals_interests_dataset (
                            record_id, record_type, category, type, description,
                            life_context, timeline_engagement_level, priority_setting,
                            status_frequency, primary_motivation, popularity_score,
                            expanded_record_description, created_at
                        )
                        VALUES (
                            :record_id, :record_type, :category, :type, :description,
                            :life_context, :timeline_engagement_level, :priority_setting,
                            :status_frequency, :primary_motivation, :popularity_score,
                            :expanded_record_description, NOW()
                        )
                        ON CONFLICT (record_id) DO UPDATE
                        SET record_type = EXCLUDED.record_type,
                            category = EXCLUDED.category,
                            type = EXCLUDED.type,
                            description = EXCLUDED.description,
                            life_context = EXCLUDED.life_context,
                            timeline_engagement_level = EXCLUDED.timeline_engagement_level,
                            priority_setting = EXCLUDED.priority_setting,
                            status_frequency = EXCLUDED.status_frequency,
                            primary_motivation = EXCLUDED.primary_motivation,
                            popularity_score = EXCLUDED.popularity_score,
                            expanded_record_description = EXCLUDED.expanded_record_description;
                    """),
                    batch
                )
                dataset_upserted += len(batch)

    logger.info(
        "Import finished! Dataset records: %d, Goal Masters: %d, Interest Masters: %d",
        dataset_upserted, goal_master_upserted, interest_master_upserted
    )

    return {
        "status": "success",
        "file_path": file_path,
        "dataset_records_imported": dataset_upserted,
        "goal_masters_imported": goal_master_upserted,
        "interest_masters_imported": interest_master_upserted,
        "skipped_records_count": len(skipped_records),
        "skipped_records": skipped_records,
    }


if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    res = import_goals_and_interests(path_arg)
    print("\n--- IMPORT SUMMARY ---")
    print(f"Status: {res['status']}")
    print(f"Dataset Records: {res['dataset_records_imported']}")
    print(f"Goal Masters: {res['goal_masters_imported']}")
    print(f"Interest Masters: {res['interest_masters_imported']}")
    print(f"Skipped / Invalid: {res['skipped_records_count']}")
    if res["skipped_records"]:
        for s in res["skipped_records"][:10]:
            print(f"  - {s}")
