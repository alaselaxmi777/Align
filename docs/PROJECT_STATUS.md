# ALIGN Project Status & Current Capabilities

**Project**: ALIGN — An Intent and Embedding-Based Framework for Personalized Community and Experience Discovery  
**Degree Track**: B.Tech Data Science Final-Year Project  
**Date**: November 16, 2026  
**Status**: Active Development & Academic Rigor Hardening  

---

## 1. System Overview

ALIGN is a full-stack social discovery and collaboration platform built to connect users with communities, events, venues, and peers based on unstructured intent statements, dense semantic embeddings, and graph network signals.

### Technology Stack
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0 ORM, Alembic migrations.
- **Persistence & Vector Search**: PostgreSQL 16 + `pgvector` extension (384-dimensional dense vectors).
- **Graph Database**: Neo4j 5 Community with APOC plugins (`bolt://neo4j:7687`).
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`) with an offline deterministic vector fallback.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide icons.
- **Orchestration**: Docker Compose (4 services: `align-frontend`, `align-backend`, `align-db`, `align-neo4j`).

---

## 2. Currently Implemented Modules & Verification Status

| Module | Implementation Details | Verified Status |
|---|---|---|
| **Authentication & Users** | Argon2id password hashing, JWT access tokens, database refresh tokens, Google OAuth verification, user-scoped endpoints. | Tested (unit + integration tests) |
| **Communities & Discussions** | Community CRUD, member join/leave tracking with live DB counts, threaded discussion posts. | Tested |
| **Events & RSVP** | Event creation, capacity limits, registration with unique ticket codes, Eventbrite ingestion. | Tested |
| **Places & Map** | OpenStreetMap / Google Places ingestion with latitude/longitude coordinates, ratings, and saved items. | Tested |
| **Projects & Collaboration** | Project ideas, required skills, applications with accept/reject, project discussions. | Tested |
| **1:1 Direct Messaging** | Persistent user-to-user messages, timestamps, and real-time read/unread status. | Tested |
| **Notifications** | Multi-event notification triggers for connection requests, community joins, project applications, and event registrations. | Tested |
| **Gamification & XP** | Verified-only XP awards with idempotency keys (`dedup_key`) and immutable activity audit logs. | Tested |
| **Assistant V2** | Tool-calling multi-turn assistant with SSE streaming, persistent user-approved memories, and goal roadmaps. | Tested |
| **Hybrid Discovery Engine** | Combines semantic similarity (`all-MiniLM-L6-v2`), lexical keyword overlap, Neo4j graph signals, and haversine distance. | Implemented; undergoing academic benchmark overhaul |

---

## 3. Active Roadmap & Known Limitations Being Addressed

1. **Evaluation Benchmark Credibility (Phase 1)**:
   - *Previous state*: The legacy benchmark evaluated only 8 queries over 10 items, exhibited identical scores across paradigms, and contained label leakage in graph features.
   - *Active improvement*: Constructing a 100+ query benchmark over 300–500 items derived from the 15,000-record dataset (`goals_and_interests` and `skills_and_hobbies`), with strict train/val/test splits, unbiased graph extraction from train split only, Wilcoxon statistical tests, and real pgvector database latency benchmarks.

2. **Explainable AI (Phase 2)**:
   - Enhancing recommendation cards with exact linear Shapley decomposition (`score_breakdown`), matched terms, and human-readable graph paths.

3. **Privacy-Preserving Geolocation (Phase 3)**:
   - Implementing Duckham–Kulik style grid snapping and bounded noise so raw user coordinates never leave the API.

4. **Retrieval & Intent Classification (Phase 4)**:
   - Pushing shortlist vector retrieval down into PostgreSQL via pgvector HNSW indexing, and adding a machine-learning intent classifier to complement keyword rules.

5. **Frontend Polish & Hero Intent Search (Phase 5)**:
   - Redesigning the landing page hero around the core intent-search box, grouping sidebar navigation into logical categories, and integrating Recharts data visualizations.

6. **Security & Roles (Phase 6)**:
   - Implementing RBAC (`user`, `moderator`, `admin`), data import cleaning with quality reports, and expanded test coverage.
