import pytest
from app.evaluation.dataset import load_or_create_benchmark_items, build_benchmark_queries, get_benchmark_splits
from app.evaluation.graph_evaluator import GraphStructureEvaluator
from app.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    f1_at_k,
    hit_rate_at_k,
    ndcg_at_k,
    mean_reciprocal_rank,
    intra_list_diversity,
    novelty_at_k,
    calculate_paired_wilcoxon,
)
from app.evaluation.latency_benchmark import measure_pgvector_latency

def test_benchmark_dataset_loading_and_splits():
    items = load_or_create_benchmark_items(num_items=100, seed=42)
    assert len(items) >= 50
    assert items[0].embedding is not None

    queries = build_benchmark_queries(items, seed=42)
    assert len(queries) >= 30

    q_train, q_val, q_test = get_benchmark_splits(items, queries, seed=42)
    assert len(q_train) > len(q_val)
    assert len(q_val) > 0
    assert len(q_test) > 0

    # Ensure hard queries are represented across splits
    assert any(q.is_hard for q in q_test)

def test_graph_evaluator_structural_affinity_zero_leakage():
    items = load_or_create_benchmark_items(num_items=50, seed=42)
    queries = build_benchmark_queries(items, seed=42)
    q_train, _, _ = get_benchmark_splits(items, queries, seed=42)

    graph_eval = GraphStructureEvaluator(items, q_train)
    affinity = graph_eval.compute_graph_affinity({"technology", "python"}, items[0].id)
    assert 0.0 <= affinity <= 1.0

def test_evaluation_metrics_mathematical_properties():
    recommended = [1, 2, 3, 4, 5]
    relevant = {2, 4, 6}

    p5 = precision_at_k(recommended, relevant, 5)
    assert p5 == 2 / 5

    r5 = recall_at_k(recommended, relevant, 5)
    assert r5 == 2 / 3

    f1 = f1_at_k(p5, r5)
    assert 0.0 < f1 <= 1.0

    hit = hit_rate_at_k(recommended, relevant, 5)
    assert hit == 1.0

    ndcg = ndcg_at_k(recommended, relevant, 5)
    assert 0.0 < ndcg <= 1.0

    mrr = mean_reciprocal_rank(recommended, relevant)
    assert mrr == 0.5  # Item 2 is at rank 2 -> 1/2

def test_statistical_significance_wilcoxon():
    scores_a = [0.8, 0.9, 0.7, 0.85, 0.95, 0.6, 0.75, 0.8]
    scores_b = [0.2, 0.3, 0.25, 0.35, 0.4, 0.1, 0.3, 0.2]

    stat, p_val = calculate_paired_wilcoxon(scores_a, scores_b)
    assert stat >= 0.0
    assert 0.0 <= p_val <= 1.0

def test_pgvector_latency_benchmark():
    res = measure_pgvector_latency(num_queries=5)
    assert res["catalog_size"] == 10000
    assert res["total_p50_ms"] > 0.0
    assert res["total_p95_ms"] >= res["total_p50_ms"]
