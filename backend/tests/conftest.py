import os
from urllib.parse import urlsplit, urlunsplit

# Tests must never connect to the main application database.
source_url = os.environ.get("DATABASE_URL")

if not source_url:
    raise RuntimeError(
        "DATABASE_URL is missing. Run pytest inside the ALIGN backend container."
    )

parts = urlsplit(source_url)
current_database = parts.path.lstrip("/")

if current_database not in {"align_db", "align_test_db"}:
    raise RuntimeError(
        f"Refusing to run tests against unexpected database: {current_database}"
    )

test_url = urlunsplit(parts._replace(path="/align_test_db"))
os.environ["DATABASE_URL"] = test_url

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.core.security import create_access_token
from app.scripts.import_skills_hobbies import import_skills_and_hobbies
from app.scripts.import_goals_interests import import_goals_and_interests


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS hobbies TEXT DEFAULT '';"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS skill_proficiency VARCHAR(64) DEFAULT '';"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS hobby_engagement_level VARCHAR(64) DEFAULT '';"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS location_privacy VARCHAR(30) DEFAULT 'approximate';"))
        conn.execute(text("ALTER TABLE places ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);"))
        conn.execute(text("ALTER TABLE user_activity_logs ADD COLUMN IF NOT EXISTS dedup_key VARCHAR(128);"))
        conn.execute(text("ALTER TABLE goals_interests_dataset ADD COLUMN IF NOT EXISTS embedding vector(384);"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE communities ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;"))
        conn.execute(text("ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ DEFAULT NOW();"))
        conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS external_id VARCHAR(120);"))
        conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS visibility VARCHAR(20) DEFAULT 'connections_only';"))
        conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS location_area VARCHAR(120);"))
        conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding vector(384);"))
        conn.execute(text("ALTER TABLE reels ADD COLUMN IF NOT EXISTS duration_seconds FLOAT;"))
        conn.execute(text("ALTER TABLE reels ADD COLUMN IF NOT EXISTS visibility VARCHAR(20) DEFAULT 'public';"))
        conn.execute(text("ALTER TABLE reels ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE reels ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE reels ADD COLUMN IF NOT EXISTS embedding vector(384);"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS instagram_recommendations_enabled BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS instagram_profile_visible BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE post_comments ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES post_comments(id) ON DELETE CASCADE;"))
        conn.execute(text("ALTER TABLE reel_comments ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES reel_comments(id) ON DELETE CASCADE;"))
        conn.execute(text("ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS target_type VARCHAR(30) DEFAULT 'user';"))
        conn.execute(text("ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS post_id INTEGER REFERENCES posts(id) ON DELETE SET NULL;"))
        conn.execute(text("ALTER TABLE user_reports ADD COLUMN IF NOT EXISTS reel_id INTEGER REFERENCES reels(id) ON DELETE SET NULL;"))
        conn.execute(text("ALTER TABLE user_reports ALTER COLUMN reported_user_id DROP NOT NULL;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(50);"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS age_cohort VARCHAR(32);"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS gender VARCHAR(32);"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(32) DEFAULT 'English';"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS onboarding_step INTEGER DEFAULT 1;"))
        conn.execute(text("TRUNCATE TABLE users CASCADE;"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    import_skills_and_hobbies()
    import_goals_and_interests()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def auth_headers(db):
    from sqlalchemy import select
    from app.models.user import User

    user = db.scalar(select(User).order_by(User.id.asc()))

    if not user:
        from app.core.security import hash_password

        user = User(
            name="Test User",
            email="test_fixture@align.local",
            password_hash=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}
