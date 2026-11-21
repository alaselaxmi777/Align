"""
ALIGN Maharashtra Synthetic Dataset Loader (v3.0).
Strictly developmental and evaluation only.
Refuses to execute when ENVIRONMENT=production.
Requires explicit --dev-seed CLI flag.
All records tagged is_test=True, source='synthetic_maharashtra'.
"""

import sys
import os
import json
import random
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete, func
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.community import Community, CommunityMembership
from app.models.event import Event
from app.models.user import User, Profile
from app.core.security import hash_password
from app.services.embeddings import generate_embedding, get_embedding_model, generate_deterministic_vector
from app.services.graph_service import graph_service

logger = logging.getLogger("seed_maharashtra")
logging.basicConfig(level=logging.INFO)

def batch_embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    if model is not None:
        try:
            vectors = model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
            return [[float(x) for x in v] for v in vectors]
        except Exception as e:
            logger.warning(f"Batch embedding failed: {e}. Falling back to deterministic vectors.")
    return [generate_deterministic_vector(t) for t in texts]

DATASET_DIR_CANDIDATES = [
    "/app/align_dataset_maharashtra",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "align_dataset_maharashtra")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "align_dataset_maharashtra")),
    "align_dataset_maharashtra",
]

def find_dataset_dir() -> str:
    for candidate in DATASET_DIR_CANDIDATES:
        if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "synthetic_communities.json")):
            return candidate
    raise FileNotFoundError(f"Could not locate align_dataset_maharashtra directory in: {DATASET_DIR_CANDIDATES}")

def purge_synthetic_maharashtra(db):
    """Purges prior synthetic Maharashtra records safely."""
    logger.info("Purging existing synthetic Maharashtra records...")
    db.execute(delete(Event).where(Event.source == "synthetic_maharashtra"))
    db.execute(delete(Community).where(Community.tags.ilike("%synthetic_maharashtra%") | (Community.is_test == True)))
    db.execute(delete(User).where(User.email.ilike("%@synthetic.maharashtra.local")))
    db.commit()
    logger.info("Prior synthetic records purged.")

