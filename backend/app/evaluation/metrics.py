import math
from typing import Sequence
import numpy as np
from scipy import stats

def precision_at_k(recommended_ids: Sequence[int], relevant_ids: set[int], k: int) -> float:
    """Calculates Precision@K: proportion of recommended items in top-K that are relevant."""
    if k <= 0 or not recommended_ids:
        return 0.0
    top_k = recommended_ids[:k]
    hits = sum(1 for item_id in top_k if item_id in relevant_ids)
    return hits / k

def recall_at_k(recommended_ids: Sequence[int], relevant_ids: set[int], k: int) -> float:
    """Calculates Recall@K: proportion of relevant items captured in top-K recommendations."""
    if not relevant_ids or k <= 0 or not recommended_ids:
        return 0.0
    top_k = recommended_ids[:k]
    hits = sum(1 for item_id in top_k if item_id in relevant_ids)
    return hits / len(relevant_ids)

def f1_at_k(prec: float, rec: float) -> float:
    """Harmonic mean of precision and recall."""
    if prec + rec == 0.0:
        return 0.0
    return 2 * (prec * rec) / (prec + rec)

def hit_rate_at_k(recommended_ids: Sequence[int], relevant_ids: set[int], k: int) -> float:
    """HitRate@K (1.0 if at least one relevant item is in top-K, 0.0 otherwise)."""
    top_k = recommended_ids[:k]
    return 1.0 if any(item_id in relevant_ids for item_id in top_k) else 0.0

def ndcg_at_k(recommended_ids: Sequence[int], relevant_ids: set[int], k: int) -> float:
    """Normalized Discounted Cumulative Gain at K (binary relevance)."""
    if k <= 0 or not recommended_ids or not relevant_ids:
        return 0.0
    top_k = recommended_ids[:k]
    dcg = 0.0
    for idx, item_id in enumerate(top_k):
        if item_id in relevant_ids:
            dcg += 1.0 / math.log2(idx + 2)  # idx is 0-based, rank is idx + 1, log2(rank + 1) = log2(idx + 2)
    
    # Ideal DCG
    ideal_hits = min(k, len(relevant_ids))
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg

def mean_reciprocal_rank(recommended_ids: Sequence[int], relevant_ids: set[int]) -> float:
    """Reciprocal rank of the first relevant item."""
    for idx, item_id in enumerate(recommended_ids):
        if item_id in relevant_ids:
            return 1.0 / (idx + 1)
    return 0.0

def intra_list_diversity(embeddings: list[list[float]], k: int) -> float:
    """
    Measures catalog diversity as average pairwise cosine distance within top-K:
    Diversity = 1 - (2 / (K * (K - 1))) * sum_{i < j} cos_sim(e_i, e_j)
    """
    top_embs = embeddings[:k]
    n = len(top_embs)
    if n <= 1:
        return 0.0
    
    sim_sum = 0.0
    pairs = 0
    for i in range(n):
        v1 = np.array(top_embs[i])
        norm1 = np.linalg.norm(v1)
        if norm1 == 0:
            continue
        v1_norm = v1 / norm1
        for j in range(i + 1, n):
            v2 = np.array(top_embs[j])
            norm2 = np.linalg.norm(v2)
            if norm2 == 0:
                continue
            v2_norm = v2 / norm2
            sim_sum += float(np.dot(v1_norm, v2_norm))
            pairs += 1
            
    if pairs == 0:
        return 0.0
    avg_sim = sim_sum / pairs
    return max(0.0, 1.0 - avg_sim)

def novelty_at_k(recommended_ids: Sequence[int], popularity_probs: dict[int, float], k: int) -> float:
    """
    Novelty: average self-information of recommended items:
    Novelty = (1 / K) * sum_{i=1}^K -log2(P(item_i))
    Higher novelty indicates recommending discovery/niche items rather than only head/popular items.
    """
    top_k = recommended_ids[:k]
    if not top_k:
        return 0.0
    self_info = 0.0
    for item_id in top_k:
        p = popularity_probs.get(item_id, 0.01)
        p = max(0.0001, min(0.9999, p))
        self_info += -math.log2(p)
    return self_info / len(top_k)

def calculate_paired_wilcoxon(scores_model_a: list[float], scores_model_b: list[float]) -> tuple[float, float]:
    """
    Performs Wilcoxon signed-rank test between paired scores across queries.
    Returns (statistic, p_value).
    """
    diffs = [a - b for a, b in zip(scores_model_a, scores_model_b)]
    if all(d == 0 for d in diffs):
        return 0.0, 1.0
    try:
        res = stats.wilcoxon(scores_model_a, scores_model_b)
        return float(res.statistic), float(res.pvalue)
    except Exception:
        return 0.0, 1.0
