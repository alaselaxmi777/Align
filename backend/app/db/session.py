from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

connect_args = {}
# For Neon PostgreSQL pooled connections (PgBouncer) and psycopg3:
# Disable client-side prepared statements to avoid prepared statement caching conflicts
if "psycopg" in settings.database_url or "neon.tech" in settings.database_url:
    connect_args["prepare_threshold"] = None

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
