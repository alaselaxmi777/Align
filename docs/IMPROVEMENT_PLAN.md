# ALIGN Improvement Plan & Roadmap

**Project**: ALIGN — An Intent and Embedding-Based Framework for Personalized Community and Experience Discovery  
**Author**: Senior Full-Stack + ML Engineer  
**Date**: November 16, 2026  
**Status**: In Progress  

---

## High-Level Objectives & Ground Rules

1. **Empirical Rigor & Honesty**: All numbers reported in evaluation and documentation must be genuine, measured from reproducible test scripts, with standard deviations and significance tests. Any case where the proposed hybrid model does not beat a baseline must be explicitly stated.
2. **Strict Verification**: No phase is marked done until backend tests (`pytest`) pass and frontend build (`npm run build`) succeeds.
3. **Design Language Continuity**: Preserve the visual branding (dark/light themes, DM Sans + Fraunces typography, violet accent).
4. **Security & Secrets Hygiene**: Zero secrets committed; placeholders only in `.env.example`; `.gitignore` covers `.env`, `.pytest_cache`, `__pycache__`, `node_modules`, `dist`.
5. **Phase-by-Phase Reviewable Commits**: Exactly one clean commit per phase.

---

## Phase Checklist

### Phase 0: Cleanup & Baseline Audit
- [ ] Delete nested duplicate folder `Align/Align`.
- [ ] Delete `backend/tests/conftest.py.backup`.
- [ ] Delete redundant report files across root and `docs/` (`FINAL_*`, `NEXTGEN_*`, `REAL_DATA_*`, root duplicates).
- [ ] Keep canonical documentation: `README.md` (root), `docs/ARCHITECTURE.md`, `docs/PROJECT_STATUS.md`, `docs/TESTING.md`.
- [ ] Rewrite `docs/PROJECT_STATUS.md` so every claim accurately reflects code without unverified marketing claims.
- [ ] Verify test suite & frontend build; commit Phase 0.

### Phase 1: Credible Benchmark & Academic Evaluation
- [ ] Construct expanded benchmark dataset: 100–200 realistic intent queries over 300–500 items derived from `goals_and_interests` (10k) and `skills_and_hobbies` (5k) master records with fixed random seed (42).
- [ ] Include semantically challenging "hard" queries with minimal lexical overlap (e.g. stress relief, creative inspiration).
- [ ] Build train/validation/test split (60/20/20).
- [ ] Extract real Neo4j graph co-occurrence / 2-hop connectivity from the TRAIN split only (strictly zero label leakage).
- [ ] Comprehensive ablation study:
  - Lexical (BM25/token Jaccard)
  - Dense (Sentence-Transformers `all-MiniLM-L6-v2`)
  - Hybrid (Dense + Lexical)
  - Dense + Lexical + Graph
  - Dense + Lexical + Graph + Geo
  - Full Framework (+ Feedback)
- [ ] Metrics: Precision@K, Recall@K, F1@K, HitRate@K, NDCG@K, MRR ($K \in \{3, 5, 10\}$), Catalog Diversity (Intra-List Distance), Novelty (Self-Information).
- [ ] Statistical significance testing: 5-seed mean ± std and Wilcoxon signed-rank test ($p$-value) between full framework and best baseline.
- [ ] Score weight optimization: Grid search on validation split only, then single unbiased evaluation on test split.
- [ ] Real pgvector retrieval latency: Benchmark `ORDER BY embedding <=> :q LIMIT 50` + re-rank over $\ge 10,000$ catalog rows; report p50 and p95 latencies.
- [ ] Automated generation: `python -m app.evaluation.run_all` generating `docs/AI_EVALUATION.md`, `docs/evaluation_results.csv`, and `docs/evaluation_charts.png`.
- [ ] Verify test suite & frontend build; commit Phase 1.

### Phase 2: Explainable AI & Score Decompositions
- [ ] Return `score_breakdown` with each recommendation: `{semantic, keyword, graph, geo, category, feedback}` summing to total score (exact Shapley values for linear model).
- [ ] Return `matched_terms`: list of overlapping lexical/semantic tokens.
- [ ] Return `graph_path`: explainable network path string (e.g. "You → Photography circle → Alex").
- [ ] Return `explanation`: natural-language one-sentence rationale without privacy leakage.
- [ ] Frontend: visual stacked contribution bar and "Why this?" popover on recommendation cards.
- [ ] Unit tests: assert breakdown sum matches score, and verify explanations never leak private user attributes.
- [ ] Verify test suite & frontend build; commit Phase 2.

### Phase 3: Privacy-Preserving Geolocation
- [ ] Create `backend/app/services/location_privacy.py` implementing grid snapping and Duckham–Kulik bounded noise.
- [ ] Add `privacy_level` on user profile: `exact`, `approximate` (~1 km), `city`, `hidden`.
- [ ] Enforce coarse location matching and ensure raw coordinates of other users never leave the API.
- [ ] Frontend: Settings page precision control with explanatory copy.
- [ ] Experiment: Evaluate recommendation metric degradation across privacy levels, documented in `docs/AI_EVALUATION.md`.
- [ ] Unit tests: assert raw coordinates are stripped from user responses.
- [ ] Verify test suite & frontend build; commit Phase 3.

### Phase 4: Retrieval, Intent Classifier & Ranking Quality
- [ ] Database-level vector shortlist retrieval: `ORDER BY embedding <=> :q LIMIT 50` with pgvector HNSW index.
- [ ] Intent classifier: Scikit-learn model (Sentence-Transformers + LogisticRegression / LinearSVC) for entity-type and goal-type classification, with regex rules as fallback.
- [ ] Personalized re-ranking: profile embeddings, saved items, memberships, and feedback with clear cold-start policy.
- [ ] Query embedding LRU cache.
- [ ] Resilience: timeouts, retries, and rate-limiting on Eventbrite / GitHub connectors.
- [ ] Verify test suite & frontend build; commit Phase 4.

### Phase 5: Frontend Experience & UI Overhaul
- [x] Hero redesign: replace stock photo with interactive intent search bar, quick example prompt chips, and 3 live result preview cards.
- [x] Add "How it works" 3-step section, privacy guarantee note, trending communities/events, and structured footer.
- [x] Streamlined navigation: Grouped into Home, Discover (Explore, Map, Opportunities), Connect (Communities, Circles, Events, Collaborate), Grow (Goal Journey, Achievements). Assistant only as floating widget; theme toggle & settings in profile menu.
- [x] Dynamic Home: personalized feed for logged-in users; marketing intent hero for guests.
- [x] Polish: eliminate dead space, vertical alignment, loosened typography tracking, WCAG AA $\ge 4.5:1$ contrast, aria-labels, focus rings, skeleton loaders.
- [x] Add Recharts visualization to Dashboard and Achievements (goal progress, activity, in-app evaluation charts).
- [x] Verify test suite & frontend build; commit Phase 5.

### Phase 6: Security, Roles, Data Hygiene & CI/CD
- [x] RBAC roles: `user`, `moderator`, `admin` with `require_role` / `require_admin` FastAPI dependencies.
- [x] Data validation and cleaning in import scripts with data quality audit report.
- [x] High test coverage: $\ge 70\%$ unit test coverage on `backend/app/services/` (Achieved: 79%).
- [x] Frontend Vitest + React Testing Library test suite.
- [x] GitHub Actions CI workflow (`.github/workflows/ci.yml`).
- [x] Structured JSON logging and `/metrics` / `/health/details` endpoint.
- [x] Produce `docs/CHANGELOG.md` with verified command outputs and any baseline non-wins.
- [x] Verify test suite & frontend build; commit Phase 6.
