import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, get_db
import app.models  # Register all models with Base.metadata
from app.api.routes import (
    auth,
    communities,
    events,
    discovery,
    saved,
    places,
    notifications,
    feed,
    messages,
    admin,
    users,
    graph,
    skills_hobbies,
    goals_interests,
    reels,
    uploads,
    assistant,
    matching,
    circles,
    goals,
    gamification,
    projects,
    opportunities,
    instagram,
    reports,
)

logger = logging.getLogger("align.database")

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.logging_config import setup_logging
    setup_logging(log_level=getattr(settings, "log_level", "INFO"))
    masked_url = engine.url.render_as_string(hide_password=True)
    logger.info("Initializing database connection: %s", masked_url)
    db_host = engine.url.host or ""
    db_name = engine.url.database or ""
    if not db_host.endswith(".neon.tech"):
        logger.warning(
            "[DATABASE WARNING] ALIGN is connected to '%s' (db: '%s') instead of Neon PostgreSQL. "
            "Neon PostgreSQL with pgvector is the required database platform.",
            db_host, db_name,
        )
    else:
        logger.info("[DATABASE OK] Connected to Neon PostgreSQL (host: '%s', db: '%s').", db_host, db_name)

    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            logger.info("PostgreSQL connection verified and 'vector' extension ready.")
            
            # Master Tables & Dataset Row Count Observability
            counts_query = text("""
                SELECT 
                    (SELECT count(*) FROM users) AS users_count,
                    (SELECT count(*) FROM communities) AS communities_count,
                    (SELECT count(*) FROM places) AS places_count,
                    (SELECT count(*) FROM skill_master) AS skill_master_count,
                    (SELECT count(*) FROM hobby_master) AS hobby_master_count,
                    (SELECT count(*) FROM skills_hobbies_dataset) AS sh_dataset_count,
                    (SELECT count(*) FROM goal_master) AS goal_master_count,
                    (SELECT count(*) FROM interest_master) AS interest_master_count,
                    (SELECT count(*) FROM goals_interests_dataset) AS gi_dataset_count
            """)
            stats = conn.execute(counts_query).mappings().first()
            if stats:
                logger.info(
                    "[NEONDB STATS] users: %d | communities: %d | places: %d | skill_master: %d | "
                    "hobby_master: %d | sh_dataset: %d | goal_master: %d | interest_master: %d | gi_dataset: %d",
                    stats["users_count"], stats["communities_count"], stats["places_count"],
                    stats["skill_master_count"], stats["hobby_master_count"], stats["sh_dataset_count"],
                    stats["goal_master_count"], stats["interest_master_count"], stats["gi_dataset_count"]
                )
                if stats["skill_master_count"] == 0 or stats["hobby_master_count"] == 0:
                    logger.warning("[CATALOG WARNING] Master tables are empty! Run: python app/scripts/seed_master_data.py")
    except Exception as exc:
        logger.critical("FATAL: Failed to connect to PostgreSQL at %s: %s", masked_url, exc)
        raise RuntimeError(f"Database connection failed: {exc}") from exc
    Base.metadata.create_all(bind=engine)

    # Storage Provider & Bucket Observability
    storage_provider = (os.getenv("STORAGE_PROVIDER") or "local").lower().strip()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    supabase_bucket = os.getenv("SUPABASE_BUCKET", "align-media")

    if storage_provider == "supabase" or (supabase_url and supabase_key):
        if not supabase_url or not supabase_key:
            logger.critical("[STORAGE ERROR] STORAGE_PROVIDER is 'supabase', but SUPABASE_URL or SUPABASE_SERVICE_KEY is missing!")
            raise RuntimeError("Missing required SUPABASE_URL or SUPABASE_SERVICE_KEY in environment.")
        logger.info("[STORAGE OK] Storage Provider: supabase | Bucket: %s", supabase_bucket)
    else:
        logger.info("[STORAGE INFO] Storage Provider: %s", storage_provider)

    yield

