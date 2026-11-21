# ALIGN — An Intent and Embedding-Based Framework for Personalized Community and Experience Discovery

ALIGN is a full-stack, AI-powered discovery platform that connects users with communities, experiences, events, third spaces, and peers based on their natural-language intent and semantic vector embeddings.

Built as a final-year B.Tech Computer Science and Engineering (Data Science) Capstone Project.

---

## 1. Key Features

- **Natural Language Multi-Intent Understanding**: Accepts unconstrained user statements (e.g. *"I want to learn artificial intelligence, meet programming enthusiasts and attend technology events near me"*), decomposing them into extracted interests, skills, action goals, entity targets, and location constraints.
- **Dense Vector Search with pgvector**: Uses `sentence-transformers/all-MiniLM-L6-v2` generating 384-dimensional unit embeddings stored in PostgreSQL with native cosine distance queries (`<=>`).
- **Explainable Hybrid Ranking Engine**: Combines dense semantic similarity (50%), lexical keyword alignment (25%), Neo4j structural network affinity (15%), and geospatial proximity (10%) with transparent match breakdowns.
- **Neo4j Knowledge Graph (368 Nodes, 597 Relationships)**: Real-time graph database linking users, communities, events, skills, goals, and interests with structural affinity scoring and bidirectional PostgreSQL synchronization.
- **15,000 Research Records Integrated**:
  - `goals_and_interests_10000_records.xlsx` (10,000 records + 64 goal master types + 72 interest master types)
  - `skills_and_hobbies_5000_records.xlsx` (5,000 records + 38 skill master types + 40 hobby master types)
- **Instagram-Inspired Canva Design System**:
  - **Light Mode**: Main `#FFFFFF`, Secondary `#F5F6FA`, Cards `#FFFFFF`, Text `#171717`, Accent `#5365F5`.
  - **Dark Mode**: Main `#0B0F14`, Secondary `#171B22`, Elevated `#242932`, Text `#F8FAFC`, Accent `#5365F5`.
  - Typography: **DM Sans** for user interface + **Fraunces** for editorial headings and card titles.
- **Complete Social & Video Discovery**:
  - Instagram 3-column photo grid and stream with interactive likes and comments.
  - Video Reels grid with view counts, tag filtering, audio tracks, and interactive video playback modal.
  - Unified `AppShell` with desktop/tablet sidebar, sticky topbar, and mobile bottom navigation.
- **Enterprise-Grade Security**:
  - Argon2id password hashing (OWASP standard) with backward-compatible bcrypt support.
  - Short-lived HS256 JWT access tokens.
  - Google OAuth 2.0 Identity Services verification using the official `google-auth` SDK.
  - Single-use cryptographically secure password reset flow.

---

## 2. Technology Stack

### Frontend
- **Framework**: React 18 with TypeScript 5.6
- **Build Tool**: Vite 5.4
- **Design System**: Canva Typography (DM Sans & Fraunces), Tailwind CSS 3.4, Custom CSS Variables
- **Icons**: Lucide React
- **Routing**: React Router v6

### Backend
- **Framework**: FastAPI (Python 3.12)
- **Database ORM**: SQLAlchemy 2.0 with type annotations
- **Migrations**: Alembic with version-controlled migrations
- **Graph Database Driver**: Neo4j Python Driver 5.28+
- **AI & NLP**: `sentence-transformers` (`all-MiniLM-L6-v2`), PyTorch, scikit-learn
- **Security**: `argon2-cffi`, `bcrypt`, `PyJWT`, `google-auth`, `cryptography`
- **Validation**: Pydantic v2 & Pydantic-Settings

### Database & Infrastructure
- **Relational & Vector**: PostgreSQL 16 with `pgvector 0.8.7` (`pgvector/pgvector:pg16` on port 5433)
- **Graph Database**: Neo4j 5 Community (`neo4j:5-community` on HTTP port 7474, Bolt port 7687)
- **Containerization**: Docker Compose (`db`, `neo4j`, `backend`, `frontend`)

---

## 3. Quick Start

### Option A: Running with Docker Compose (Recommended)

1. Open PowerShell in `D:\Align final\Align`.
2. Start the entire container stack:
   ```powershell
   docker compose up -d
   ```
3. Check running services:
   ```powershell
   docker compose ps
   ```
