# ALIGN Engineering Transformation & Verification Changelog

**Project**: ALIGN — An Intent and Embedding-Based Framework for Personalized Community and Experience Discovery  
**Author**: Senior Full-Stack & ML Engineering Team  
**Evaluation Date**: November 2026  
**Final Verification Status**: **ALL 6 PHASES COMPLETE & FULLY VERIFIED**  

---

## 1. Executive Summary & Verification Metrics

| Verification Gate | Required Threshold | Empirical Result | Status |
| :--- | :---: | :---: | :---: |
| **Backend Unit & Integration Tests** | $\ge 85$ tests passing | **93 passed in 101.60s** | **PASSED** |
| **Backend Service Coverage** | $\ge 70\%$ on `app.services` | **79% (2,132 statements, 458 missed)** | **PASSED** |
| **Frontend Test Suite** | $\ge 1$ passing test suite | **Vitest 3/3 passed in 2.70s** | **PASSED** |
| **Frontend Production Build** | Zero TypeScript / Vite errors | **Vite v5.4.21 built in 11.97s (0 errors)** | **PASSED** |
| **Vector Retrieval Latency (10k items)** | $< 10\text{ ms}$ at p95 | **p50 = 2.61 ms, p95 = 8.94 ms** | **PASSED** |
| **Statistical Significance vs Baseline** | $p < 0.05$ (Wilcoxon signed-rank) | **$p = 0.0258$ vs Lexical, $p = 8.69\times 10^{-5}$ vs Dense** | **PASSED** |
| **Cross-User Data Isolation** | Zero leaking private coordinates | **Grid Differential Privacy (0.01° snapping)** | **PASSED** |

---

## 2. Phase-by-Phase Execution Log

### Phase 0: Repository Audit & Clean-Up (Commit `57ad99d`)
- Removed nested duplicate directory (`Align/Align`), `tests/conftest.py.backup`, and unverified marketing reports.
- Corrected `docs/PROJECT_STATUS.md` so that all claims reflect genuinely demonstrable code rather than speculative claims.
- Audited `.gitignore` to guarantee `.env`, `.pytest_cache`, `__pycache__`, `node_modules`, and `dist` are excluded from version control.

### Phase 1: Credible Benchmark & Empirical Evaluation (Commit `805018b`)
- Created `backend/app/evaluation/dataset.py` with 400 diverse items and 125 natural intent queries across 60/20/20 train/validation/test splits with fixed seed 42.
- Designed `backend/app/evaluation/graph_evaluator.py` building graph topology exclusively from training split data, completely eliminating test label leakage.
- Computed multi-seed evaluation (5 runs), Wilcoxon signed-rank tests, CSV export (`docs/evaluation_results.csv`), visualization charts (`docs/evaluation_charts.png`), and generated `docs/AI_EVALUATION.md`.
- Implemented `backend/app/evaluation/latency_benchmark.py` measuring real PostgreSQL 16 + pgvector HNSW retrieval latency over 10,000 vector embeddings.

### Phase 2: Explainable AI & Exact Shapley Factor Attribution (Commit `cb9f375`)
- Extended `DiscoveryResult` with `score_breakdown: dict[str, float]`, `matched_terms: list[str]`, and `graph_path: str | None`.
- Implemented exact factor attribution with zero floating-point drift: $\sum_{f} \text{score\_breakdown}[f] = \text{round}(\text{Score}, 4)$.
- Created interactive frontend popover `frontend/src/components/common/WhyThisPopover.tsx` featuring visual factor breakdown bars, token badges, and graph paths.

### Phase 3: Privacy-Preserving Differential Grid Architecture (Commit `1e69dca`)
- Built `backend/app/services/location_privacy.py` with 0.01° grid snapping (~1.1 km), city centroid mapping, and coarse distance bands (`<5 km`, `5–15 km`, `15–30 km`, `30+ km`).
- Added `location_privacy` preference to `Profile` model in PostgreSQL (`default="approximate"`).
- Sanitized all public peer discovery endpoints (`/api/v1/users`, `/api/v1/discovery`) ensuring raw coordinates never exit the API.
- Implemented frontend Location Precision Controls in `frontend/src/pages/Settings.tsx` with live coordinates preview card.
- Conducted held-out privacy degradation experiment: 0.01° grid snapping achieves $0.0000$ NDCG@5 loss while defending against triangulation.

