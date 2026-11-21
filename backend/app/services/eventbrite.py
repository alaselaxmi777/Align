import os
import json
import logging
import time
import urllib.request
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import delete, func, or_, select
from app.core.config import settings
from app.models.event import Event
from app.services.embeddings import cosine_similarity, generate_embedding

logger = logging.getLogger(__name__)

# In-memory 1-hour cache for remote Eventbrite provider responses
_EVENTBRITE_CACHE: dict[str, dict] = {}
CACHE_TTL_SECONDS: int = 3600  # 1 hour

def get_eventbrite_cache_stats() -> dict:
    """Returns runtime caching statistics for the Eventbrite integration."""
    return {
        "cached_queries_count": len(_EVENTBRITE_CACHE),
        "ttl_seconds": CACHE_TTL_SECONDS,
        "cached_queries": list(_EVENTBRITE_CACHE.keys()),
    }

DUMMY_EVENT_TITLES = [
    "Build Your First Vector Search & AI App",
    "Sinhagad Fort Sunrise Hike & Photography",
    "UX Case Study Review & Feedback Night",
]

def purge_dummy_events(db: Session) -> int:
    """Removes all synthetic/dummy events from the database."""
    total_removed = 0
    for dummy_title in DUMMY_EVENT_TITLES:
        res = db.execute(delete(Event).where(Event.title.ilike(f"%{dummy_title}%")))
        total_removed += res.rowcount or 0
    db.commit()
    logger.info(f"Purged {total_removed} dummy events from database.")
    return total_removed

def fetch_eventbrite_events(query: str = "tech", location: str = "") -> list[dict]:
    token = settings.eventbrite_private_token or os.getenv("EVENTBRITE_PRIVATE_TOKEN")
    if not token:
        logger.warning("EVENTBRITE_PRIVATE_TOKEN not configured. Skipping remote Eventbrite query.")
        return []

    cache_key = f"{query.strip().lower()}:{location.strip().lower()}"
    now_ts = time.time()
    cached = _EVENTBRITE_CACHE.get(cache_key)
    if cached and (now_ts - cached["timestamp"] < CACHE_TTL_SECONDS):
        logger.info(f"Using 1-hour cached Eventbrite results for '{cache_key}' ({len(cached['data'])} items)")
        return cached["data"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # If query is "all" or "recommended", search across multiple categories
    search_queries = [query]
    if query in ["all", "recommended", "realtime", "featured"]:
        search_queries = ["tech", "ai", "hackathon", "developer", "design", "startup"]

    all_results = []
    seen_ids = set()

    for q in search_queries:
        search_term = f"{q} {location}".strip() if location else q
        payload: dict = {
            "event_search": {
                "q": search_term,
                "dates": "current_future"
            }
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://www.eventbriteapi.com/v3/destination/search/",
            data=data_bytes,
            headers=headers,
            method="POST"
        )

        data = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    break
            except Exception as exc:
                if attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    logger.warning(f"Error fetching from Eventbrite API for query '{q}' after retries: {exc}")

        if data:
            results = data.get("events", {}).get("results", [])
            for evt in results:
                eid = evt.get("id") or evt.get("name")
                if eid and eid not in seen_ids:
                    seen_ids.add(eid)
                    all_results.append(evt)

    if all_results:
        _EVENTBRITE_CACHE[cache_key] = {"timestamp": now_ts, "data": all_results}

    return all_results

def sync_eventbrite_events(
    db: Session,
    query: str = "tech",
    location: str = "",
    purge_dummy: bool = True,
    min_relevance: float = 0.40,
) -> dict:
    purged_count = 0
    if purge_dummy:
        purged_count = purge_dummy_events(db)

    raw_events = fetch_eventbrite_events(query=query, location=location)
    if not raw_events:
        return {
            "status": "ok",
            "synced": 0,
            "purged_dummy": purged_count,
            "message": "No new events returned by Eventbrite."
        }

    synced_count = 0
    now_utc = datetime.now(timezone.utc)
    query_emb = generate_embedding(query.strip()) if query and query.lower() not in ["all", "realtime", "featured", "tech"] else None

    for item in raw_events:
        name = item.get("name")
        if not name:
            continue

        title = str(name).strip()[:160]
        eb_id = str(item.get("id") or item.get("eid") or item.get("eventbrite_event_id") or "").strip()

        # Deduplication Rule 1: by external_id (Eventbrite ID)
        if eb_id:
            existing_by_ext = db.scalar(select(Event.id).where(Event.external_id == eb_id))
            if existing_by_ext:
                continue

        # Parse start and end times
        starts_at = None
        s_date = item.get("start_date")
        s_time = item.get("start_time")
        if s_date:
            try:
                time_part = s_time if s_time else "00:00:00"
                if len(time_part) == 5:
                    time_part += ":00"
                dt_str = f"{s_date}T{time_part}"
                starts_at = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Drop past events
        if starts_at and starts_at < now_utc:
            continue

        # Deduplication Rule 2: by normalized title + start date
        norm_title = title.strip().lower()
        if starts_at:
            existing_dup = db.scalar(
                select(Event.id).where(func.lower(Event.title) == norm_title, Event.starts_at == starts_at)
            )
            if existing_dup:
                continue
        else:
            existing_dup = db.scalar(
                select(Event.id).where(func.lower(Event.title) == norm_title)
            )
            if existing_dup:
                continue

        summary = item.get("summary") or "Join us for this live event."
        url = item.get("url") or item.get("tickets_url") or ""

        # Build clean structured description containing Eventbrite ID and Ticket Link
        desc_parts = [summary]
        if eb_id:
            desc_parts.append(f"\n\nEventbrite ID: {eb_id}")
        if url:
            desc_parts.append(f"Event Link / Tickets: {url}")
        description = "\n".join(desc_parts)[:4000]

        # Location parsing
        is_online = item.get("is_online_event", False)
        loc_str = "Online"
        if not is_online:
            locs = item.get("locations", [])
            local_parts = [loc.get("name") for loc in locs if loc.get("name") and loc.get("type") in ["locality", "region", "country"]]
            loc_str = ", ".join(local_parts) if local_parts else (location or "In-Person")

        # Category from tags
        category = "Tech & Community"
        tag_names = []
        for tag in item.get("tags", []):
            dname = tag.get("display_name")
            if dname:
                tag_names.append(dname)
        if tag_names:
            category = tag_names[0][:80]

        ends_at = None
        e_date = item.get("end_date")
        e_time = item.get("end_time")
        if e_date:
            try:
                time_part = e_time if e_time else "23:59:59"
                if len(time_part) == 5:
                    time_part += ":00"
                dt_str = f"{e_date}T{time_part}"
                ends_at = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Vector embedding for semantic search
        text_for_embedding = f"{title} {summary} {' '.join(tag_names)} {loc_str}"
        emb = generate_embedding(text_for_embedding)

        # Configurable minimum relevance filter (default 0.40)
        if query_emb and emb:
            relevance = cosine_similarity(query_emb, emb)
            if relevance < min_relevance:
                continue

        event = Event(
            title=title,
            description=description,
            category=category,
            location=loc_str[:160],
            starts_at=starts_at,
            ends_at=ends_at,
            capacity=100,
            embedding=emb,
            source="Eventbrite",
            external_id=eb_id if eb_id else None,
            event_url=url if url else None,
        )
        db.add(event)
        synced_count += 1

    db.commit()
    return {
        "status": "success",
        "synced": synced_count,
        "message": f"Successfully synced {synced_count} real-time events from Eventbrite."
    }
