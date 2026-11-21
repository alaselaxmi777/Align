# ALIGN Automated Testing & Verification Guide

## 1. Automated Test Suite

ALIGN includes a comprehensive test suite covering authentication, security, relational constraints, communities, events, bookmarks, semantic recommendation search, assistant intelligence, gamification, project collaboration, and multi-user isolation.

### Test Directory Structure:
- `backend/tests/conftest.py`: Test fixtures, test database setup, and FastAPI `TestClient` initialization.
- `backend/tests/test_assistant_v2.py`: Multi-turn conversation CRUD, SSE streaming, action cards, memory consent, prompt-injection defense.
- `backend/tests/test_auth_api.py`: Registration, login, duplicate email rejection (409), password reset, connections flow, onboarding embeddings.
- `backend/tests/test_communities_and_events.py`: Community lifecycle, join/leave, event RSVP, capacity limits.
- `backend/tests/test_discovery.py`: Cosine similarity, Haversine distance, embedding normalization, hybrid ranker.
- `backend/tests/test_e2e_workflows.py`: Complete multi-step user onboarding and discovery workflows.
- `backend/tests/test_goals_interests.py`: Dataset counts, categories, pagination, search filters, facets, and import idempotency.
- `backend/tests/test_graph.py`: Neo4j graph health, sync, traversal, and structural affinity endpoints.
- `backend/tests/test_nextgen_features.py`: Assistant features, people matching, interest circles, goal journeys, gamification.
- `backend/tests/test_phase1_security_and_reels.py`: Database reels persistence, token refresh lifecycle, sliding rate limiter, file magic-byte spoofing prevention, cross-user privacy.
- `backend/tests/test_phase2_workflows.py`: Core user profile counts, connection requests, community admin authorization, event capacity, place deduplication.
- `backend/tests/test_phase3_recommendations.py`: Recommendation pipeline validation across all entities, feedback loop.
- `backend/tests/test_phase5_collaboration.py`: Project lifecycle, applications, milestones, discussions, messaging read states, anti-duplicate XP protection, notification triggers.
- `backend/tests/test_phase6_18_scenarios.py`: 18 full end-to-end integration scenarios.
- `backend/tests/test_saved_and_notifications.py`: Bookmark lifecycle, discovery search endpoint.
- `backend/tests/test_security.py`: Argon2id password hashing, JWT creation, token randomness.
- `backend/tests/test_skills_hobbies.py`: Skills dataset verification, category APIs, search filters, and import idempotency.

---

## 2. Running Backend Tests

### Option A: Running inside Docker (Recommended)
```powershell
docker exec -e PYTHONPATH=. align-backend-1 pytest tests/ -v
```

### Option B: Running Locally Outside Docker
Ensure PostgreSQL (port 5433) and Neo4j (port 7687) are running, then:
```powershell
$env:PYTHONPATH="backend"
python -m pytest backend/tests -v
```

### Verified Test Suite Status:
```
======================== 72 passed in ~70s =========================
```

---

## 3. Running Frontend Production Build

Verify TypeScript compilation and Vite asset bundling:
```powershell
cd frontend
npm run build
```

### Verified Result:
```
vite v5.4.21 building for production...
✓ 1634 modules transformed.
✓ built in ~9s
```