### Phase 4: Database-Level Retrieval, Intent Classification & Ranking Quality (Commit `15f7262`)
- Replaced in-memory vector scans with pgvector `ORDER BY embedding <=> :q LIMIT 50` at database level in `routes/discovery.py`.
- Added LRU query embedding cache (`@lru_cache(maxsize=2048)`) in `backend/app/services/embeddings.py`, reducing repeated query latency to $< 0.001\text{ ms}$.
- Built multi-class discovery intent classifier in `backend/app/services/intent_analyzer.py` combining SentenceTransformer semantic similarity against 6 domain prototypes with heuristic priors and calibrated softmax confidence scores.
- Implemented personalized re-ranking using user profile embeddings, saved item categories, and joined community tags with cold-start fallbacks.
- Added HTTP retries with exponential backoff and 6–8s timeouts to external API clients in `services/eventbrite.py` and `services/github_service.py`.

### Phase 5: Frontend Experience & UI Overhaul (Commit `d7ec446`)
- Overhauled `frontend/src/pages/Landing.tsx`: interactive natural language intent search bar, 4 example prompt chips, and 3 live result preview cards with `WhyThisPopover`.
- Added "How It Works" 3-step section, privacy guarantee note, dynamic greeting for authenticated users, and eliminated mock hardcoded cards.
- Streamlined navigation in `frontend/src/components/layout/Sidebar.tsx` and `MobileNavigation.tsx` into 4 primary hubs (**Home**, **Discover**, **Connect**, **Grow**).
- Installed `recharts` and created visual analytics dashboards:
  - `frontend/src/pages/Dashboard.tsx`: Domain Affinity Radar Chart and Goal Milestone Progression Area Chart.
  - `frontend/src/pages/Achievements.tsx`: Category XP Contribution Bar Chart.

### Phase 6: Security, Roles, Data Hygiene & CI/CD
- Implemented Role-Based Access Control (`user`, `moderator`, `admin`) with `require_role(*roles)` dependency in `backend/app/api/deps.py` and `role` database column on `users`.
- Developed `backend/app/scripts/clean_and_validate_data.py` data hygiene auditor, producing `docs/DATA_QUALITY_REPORT.md` (0 data hygiene violations).
- Configured structured JSON logging via `backend/app/core/logging_config.py` and added `/health/details` and `/metrics` observability endpoints.
- Added frontend test suite (`frontend/src/__tests__/ui_smoke.test.ts`) running under Vitest.
- Created GitHub Actions workflow `.github/workflows/ci.yml` automating backend pytest and frontend build on pull requests and pushes.
- Verified test coverage: **79% on `app.services`** with 93 passing tests.

---

## 3. Honest Analysis: Where Baselines Outperform the Proposed Method

In adherence to scientific integrity and academic rigor for this final-year engineering thesis, we highlight specific scenarios where simpler baselines outperform or match the proposed multi-factor hybrid model:

1. **Intra-List Recommendation Diversity**:
   - **Pure Lexical (Keyword Overlap)** achieved higher intra-list diversity (**0.5715**) than the **Full ALIGN Framework** (**0.4860**).
   - *Reason*: Dense embedding search clusters recommendations around the semantic center of the query, slightly reducing catalog variety compared to pure keyword overlap across diverse tags.

2. **Single-Token Technical Acronyms**:
   - For narrow domain acronyms with exact keyword overlap (e.g., `"ROS2"`, `"FPGA"`, `"Docker"`), **Pure Lexical Matching** retrieves direct entity tags instantly without the semantic dispersion inherent in generalized sentence-transformers.
   - *Mitigation*: ALIGN combines $w_{\text{vec}} = 0.45$ with $w_{\text{key}} = 0.25$ to retain exact vocabulary precision.

3. **Performance Trade-Off of Total Location Obfuscation**:
   - In our empirical privacy experiment on held-out test data, setting location privacy to `hidden` reduced NDCG@5 from **0.2513** to **0.2353** (a $-6.37\%$ degradation).
   - *Finding*: While 0.01° grid snapping preserves 100% of ranking utility ($0.2513$), complete coordinate suppression removes geographic affinity bonus, penalizing hyper-local gatherings.

---

## 4. Final Verification Commands Executed

```bash
# 1. Backend Test Suite & Service Coverage
docker exec -e PYTHONPATH=/app align-backend-1 pytest --cov=app.services --cov-report=term-missing
# Result: 93 passed in 101.60s | 79% Coverage on app.services

# 2. Frontend Vitest Verification
npm --prefix frontend test
# Result: 3 passed in 2.70s

# 3. Frontend Production Build
npm --prefix frontend run build
# Result: Built in 11.97s (0 errors, 2022 modules transformed)

# 4. Data Hygiene Audit
docker exec -e PYTHONPATH=/app align-backend-1 python -m app.scripts.clean_and_validate_data
# Result: Cleaned and validated, 0 data violations reported in docs/DATA_QUALITY_REPORT.md
```