def main():
    # 1. Environment Safety Gate
    if os.getenv("ENVIRONMENT", "").lower() == "production" or getattr(settings, "environment", "").lower() == "production":
        raise RuntimeError("ABORTED: Seeding synthetic or dev data is strictly forbidden in production environments.")

    # 2. Explicit CLI Flag Gate
    if "--dev-seed" not in sys.argv and os.getenv("DEV_SEED", "").lower() != "true":
        print(
            "SAFETY NOTICE: ALIGN operates as a real, data-driven platform. "
            "Synthetic Maharashtra dataset loading is disabled by default to prevent contaminating production databases. "
            "To explicitly seed developmental test records, run with: python -m app.seed_maharashtra --dev-seed"
        )
        return

    dataset_dir = find_dataset_dir()
    logger.info(f"Using Maharashtra dataset from: {dataset_dir}")

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if "--purge" in sys.argv:
            purge_synthetic_maharashtra(db)

        # 3. Create or find dev admin anchor for synthetic communities
        anchor_user = db.scalar(select(User).where(User.email == "dev_seed@align.local"))
        if not anchor_user:
            anchor_user = User(
                name="Dev Seed Anchor",
                email="dev_seed@align.local",
                password_hash=hash_password("AlignDev2026!"),
                is_active=True,
                is_verified=True,
                is_test=True,
            )
            db.add(anchor_user)
            db.flush()

        # 4. Load Synthetic Communities (400 records)
        comm_file = os.path.join(dataset_dir, "synthetic_communities.json")
        with open(comm_file, encoding="utf-8") as f:
            communities_data = json.load(f)

        logger.info(f"Loading {len(communities_data)} synthetic communities...")
        comm_id_map = {}
        to_insert_comms = []
        comm_contexts = []
        
        for item in communities_data:
            existing = db.scalar(select(Community).where(Community.name == item["name"]))
            if not existing:
                loc = item.get("location") or {}
                interests = item.get("interests", [])
                skills = item.get("skills_supported", [])
                tags_str = f"synthetic_maharashtra, {', '.join(interests + skills)}"
                ctx = f"{item['name']} {item['description']} {item.get('category', '')} {tags_str} {loc.get('city', '')}"
                to_insert_comms.append((item, loc, tags_str))
                comm_contexts.append(ctx)
            else:
                comm_id_map[item["id"]] = existing.id

        if comm_contexts:
            logger.info(f"Generating embeddings for {len(comm_contexts)} communities...")
            comm_embs = batch_embed(comm_contexts)
            for (item, loc, tags_str), emb in zip(to_insert_comms, comm_embs):
                comm = Community(
                    name=item["name"],
                    description=item["description"],
                    category=item.get("category", "General"),
                    tags=tags_str,
                    location=loc.get("city", "Maharashtra"),
                    latitude=loc.get("approx_lat"),
                    longitude=loc.get("approx_lng"),
                    is_private=item.get("privacy", "public") == "private",
                    is_test=True,
                    created_by_id=anchor_user.id,
                    embedding=emb,
                )
                db.add(comm)
                db.flush()
                comm_id_map[item["id"]] = comm.id

        db.commit()
        logger.info(f"Loaded {len(to_insert_comms)} new communities.")

        # 5. Load Synthetic Events (800 records)
        events_file = os.path.join(dataset_dir, "synthetic_events.json")
        with open(events_file, encoding="utf-8") as f:
            events_data = json.load(f)

        logger.info(f"Loading {len(events_data)} synthetic events...")
        to_insert_events = []
        event_contexts = []
        for item in events_data:
            existing = db.scalar(select(Event).where(Event.external_id == item["id"]))
            if not existing:
                loc = item.get("location") or {}
                days = item.get("days_from_now", 14)
                start_dt = datetime.now(timezone.utc) + timedelta(days=days)
                ctx = f"{item['title']} {item['description']} {item.get('category', '')} {loc.get('city', '')}"
                c_id = comm_id_map.get(item.get("community_id"))
                to_insert_events.append((item, loc, start_dt, c_id))
                event_contexts.append(ctx)

        if event_contexts:
            logger.info(f"Generating embeddings for {len(event_contexts)} events...")
            event_embs = batch_embed(event_contexts)
            for (item, loc, start_dt, c_id), emb in zip(to_insert_events, event_embs):
                event = Event(
                    title=item["title"],
                    description=item["description"],
                    category=item.get("category", "Meetup"),
                    location=loc.get("city", "Maharashtra"),
                    latitude=loc.get("approx_lat"),
                    longitude=loc.get("approx_lng"),
                    starts_at=start_dt,
                    capacity=item.get("capacity", 25),
                    is_cancelled=False,
                    source="synthetic_maharashtra",
                    external_id=item["id"],
                    community_id=c_id,
                    created_by_id=anchor_user.id,
                    embedding=emb,
                )
                db.add(event)

        db.commit()
        logger.info(f"Loaded {len(to_insert_events)} new events.")

        # 6. Load Synthetic Activities (500 records)
        act_file = os.path.join(dataset_dir, "synthetic_activities.json")
        with open(act_file, encoding="utf-8") as f:
            act_data = json.load(f)

        logger.info(f"Loading {len(act_data)} synthetic activities...")
        to_insert_acts = []
        act_contexts = []
        for item in act_data:
            existing = db.scalar(select(Event).where(Event.external_id == item["id"]))
            if not existing:
                loc = item.get("location") or {}
                start_dt = datetime.now(timezone.utc) + timedelta(days=random.randint(1, 45) if "random" in globals() else 10)
                ctx = f"{item['title']} {item['description']} Activity {loc.get('city', '')}"
                to_insert_acts.append((item, loc, start_dt))
                act_contexts.append(ctx)

        if act_contexts:
            logger.info(f"Generating embeddings for {len(act_contexts)} activities...")
            act_embs = batch_embed(act_contexts)
            for (item, loc, start_dt), emb in zip(to_insert_acts, act_embs):
                act = Event(
                    title=item["title"],
                    description=item["description"],
                    category="Activity",
                    location=loc.get("city", "Maharashtra"),
                    latitude=loc.get("approx_lat"),
                    longitude=loc.get("approx_lng"),
                    starts_at=start_dt,
                    capacity=20,
                    is_cancelled=False,
                    source="synthetic_maharashtra",
                    external_id=item["id"],
                    created_by_id=anchor_user.id,
                    embedding=emb,
                )
                db.add(act)

        db.commit()
        logger.info(f"Loaded {len(to_insert_acts)} new activities.")

        # 7. Load Synthetic Users (1,500 records)
        users_file = os.path.join(dataset_dir, "synthetic_users.json")
        with open(users_file, encoding="utf-8") as f:
            users_data = json.load(f)

        logger.info(f"Loading {len(users_data)} synthetic users...")
        to_insert_users = []
        user_contexts = []
        for item in users_data:
            synth_email = f"{item['id']}@synthetic.maharashtra.local"
            existing = db.scalar(select(User).where(User.email == synth_email))
            if not existing:
                loc = item.get("location") or {}
                bio = item.get("bio", "")
                interests = ", ".join(item.get("interests", []))
                skills = ", ".join(item.get("skills", []))
                goals = ", ".join(item.get("short_term_goals", []))
                ctx = f"{bio} {interests} {skills} {goals} {loc.get('city', 'Maharashtra')}"
                to_insert_users.append((item, loc, synth_email, bio, interests, skills, goals))
                user_contexts.append(ctx)

        if user_contexts:
            logger.info(f"Generating embeddings for {len(user_contexts)} user profiles...")
            user_embs = batch_embed(user_contexts)
            for (item, loc, synth_email, bio, interests, skills, goals), emb in zip(to_insert_users, user_embs):
                u = User(
                    name=item["display_name"],
                    email=synth_email,
                    password_hash=hash_password("SyntheticDev2026!"),
                    is_active=False,  # Inactive: synthetic profiles cannot log in
                    is_verified=False,
                    is_test=True,
                )
                db.add(u)
                db.flush()

                p = Profile(
                    user_id=u.id,
                    bio=bio,
                    location=loc.get("city", "Maharashtra"),
                    latitude=loc.get("approx_lat"),
                    longitude=loc.get("approx_lng"),
                    interests=interests,
                    skills=skills,
                    goals=goals,
                    onboarding_completed=True,
                    embedding=emb,
                )
                db.add(p)

        db.commit()
        logger.info(f"Loaded {len(to_insert_users)} synthetic users.")

    print(
        f"SUCCESS: Loaded Maharashtra synthetic dataset "
        f"({len(to_insert_comms)} communities, {len(to_insert_events)} events, {len(to_insert_acts)} activities, {len(to_insert_users)} users). "
        f"All rows marked is_test=True, source='synthetic_maharashtra'."
    )

if __name__ == "__main__":
    main()