4. Access endpoints in your browser:
   - **Frontend Application**: [http://localhost:5173](http://localhost:5173)
   - **Backend Health & Verification**: [http://localhost:8000/health](http://localhost:8000/health)
   - **Interactive API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Neo4j Browser**: [http://localhost:7474](http://localhost:7474)

---

### Option B: Running Locally Outside Docker

1. Ensure PostgreSQL and Neo4j containers are active:
   ```powershell
   docker compose up -d db neo4j
   ```
2. Start the FastAPI backend:
   ```powershell
   $env:PYTHONPATH="backend"
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Start the React frontend:
   ```powershell
   cd frontend
   npm run dev
   ```

---

## 4. User Accounts & Privacy-First Philosophy

ALIGN operates strictly on real, user-owned accounts:
- **No Default Demo Account**: Every user registers their own account with Argon2id password hashing via `/register` or Google OAuth.
- **Developmental Seeding**: Optional dev seed data (`is_test=True`) can be generated in non-production environments using `python -m app.seed --dev-seed`. It is disabled by default and strictly refuses to run when `ENVIRONMENT=production`.

---

## 5. Running Automated Verification & Tests

### Backend Pytest Suite (102/102 Tests Passing)
```powershell
docker exec -e PYTHONPATH=/app align-backend-1 pytest
```

### Frontend Production Build
```powershell
cd frontend
npm run build
```

---

## 6. Real-Data Ingestion Pipelines & Hygiene Jobs

ALIGN operates strictly on verifiable, real-world data across external providers, relational tables, and vector stores.

### A. Environment Configuration (`.env`)
Refer to `.env.example` for all configurable environment variables:
- `EVENTBRITE_PRIVATE_TOKEN`: Live Eventbrite API token for fetching tech/community events.
- `KAGGLE_USERNAME` & `KAGGLE_KEY`: Credentials for querying Kaggle machine learning competitions.
- `GITHUB_TOKEN`: Personal access token for fetching open-source "good first issues" and hackathons.
- `NOMINATIM_USER_AGENT`: Custom identification string conforming to Nominatim OSM usage policies (1 req/sec strict rate-limiting).
- `INSTAGRAM_ENABLED`: Optional feature flag (`true`/`false`, default: `false`) controlling the Instagram API with Instagram Login integration.
- `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`, `INSTAGRAM_REDIRECT_URI`: Meta App credentials for Instagram OAuth 2.0.
- `TOKEN_ENCRYPTION_KEY`: 32 url-safe base64-encoded bytes for Fernet encryption of Instagram tokens at rest.

### B. Ingestion & Sync Commands
External integrations are encapsulated inside backend services and can be triggered via CLI or REST endpoints:

1. **Eventbrite Live Events Sync**:
   ```powershell
   # Sync upcoming tech events in Pune/Mumbai with 1-hour cache and deduplication
   curl -X POST "http://localhost:8000/api/v1/admin/sync/events?query=tech&location=Pune" -H "Authorization: Bearer <ADMIN_TOKEN>"
   ```

2. **OpenStreetMap Places & POI Ingestion**:
   ```powershell
   # Ingest verified colleges, coworking spaces, and IT parks within radius
   curl -X POST "http://localhost:8000/api/v1/admin/sync/places?city=Pune" -H "Authorization: Bearer <ADMIN_TOKEN>"
   ```

3. **Curated & Real-World Opportunities Pipeline**:
   ```powershell
   # Seed verified opportunities from CSV with verified URLs and fixed deadlines:
   curl -X POST "http://localhost:8000/api/v1/opportunities/seed-verified" -H "Authorization: Bearer <ADMIN_TOKEN>"

   # Ingest active Kaggle competitions:
   curl -X POST "http://localhost:8000/api/v1/opportunities/sync/kaggle" -H "Authorization: Bearer <ADMIN_TOKEN>"

   # Ingest verified GitHub open-source bounties & hackathons:
   curl -X POST "http://localhost:8000/api/v1/opportunities/sync/github" -H "Authorization: Bearer <ADMIN_TOKEN>"
   ```

4. **Nightly Expiration & Inactive Rows Deactivation**:
   ```powershell
   # Flags expired opportunities (deadline < NOW()) as is_active=False
   curl -X POST "http://localhost:8000/api/v1/opportunities/deactivate-expired" -H "Authorization: Bearer <ADMIN_TOKEN>"
   ```

5. **Test Data Audit & Cleanup Tool**:
   ```powershell
   # Dry-run audit of records flagged with is_test=True:
   docker exec -e PYTHONPATH=/app align-backend-1 python scripts/cleanup_test_data.py --dry-run

   # Execute permanent purging of flagged test rows:
   docker exec -e PYTHONPATH=/app align-backend-1 python scripts/cleanup_test_data.py --execute
   ```

### C. Data Health Observability Dashboard
Visit **`/admin/data-health`** in the web application (or `GET /api/v1/admin/data-health`) to inspect:
- Live external source status (Eventbrite, OSM/Overpass, Kaggle, GitHub, CSV seeds)
- Real vs. Test row breakdown across Users, Communities, Projects, Events, and Opportunities
- Expired and inactive watchdog metrics
- One-click trigger buttons for sync and deactivation jobs

---

## 7. Project Documentation Index

- [Comprehensive Project Audit (`FINAL_PROJECT_AUDIT.md`)](file:///d:/Align%20final/Align/FINAL_PROJECT_AUDIT.md)
- [Final Completion Report (`FINAL_COMPLETION_REPORT.md`)](file:///d:/Align%20final/Align/FINAL_COMPLETION_REPORT.md)
- [Empirical AI Model Evaluation (`AI_MODEL_EVALUATION.md`)](file:///d:/Align%20final/Align/AI_MODEL_EVALUATION.md)
- [System Architecture Specification (`docs/ARCHITECTURE.md`)](file:///d:/Align%20final/Align/docs/ARCHITECTURE.md)
- [Feature Implementation Status (`docs/FEATURE_STATUS.md`)](file:///d:/Align%20final/Align/docs/FEATURE_STATUS.md)
- [Testing & Verification Guide (`docs/TESTING.md`)](file:///d:/Align%20final/Align/docs/TESTING.md)
- [Database & Migrations Guide (`docs/DATABASE.md`)](file:///d:/Align%20final/Align/docs/DATABASE.md)
- [Instagram API Setup & OAuth Guide (`docs/INSTAGRAM_SETUP.md`)](file:///d:/Align%20final/Align/docs/INSTAGRAM_SETUP.md)
