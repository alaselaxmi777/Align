import csv
import io
import json
import logging
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func
from app.core.config import settings
from app.models.opportunity import Opportunity
from app.services.embeddings import generate_embedding

logger = logging.getLogger(__name__)

def parse_iso_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str or not dt_str.strip():
        return None
    cleaned = dt_str.strip()
    try:
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        return datetime.fromisoformat(cleaned).astimezone(timezone.utc)
    except Exception as exc:
        logger.warning(f"Failed to parse datetime '{dt_str}': {exc}")
        return None

def import_opportunities_from_csv(csv_content: str, db: Session) -> dict:
    """Parses, validates, and imports opportunities from CSV content."""
    reader = csv.DictReader(io.StringIO(csv_content))
    imported = 0
    skipped = 0
    now = datetime.now(timezone.utc)

    for row in reader:
        title = (row.get("title") or "").strip()
        org = (row.get("organization") or row.get("org") or "").strip()
        apply_url = (row.get("apply_url") or row.get("source_url") or "").strip()
        if not title or not org or not apply_url:
            skipped += 1
            continue

        opp_type = (row.get("opportunity_type") or row.get("type") or "hackathon").strip().lower()
        desc = (row.get("description") or f"{opp_type.title()} by {org}.").strip()
        loc = (row.get("location") or "Remote / Global").strip()
        is_remote_val = str(row.get("is_remote") or row.get("remote_eligible") or "true").lower() in ("true", "1", "yes")
        deadline = parse_iso_datetime(row.get("deadline"))
        reward = (row.get("stipend_or_prize") or row.get("reward") or "").strip() or None
        tags = (row.get("tags") or "").strip()
        source = (row.get("source") or "Verified CSV").strip()

        # Check for existing duplicate by apply_url or title
        existing = db.scalar(
            select(Opportunity).where(
                (Opportunity.apply_url == apply_url) | (func.lower(Opportunity.title) == title.lower())
            )
        )
        if existing:
            # Update existing with latest verified timestamp
            existing.last_verified_at = now
            skipped += 1
            continue

        ctx = f"{title} {org} {opp_type} {desc} {tags} {loc}"
        emb = generate_embedding(ctx)

        opp = Opportunity(
            title=title,
            organization=org,
            opportunity_type=opp_type,
            description=desc,
            location=loc,
            is_remote=is_remote_val,
            deadline=deadline,
            stipend_or_prize=reward,
            apply_url=apply_url,
            tags=tags,
            source=source,
            is_active=True if not deadline or deadline >= now else False,
            last_verified_at=now,
            embedding=emb,
        )
        db.add(opp)
        imported += 1

    if imported > 0:
        db.commit()

    return {"imported": imported, "skipped": skipped}

def seed_verified_opportunities(db: Session) -> int:
    """Seeds verified external opportunities from verified_opportunities.csv."""
    # Look for the verified CSV in standard data locations
    potential_paths = [
        Path(__file__).parent.parent / "data" / "verified_opportunities.csv",
        Path("/app/app/data/verified_opportunities.csv"),
        Path("backend/app/data/verified_opportunities.csv"),
    ]

    csv_file = None
    for p in potential_paths:
        if p.exists():
            csv_file = p
            break

    if not csv_file:
        logger.warning("verified_opportunities.csv not found in standard locations.")
        return 0

    try:
        content = csv_file.read_text(encoding="utf-8")
        res = import_opportunities_from_csv(content, db)
        logger.info(f"Seeded verified opportunities from CSV: {res}")
        return res["imported"]
    except Exception as exc:
        logger.error(f"Error seeding opportunities from CSV: {exc}", exc_info=True)
        return 0

