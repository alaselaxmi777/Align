"""
Validation Set Score Weight Tuner for ALIGN Recommendation Framework.

Performs parameter optimization on the VALIDATION SPLIT ONLY.
Optimized via vectorized precomputed feature tensors.
"""

from typing import Sequence
import numpy as np
from app.evaluation.dataset import BenchmarkItem, BenchmarkQuery
from app.evaluation.graph_evaluator import GraphStructureEvaluator
from app.evaluation.metrics import ndcg_at_k
from app.services.embeddings import cosine_similarity, generate_embedding
from app.services.discovery import tokens, haversine_distance

def tune_weights_on_validation(
    val_queries: list[BenchmarkQuery],
    items: list[BenchmarkItem],
    graph_evaluator: GraphStructureEvaluator,
) -> dict:
    """
    Vectorized grid search over candidate weight combinations on the validation split.
    Optimizes for NDCG@5.
    """
    n_queries = len(val_queries)
    n_items = len(items)

    item_ids = np.array([it.id for it in items])
    item_tokens = [tokens(f"{it.title} {it.description} {it.category} {it.tags}") for it in items]
    
    # 1. Precompute Feature Matrices (Shape: n_queries x n_items)
    M_dense = np.zeros((n_queries, n_items), dtype=np.float32)
    M_lex = np.zeros((n_queries, n_items), dtype=np.float32)
    M_graph = np.zeros((n_queries, n_items), dtype=np.float32)
    M_geo = np.zeros((n_queries, n_items), dtype=np.float32)

    for q_idx, q in enumerate(val_queries):
        q_emb = generate_embedding(q.query)
        q_toks = tokens(q.query)
        user_interests = set(q.category.lower().split())

        for it_idx, it in enumerate(items):
            # Dense semantic similarity
            M_dense[q_idx, it_idx] = cosine_similarity(q_emb, it.embedding)

            # Lexical keyword score
            doc_toks = item_tokens[it_idx]
            overlap = q_toks & doc_toks
            M_lex[q_idx, it_idx] = len(overlap) / max(1, len(q_toks)) if q_toks else 0.0

            # Graph structural affinity
            M_graph[q_idx, it_idx] = graph_evaluator.compute_graph_affinity(user_interests, it.id)

            # Geographic proximity
            if q.user_lat and q.user_lon and it.latitude and it.longitude:
                dist = haversine_distance(q.user_lat, q.user_lon, it.latitude, it.longitude)
                if dist <= 25.0:
                    M_geo[q_idx, it_idx] = 1.0
                elif dist <= 50.0:
                    M_geo[q_idx, it_idx] = 0.5

    # 2. Candidate Weight Grids
    dense_weights = [0.40, 0.45, 0.50, 0.55, 0.60]
    lex_weights = [0.15, 0.20, 0.25, 0.30]
    graph_weights = [0.05, 0.10, 0.15, 0.20]
    geo_weights = [0.05, 0.10]

    best_score = -1.0
    best_weights = {"w_dense": 0.50, "w_lex": 0.25, "w_graph": 0.15, "w_geo": 0.10}
    combinations_tested = 0

    for wd in dense_weights:
        for wl in lex_weights:
            for wg in graph_weights:
                for wgeo in geo_weights:
                    total_w = wd + wl + wg + wgeo
                    n_wd = round(wd / total_w, 3)
                    n_wl = round(wl / total_w, 3)
                    n_wg = round(wg / total_w, 3)
                    n_wgeo = round(wgeo / total_w, 3)

                    # Vectorized linear combination (Shape: n_queries x n_items)
                    scores = (n_wd * M_dense) + (n_wl * M_lex) + (n_wg * M_graph) + (n_wgeo * M_geo)

                    ndcg_scores = []
                    for q_idx, q in enumerate(val_queries):
                        # Top-5 items for this query
                        top_indices = np.argsort(-scores[q_idx])[:5]
                        ranked_ids = item_ids[top_indices].tolist()
                        ndcg_scores.append(ndcg_at_k(ranked_ids, q.relevant_ids, k=5))

                    mean_ndcg = float(np.mean(ndcg_scores))
                    combinations_tested += 1

                    if mean_ndcg > best_score:
                        best_score = mean_ndcg
                        best_weights = {
                            "w_dense": n_wd,
                            "w_lex": n_wl,
                            "w_graph": n_wg,
                            "w_geo": n_wgeo,
                        }

    return {
        "best_weights": best_weights,
        "best_val_ndcg5": round(best_score, 4),
        "total_combinations_tested": combinations_tested,
    }
