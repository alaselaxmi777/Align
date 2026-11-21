# ALIGN: Architectural Limitations & Future Work

**Platform**: ALIGN (An Intent and Embedding-Based Framework for Personalized Community and Experience Discovery)  
**Version**: 2.0.0 (Production-Grade Prototype)  
**Scope**: Honest Academic Appraisal, Algorithmic Bounds, and Scalability Constraints  

---

## 1. Executive Summary

As a prototype developed for academic submission, research demonstration, and initial deployment, ALIGN demonstrates full end-to-end functionality across semantic intent discovery, knowledge graph reasoning, media feed ranking, and administrative safety. However, rigorous research demands transparent documentation of the system's current technical constraints and design trade-offs.

---

## 2. Key Technical Limitations

### 1. Application-Layer Vector Similarity vs. Database HNSW Indexing
- **Current Behavior:** While 384-dimensional dense vectors are persisted in native PostgreSQL `vector(384)` columns via the `pgvector` extension, candidate vector similarity calculations are evaluated in an in-memory application-layer loop inside FastAPI using NumPy/Python cosine operations over retrieved candidate sets ($O(N \cdot 384)$).
- **Scale Implication:** While highly performant for catalogues up to $10^4$ entities (sub-50ms latency), scaling to millions of items requires transitioning to database-side approximate nearest neighbor (ANN) index scans (`CREATE INDEX USING hnsw (embedding vector_cosine_ops)`).

### 2. Hand-Tuned Heuristic Weights vs. Learned Ranking (LTR)
- **Current Behavior:** Both the multi-entity discovery scorer ($0.50 s + 0.25 k + 0.15 g + b_{\text{geo}} + b_{\text{cat}}$) and the 6-factor feed ranker ($0.25 s + 0.20 g + 0.20 r + 0.15 e + 0.10 m + 0.10 l$) rely on hand-tuned, interpretable weights that sum to 1.00.
- **Design Justification:** In a newly deployed platform facing a severe cold-start problem, no historical click-through or interaction matrix exists to train supervised models.
- **Limitation:** These linear weights do not dynamically adapt to individual user behavioral tendencies (e.g., users who strongly favor video over text or vice versa). Future iterations will train a learned re-ranking model (e.g., LambdaMART or GNN-based ranker) once dense user engagement logs accumulate.

### 3. Asynchronous Worker Architecture
- **Current Behavior:** Video transcoding (FFmpeg conversion to H.264/AAC MP4 with poster generation) and notification dispatch execute via FastAPI's native `BackgroundTasks` runner.
- **Scale Implication:** Background tasks execute inside the same process boundary as the API server. In heavy multi-tenant production deployments with concurrent high-definition video uploads, CPU-bound FFmpeg tasks must be offloaded to dedicated distributed task workers (e.g., Celery or ARQ backed by Redis).

### 4. Cold-Start Reference Data Dependency
- **Current Behavior:** To seed the system, ALIGN relies on 15,000 curated records across skills, hobbies, goals, and interests. While this solves the "empty room" problem, user profiles with sparse descriptions rely on neutral baseline signals ($s = 0.50$) until rich text attributes or intent queries are supplied.

### 5. External API Latency Variability
- **Current Behavior:** Real-time connectors to external services (Eventbrite and GitHub) depend on third-party network roundtrips and external rate limits. 
- **Mitigation:** The architecture implements in-memory caching and fallback synthetic mocks to ensure benchmarking reproducibility when live connections are throttled.

---

## 3. Roadmap for Future Enhancements

1. **Native PostgreSQL HNSW Indexing:** Migrate all similarity queries from application-layer Python loops to direct SQL vector operators (`ORDER BY embedding <=> query_vector LIMIT K`) with HNSW index traversal.
2. **Graph Neural Network (GNN) Embeddings:** Transition from heuristic Neo4j Cypher path traversals to learned node embeddings (e.g., Graph Convolutional Networks or KGAT) to capture higher-order relational dependencies.
3. **Multilingual Fine-Tuning:** Extend sentence embeddings with fine-tuned domain corpora specifically adapted to mixed Devanagari script and colloquial Marathi/Hindi social expressions.
4. **Distributed Task Queue:** Decouple media transcoding and heavy vector batch jobs to external Redis/Celery workers with autoscaling worker pools.