def ingest_kaggle_opportunities(db: Session) -> dict:
    """Ingests real competitive machine learning competitions from Kaggle API."""
    username = settings.kaggle_username or os.getenv("KAGGLE_USERNAME")
    key = settings.kaggle_key or os.getenv("KAGGLE_KEY")

    if not username or not key:
        logger.info("Kaggle credentials not configured in environment. Skipping Kaggle ingestion.")
        return {"status": "skipped", "message": "Kaggle credentials not provided in .env"}

    import base64
    auth_header = "Basic " + base64.b64encode(f"{username}:{key}".encode("utf-8")).decode("utf-8")
    req = urllib.request.Request(
        "https://www.kaggle.com/api/v1/competitions/list?sortBy=latestDeadline",
        headers={"Authorization": auth_header, "User-Agent": "ALIGN-Platform"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            imported = 0
            now = datetime.now(timezone.utc)
            for item in data[:15]:
                title = item.get("title") or item.get("ref")
                if not title:
                    continue
                url = item.get("url") or f"https://www.kaggle.com/competitions/{item.get('ref')}"
                existing = db.scalar(select(Opportunity.id).where(Opportunity.apply_url == url))
                if existing:
                    continue

                deadline = parse_iso_datetime(item.get("deadline"))
                if deadline and deadline < now:
                    continue

                reward = item.get("reward") or "Medals & Knowledge"
                desc = item.get("description") or f"Official Kaggle Machine Learning challenge: {title}"
                tags = "Kaggle, MachineLearning, DataScience, Python"
                ctx = f"{title} Kaggle competition {desc} {tags}"
                emb = generate_embedding(ctx)

                opp = Opportunity(
                    title=title[:200],
                    organization="Kaggle & Partners",
                    opportunity_type="competition",
                    description=desc[:4000],
                    location="Online / Global",
                    is_remote=True,
                    deadline=deadline,
                    stipend_or_prize=reward[:120],
                    apply_url=url[:500],
                    tags=tags,
                    source="Kaggle API",
                    is_active=True,
                    last_verified_at=now,
                    embedding=emb,
                )
                db.add(opp)
                imported += 1

            if imported > 0:
                db.commit()
            return {"status": "success", "imported": imported}
    except Exception as exc:
        logger.warning(f"Kaggle API ingestion failed: {exc}")
        return {"status": "error", "message": str(exc)}

def ingest_github_opportunities(db: Session) -> dict:
    """Ingests open hackathons, student programs, and bounty grants from GitHub API."""
    token = settings.github_token or os.getenv("GITHUB_TOKEN")
    headers = {"User-Agent": "ALIGN-Platform", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        "https://api.github.com/search/repositories?q=topic:hackathon+stars:%3E100&sort=updated&order=desc",
        headers=headers
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("items", [])
            imported = 0
            now = datetime.now(timezone.utc)
            for repo in items[:8]:
                repo_url = repo.get("html_url")
                if not repo_url:
                    continue
                existing = db.scalar(select(Opportunity.id).where(Opportunity.apply_url == repo_url))
                if existing:
                    continue

                title = f"{repo.get('name').replace('-', ' ').title()} Open Hackathon"
                org = repo.get("owner", {}).get("login", "Open Source Initiative")
                desc = repo.get("description") or f"Global open-source community hackathon and developer challenge."
                tags = ", ".join(repo.get("topics", ["OpenSource", "GitHub"])[:5])
                ctx = f"{title} {org} hackathon {desc} {tags}"
                emb = generate_embedding(ctx)

                opp = Opportunity(
                    title=title[:200],
                    organization=org[:160],
                    opportunity_type="hackathon",
                    description=desc[:4000],
                    location="Online / Global",
                    is_remote=True,
                    deadline=None,  # Continuous
                    stipend_or_prize="GitHub Swag & Community Grants",
                    apply_url=repo_url[:500],
                    tags=tags,
                    source="GitHub API",
                    is_active=True,
                    last_verified_at=now,
                    embedding=emb,
                )
                db.add(opp)
                imported += 1

            if imported > 0:
                db.commit()
            return {"status": "success", "imported": imported}
    except Exception as exc:
        logger.warning(f"GitHub opportunities ingestion failed: {exc}")
        return {"status": "error", "message": str(exc)}

def deactivate_expired_opportunities(db: Session) -> int:
    """Nightly job / maintenance task: deactivates expired opportunity rows."""
    now = datetime.now(timezone.utc)
    res = db.execute(
        update(Opportunity)
        .where(Opportunity.is_active == True, Opportunity.deadline.isnot(None), Opportunity.deadline < now)
        .values(is_active=False)
    )
    db.commit()
    logger.info(f"Deactivated {res.rowcount} expired opportunities.")
    return res.rowcount or 0
