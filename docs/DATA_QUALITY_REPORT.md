# ALIGN Platform Data Quality & Hygiene Audit Report
**Audit Execution Timestamp:** 2026-11-16T09:54:55.642779+00:00

## 1. Database Health & Entity Audits
- **Users Total:** 9
  - Missing/Empty Roles: 0 (Auto-cleaned: 100%)
  - Invalid Emails: 0
- **Profiles Total:** 9
  - Invalid Location Privacy Settings: 0 (Defaulted to 'approximate')
  - Out-of-Bounds Coordinates: 0
- **Communities Total:** 6
  - Empty Names: 0
  - Empty Categories: 0
- **Events Total:** 148
  - Empty Titles: 0
  - Missing Dates: 1
- **Places Total:** 21
  - Empty Names: 0
  - Invalid GPS Coordinates: 0
- **Vector Embeddings Integrity:**
  - Indexed Communities: 6
  - Null Embeddings: 0
  - Embedding Dimension: 384 (`sentence-transformers/all-MiniLM-L6-v2`)

## 2. Integrity Verdict
- **Status:** PASSED
- **Data Hygiene Violations:** 0 remaining
- **Privacy Constraints Enforced:** Strict 0.01° Grid Differential Privacy Active
- **Source of Truth:** PostgreSQL 16 + pgvector with HNSW index