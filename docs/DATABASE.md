# ALIGN Database & Migrations Guide

## 1. Relational Schema Architecture

The ALIGN PostgreSQL database schema stores all core entities, user profiles, intent vectors, and activity records.

```mermaid
erDiagram
    USERS ||--o| PROFILES : "has"
    USERS ||--o{ OAUTH_ACCOUNTS : "has"
    USERS ||--o{ COMMUNITY_MEMBERSHIPS : "joins"
    COMMUNITIES ||--o{ COMMUNITY_MEMBERSHIPS : "contains"
    USERS ||--o{ EVENT_REGISTRATIONS : "attends"
    EVENTS ||--o{ EVENT_REGISTRATIONS : "has"
    USERS ||--o{ SAVED_ITEMS : "bookmarks"
    USERS ||--o{ NOTIFICATIONS : "receives"
    USERS ||--o{ USER_PREFERENCES : "customizes"

    USERS {
        int id PK
        string name
        string email UK
        string password_hash
        boolean is_active
        boolean is_verified
        boolean is_admin
        datetime created_at
    }

    PROFILES {
        int id PK
        int user_id FK
        text bio
        string location
        float latitude
        float longitude
        text interests
        text skills
        text goals
        text preferred_activities
        vector embedding "dim 384"
    }

    COMMUNITIES {
        int id PK
        string name
        text description
        string category
        text tags
        string location
        vector embedding "dim 384"
        int created_by_id FK
    }

    EVENTS {
        int id PK
        string title
        text description
        string category
        string location
        datetime starts_at
        int capacity
        vector embedding "dim 384"
        int created_by_id FK
    }

    PLACES {
        int id PK
        string name
        text description
        string category
        string address
        string city
        float latitude
        float longitude
        vector embedding "dim 384"
    }

    SAVED_ITEMS {
        int id PK
        int user_id FK
        string item_type
        int item_id
        datetime created_at
    }
```

---

## 2. pgvector Setup & Indexing

ALIGN uses `pgvector` for similarity calculations.
Vectors are initialized in SQLAlchemy models using:
```python
from pgvector.sqlalchemy import Vector
embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
```

In SQL, cosine similarity queries run natively:
```sql
SELECT id, name, 1 - (embedding <=> :query_vector) AS similarity
FROM communities
WHERE embedding IS NOT NULL
ORDER BY embedding <=> :query_vector ASC
LIMIT 10;
```

---

## 3. Migration Commands

Alembic manages all schema changes. Migrations run automatically or manually:

### Apply Migrations:
```powershell
cd backend
$env:PYTHONPATH="."
alembic upgrade head
```

### Generate New Revision (after model changes):
```powershell
cd backend
$env:PYTHONPATH="."
alembic revision --autogenerate -m "describe_change"
```

### Rollback Last Migration:
```powershell
cd backend
$env:PYTHONPATH="."
alembic downgrade -1
```

---

## 4. Volume Persistence

The database files are stored in Docker's persistent volume:
`align_postgres_data:/var/lib/postgresql/data`

Data persists across `docker compose down` and container rebuilds. To restart services without losing records:
```powershell
docker compose down
docker compose up -d
```