is_prod = settings.environment.lower() == "production"
app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="ALIGN — Intent- and Embedding-Based Framework for Personalized Community and Experience Discovery",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
    debug=False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
    # Strip server information banner to prevent fingerprinting
    if "server" in response.headers:
        del response.headers["server"]
    # CSP: default-src 'self' (permit swagger assets on docs endpoints)
    if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "connect-src 'self' http: https: ws: wss:; "
            "frame-ancestors 'none';"
        )
    return response

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(users.router, prefix=settings.api_v1_prefix)
app.include_router(communities.router, prefix=settings.api_v1_prefix)
app.include_router(events.router, prefix=settings.api_v1_prefix)
app.include_router(discovery.router, prefix=settings.api_v1_prefix)
app.include_router(saved.router, prefix=settings.api_v1_prefix)
app.include_router(places.router, prefix=settings.api_v1_prefix)
app.include_router(notifications.router, prefix=settings.api_v1_prefix)
app.include_router(feed.router, prefix=settings.api_v1_prefix)
app.include_router(reels.router, prefix=settings.api_v1_prefix)
app.include_router(messages.router, prefix=settings.api_v1_prefix)
app.include_router(graph.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(skills_hobbies.router, prefix=settings.api_v1_prefix)
# Direct /api prefix aliases for skill/hobby discovery
app.include_router(skills_hobbies.router, prefix="/api")
app.include_router(goals_interests.router, prefix=settings.api_v1_prefix)
# Direct /api prefix aliases for goals/interests discovery
app.include_router(goals_interests.router, prefix="/api")
app.include_router(uploads.router, prefix=settings.api_v1_prefix)
app.include_router(uploads.router, prefix="/api")
app.include_router(assistant.router, prefix=settings.api_v1_prefix)
app.include_router(matching.router, prefix=settings.api_v1_prefix)
app.include_router(circles.router, prefix=settings.api_v1_prefix)
app.include_router(goals.router, prefix=settings.api_v1_prefix)
app.include_router(gamification.router, prefix=settings.api_v1_prefix)
app.include_router(projects.router, prefix=settings.api_v1_prefix)
app.include_router(opportunities.router, prefix=settings.api_v1_prefix)
app.include_router(instagram.router, prefix=settings.api_v1_prefix)
app.include_router(reports.router, prefix=settings.api_v1_prefix)

# Persistent static file uploads directory
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.get("/health", tags=["system"])
@app.get(f"{settings.api_v1_prefix}/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        logger.error("Health check failed to query database: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Database connectivity check failed.",
        )

    from app.services.graph_service import graph_service
    g_health = graph_service.check_health()
    return {
        "status": "ok",
        "service": "align-api",
        "database": db_status,
        "database_platform": "neon-postgresql",
        "pgvector": "enabled",
        "storage": "supabase-storage",
        "graph_database": g_health.get("status", "unavailable"),
    }

TABLE_COUNT_QUERIES = {
    "users": text("SELECT count(*) FROM users"),
    "communities": text("SELECT count(*) FROM communities"),
    "events": text("SELECT count(*) FROM events"),
    "places": text("SELECT count(*) FROM places"),
    "recommendation_feedbacks": text("SELECT count(*) FROM recommendation_feedbacks"),
}

def _safe_count(table_name: str, db: Session) -> int:
    stmt = TABLE_COUNT_QUERIES.get(table_name)
    if stmt is None:
        return 0
    try:
        return db.execute(stmt).scalar() or 0
    except Exception:
        db.rollback()
        return 0

@app.get("/health/details", tags=["system"])
def health_details(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    from app.services.graph_service import graph_service
    from app.services.embeddings import get_embedding_cache_info, EMBEDDING_DIM
    g_health = graph_service.check_health()

    counts = {
        "users": _safe_count("users", db),
        "communities": _safe_count("communities", db),
        "events": _safe_count("events", db),
        "places": _safe_count("places", db),
        "feedback": _safe_count("recommendation_feedbacks", db),
    }

    return {
        "status": "healthy",
        "service": "align-api",
        "version": "0.2.0",
        "database": {
            "engine": "postgresql",
            "pgvector_extension": "active",
            "connection_status": "connected",
            "entity_counts": counts,
        },
        "graph_database": {
            "engine": "neo4j",
            "uri": g_health.get("uri", settings.neo4j_uri),
            "status": g_health.get("status", "unavailable"),
        },
        "embeddings": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "dimension": EMBEDDING_DIM,
            "cache": get_embedding_cache_info(),
        },
        "privacy": {
            "grid_snapping_precision_deg": 0.01,
            "coarse_resolution_km": 1.11,
            "public_coordinate_masking": "enforced",
        },
    }

@app.get("/metrics", tags=["system"])
def system_metrics(db: Session = Depends(get_db)):
    from app.services.embeddings import get_embedding_cache_info
    cache_info = get_embedding_cache_info()

    return {
        "align_embedding_cache_hits_total": cache_info.get("hits", 0),
        "align_embedding_cache_misses_total": cache_info.get("misses", 0),
        "align_embedding_cache_size": cache_info.get("currsize", 0),
        "align_users_total": _safe_count("users", db),
        "align_communities_total": _safe_count("communities", db),
        "align_events_total": _safe_count("events", db),
        "align_places_total": _safe_count("places", db),
        "align_recommendation_feedbacks_total": _safe_count("recommendation_feedbacks", db),
    }
