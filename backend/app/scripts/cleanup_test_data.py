"""Script to identify, flag, and optionally clean synthetic test/audit data from ALIGN.

Usage:
    # Dry-run inspection (default):
    python backend/app/scripts/cleanup_test_data.py

    # Explicit dry-run:
    python backend/app/scripts/cleanup_test_data.py --dry-run

    # Execute flag marking (sets is_test = True):
    python backend/app/scripts/cleanup_test_data.py --execute

    # Execute hard purge:
    python backend/app/scripts/cleanup_test_data.py --execute --purge
"""

import argparse
import logging
import re
import sys
from sqlalchemy import or_, select, text, delete
from app.db.session import SessionLocal
from app.models.user import User
from app.models.community import Community
from app.models.project import Project

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cleanup_test_data")

TEST_PATTERN = re.compile(r"(test|audit|[0-9]{7,})", re.IGNORECASE)

def is_test_string(val: str | None) -> bool:
    if not val:
        return False
    return bool(TEST_PATTERN.search(val))

def run_cleanup(dry_run: bool = True, purge: bool = False, db = None):
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    mode_str = "DRY RUN" if dry_run else "EXECUTE"
    logger.info(f"=== Starting ALIGN Test Data Audit ({mode_str} | Action: {'PURGE' if purge else 'FLAG is_test=True'}) ===")

    try:
        # 1. Audit Users
        all_users = list(db.scalars(select(User)))
        test_users = [
            u for u in all_users
            if is_test_string(u.name) or is_test_string(u.email) or getattr(u, "is_test", False)
        ]

        logger.info(f"Identified {len(test_users)} test users out of {len(all_users)} total users:")
        for u in test_users:
            logger.info(f"  - User ID {u.id}: '{u.name}' <{u.email}> (currently is_test={getattr(u, 'is_test', False)})")

        # 2. Audit Communities
        all_comms = list(db.scalars(select(Community)))
        test_comms = [
            c for c in all_comms
            if is_test_string(c.name) or getattr(c, "is_test", False)
        ]

        logger.info(f"Identified {len(test_comms)} test communities out of {len(all_comms)} total communities:")
        for c in test_comms:
            logger.info(f"  - Community ID {c.id}: '{c.name}' (Category: {c.category}, is_test={getattr(c, 'is_test', False)})")

        # 3. Audit Projects
        all_projects = list(db.scalars(select(Project)))
        test_projects = [
            p for p in all_projects
            if is_test_string(p.title) or getattr(p, "is_test", False)
        ]

        logger.info(f"Identified {len(test_projects)} test projects out of {len(all_projects)} total projects:")
        for p in test_projects:
            logger.info(f"  - Project ID {p.id}: '{p.title}' (Category: {p.category}, is_test={getattr(p, 'is_test', False)})")

        if dry_run:
            logger.info("\n>>> DRY RUN COMPLETED: No database changes were applied. Run with --execute to commit changes. <<<")
            return {
                "dry_run": True,
                "users_flagged": len(test_users),
                "communities_flagged": len(test_comms),
                "projects_flagged": len(test_projects),
            }

        # Execute modifications
        if purge:
            logger.info("\n>>> PURGING TEST ROWS FROM DATABASE <<<")
            # Delete test projects
            if test_projects:
                proj_ids = [p.id for p in test_projects]
                db.execute(delete(Project).where(Project.id.in_(proj_ids)))
                logger.info(f"Purged {len(proj_ids)} test projects.")

            # Delete test communities
            if test_comms:
                comm_ids = [c.id for c in test_comms]
                db.execute(delete(Community).where(Community.id.in_(comm_ids)))
                logger.info(f"Purged {len(comm_ids)} test communities.")

            # Delete test users (cascades memberships, messages, etc.)
            if test_users:
                user_ids = [u.id for u in test_users]
                db.execute(delete(User).where(User.id.in_(user_ids)))
                logger.info(f"Purged {len(user_ids)} test users.")
        else:
            logger.info("\n>>> MARKING is_test = TRUE ON IDENTIFIED TEST ROWS <<<")
            for u in test_users:
                u.is_test = True
            for c in test_comms:
                c.is_test = True
            for p in test_projects:
                p.is_test = True
            logger.info(f"Flagged {len(test_users)} users, {len(test_comms)} communities, {len(test_projects)} projects.")

        db.commit()
        logger.info(">>> EXECUTION COMPLETED: Changes committed to database successfully. <<<")
        return {
            "dry_run": False,
            "purged": purge,
            "users_affected": len(test_users),
            "communities_affected": len(test_comms),
            "projects_affected": len(test_projects),
        }

    except Exception as exc:
        db.rollback()
        logger.error(f"Error executing cleanup script: {exc}", exc_info=True)
        raise
    finally:
        if should_close:
            db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit and clean test data in ALIGN.")
    parser.add_argument("--execute", action="store_true", help="Apply modifications to the database (defaults to dry-run)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate audit without modifying data")
    parser.add_argument("--purge", action="store_true", help="Permanently delete test entities instead of marking is_test=True")

    args = parser.parse_args()
    dry_run = not args.execute or args.dry_run and not args.execute

    res = run_cleanup(dry_run=dry_run, purge=args.purge)
    sys.exit(0)
