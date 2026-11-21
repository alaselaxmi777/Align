"""
ALIGN Maharashtra Evaluation Benchmark Runner.
Evaluates discovery and ranking over 334 real-world test queries across English, Marathi (Devanagari), and Hinglish.
Computes Precision@5, NDCG@5, and MRR per language and split (dev / test).
Supports ablation study between English-only (all-MiniLM-L6-v2) and Multilingual (paraphrase-multilingual-MiniLM-L12-v2).
"""

import sys
import os
import json
import math
import logging
from typing import Sequence
import numpy as np

logger = logging.getLogger("eval_maharashtra")
logging.basicConfig(level=logging.INFO)

DATASET_DIR_CANDIDATES = [
    "/app/align_dataset_maharashtra",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "align_dataset_maharashtra")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "align_dataset_maharashtra")),
    "align_dataset_maharashtra",
]

def find_dataset_dir() -> str:
    for candidate in DATASET_DIR_CANDIDATES:
        if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "eval_queries.json")):
            return candidate
    raise FileNotFoundError(f"Could not locate align_dataset_maharashtra in: {DATASET_DIR_CANDIDATES}")

def precision_at_k(recommended_ids: Sequence[str], relevant_dict: dict[str, int], k: int = 5) -> float:
    if k <= 0 or not recommended_ids:
        return 0.0
    top_k = recommended_ids[:k]
    # Grade 2 is highly relevant target
    hits = sum(1 for item_id in top_k if relevant_dict.get(item_id, 0) >= 2)
    return hits / k

def ndcg_at_k(recommended_ids: Sequence[str], relevant_dict: dict[str, int], k: int = 5) -> float:
    if k <= 0 or not recommended_ids or not relevant_dict:
        return 0.0
    top_k = recommended_ids[:k]
    dcg = 0.0
    for idx, item_id in enumerate(top_k):
        rel = relevant_dict.get(item_id, 0)
        if rel > 0:
            dcg += (2.0 ** rel - 1.0) / math.log2(idx + 2)

    # Calculate IDCG
    sorted_rels = sorted(relevant_dict.values(), reverse=True)[:k]
    idcg = sum((2.0 ** r - 1.0) / math.log2(i + 2) for i, r in enumerate(sorted_rels))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg

def mrr(recommended_ids: Sequence[str], relevant_dict: dict[str, int]) -> float:
    for idx, item_id in enumerate(recommended_ids):
        if relevant_dict.get(item_id, 0) >= 2:
            return 1.0 / (idx + 1)
    return 0.0

def load_catalog(dataset_dir: str) -> list[dict]:
    items = []
    # 1. Communities
    with open(os.path.join(dataset_dir, "synthetic_communities.json"), encoding="utf-8") as f:
        comms = json.load(f)
        for c in comms:
            city = (c.get("location") or {}).get("city", "")
            interests = ", ".join(c.get("interests", []))
            text = f"{c['name']} {c['description']} {c.get('category', '')} {interests} {city}"
            items.append({
                "id": c["id"],
                "type": "community",
                "title": c["name"],
                "text": text,
            })

    # 2. Events
    with open(os.path.join(dataset_dir, "synthetic_events.json"), encoding="utf-8") as f:
        events = json.load(f)
        for e in events:
            city = (e.get("location") or {}).get("city", "")
            interests = ", ".join(e.get("interests", []))
            text = f"{e['title']} {e['description']} {e.get('category', '')} {interests} {city}"
            items.append({
                "id": e["id"],
                "type": "event",
                "title": e["title"],
                "text": text,
            })

    # 3. Activities
    with open(os.path.join(dataset_dir, "synthetic_activities.json"), encoding="utf-8") as f:
        acts = json.load(f)
        for a in acts:
            city = (a.get("location") or {}).get("city", "")
            interests = ", ".join(a.get("interests", []))
            text = f"{a['title']} {a['description']} Activity {interests} {city}"
            items.append({
                "id": a["id"],
                "type": "activity",
                "title": a["title"],
                "text": text,
            })

    return items

def evaluate_model(model_name: str, catalog: list[dict], queries: list[dict], split_filter: str | None = None) -> dict:
    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading SentenceTransformer: {model_name}...")
    model = SentenceTransformer(model_name)

    logger.info("Encoding catalog items (1,700 items)...")
    catalog_texts = [item["text"] for item in catalog]
    item_embs = model.encode(catalog_texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    item_ids = [item["id"] for item in catalog]

    eval_set = [q for q in queries if split_filter is None or q.get("split") == split_filter]
    logger.info(f"Evaluating {len(eval_set)} queries (split: {split_filter or 'all'})...")

    results_by_lang = {
        "en": {"p@5": [], "ndcg@5": [], "mrr": []},
        "mr": {"p@5": [], "ndcg@5": [], "mrr": []},
        "hi-latn": {"p@5": [], "ndcg@5": [], "mrr": []},
    }

    query_texts = [q["query"] for q in eval_set]
    q_embs = model.encode(query_texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)

    # Dot product since vectors are normalized = cosine similarity
    sim_matrix = np.dot(q_embs, item_embs.T)

    for i, q in enumerate(eval_set):
        lang = q.get("language", "en")
        rel_dict = q.get("relevance", {})
        scores = sim_matrix[i]
        
        # Rank top 50
        ranked_indices = np.argsort(-scores)[:50]
        ranked_ids = [item_ids[idx] for idx in ranked_indices]

        p5 = precision_at_k(ranked_ids, rel_dict, k=5)
        n5 = ndcg_at_k(ranked_ids, rel_dict, k=5)
        r = mrr(ranked_ids, rel_dict)

        if lang in results_by_lang:
            results_by_lang[lang]["p@5"].append(p5)
            results_by_lang[lang]["ndcg@5"].append(n5)
            results_by_lang[lang]["mrr"].append(r)

    summary = {}
    all_p5, all_ndcg, all_mrr = [], [], []

    for lang, metrics in results_by_lang.items():
        count = len(metrics["p@5"])
        if count > 0:
            avg_p5 = float(np.mean(metrics["p@5"]))
            avg_ndcg = float(np.mean(metrics["ndcg@5"]))
            avg_mrr = float(np.mean(metrics["mrr"]))
            summary[lang] = {
                "count": count,
                "precision@5": round(avg_p5, 4),
                "ndcg@5": round(avg_ndcg, 4),
                "mrr": round(avg_mrr, 4),
            }
            all_p5.extend(metrics["p@5"])
            all_ndcg.extend(metrics["ndcg@5"])
            all_mrr.extend(metrics["mrr"])
        else:
            summary[lang] = {"count": 0, "precision@5": 0.0, "ndcg@5": 0.0, "mrr": 0.0}

    summary["overall"] = {
        "count": len(all_p5),
        "precision@5": round(float(np.mean(all_p5)), 4) if all_p5 else 0.0,
        "ndcg@5": round(float(np.mean(all_ndcg)), 4) if all_ndcg else 0.0,
        "mrr": round(float(np.mean(all_mrr)), 4) if all_mrr else 0.0,
    }

    return summary

def main():
    dataset_dir = find_dataset_dir()
    catalog = load_catalog(dataset_dir)
    with open(os.path.join(dataset_dir, "eval_queries.json"), encoding="utf-8") as f:
        queries = json.load(f)

    split = "test" if "--test-only" in sys.argv else None
    
    # Models to test
    multilingual_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    english_model = "sentence-transformers/all-MiniLM-L6-v2"

    print("================================================================================")
    print("           ALIGN MAHARASHTRA MULTILINGUAL EVALUATION BENCHMARK                  ")
    print(f"Catalog items: {len(catalog)} | Total queries: {len(queries)} | Split: {split or 'all'}")
    print("================================================================================\n")

    # 1. Primary Multilingual Model Evaluation
    print(f"--> Evaluating Multilingual Model: {multilingual_model}")
    res_multi = evaluate_model(multilingual_model, catalog, queries, split_filter=split)

    print("\n--- RESULTS: paraphrase-multilingual-MiniLM-L12-v2 ---")
    print(f"{'Language':<15} | {'Count':<6} | {'Precision@5':<12} | {'NDCG@5':<10} | {'MRR':<8}")
    print("-" * 60)
    for lang in ["en", "mr", "hi-latn", "overall"]:
        label = {"en": "English", "mr": "Marathi", "hi-latn": "Hinglish", "overall": "OVERALL"}[lang]
        m = res_multi[lang]
        print(f"{label:<15} | {m['count']:<6} | {m['precision@5']:<12.4f} | {m['ndcg@5']:<10.4f} | {m['mrr']:<8.4f}")

    # 2. Ablation Comparison if requested
    if "--ablation" in sys.argv:
        print("\n\n--> Running Ablation against English-Only Model: " + english_model)
        res_en = evaluate_model(english_model, catalog, queries, split_filter=split)

        print("\n--- ABLATION COMPARISON (Multilingual vs English-Only) ---")
        print(f"{'Language':<12} | {'Multilingual NDCG@5':<20} | {'English-Only NDCG@5':<20} | {'Delta':<10}")
        print("-" * 70)
        for lang in ["en", "mr", "hi-latn", "overall"]:
            label = {"en": "English", "mr": "Marathi", "hi-latn": "Hinglish", "overall": "OVERALL"}[lang]
            ndcg_m = res_multi[lang]["ndcg@5"]
            ndcg_e = res_en[lang]["ndcg@5"]
            delta = ndcg_m - ndcg_e
            print(f"{label:<12} | {ndcg_m:<20.4f} | {ndcg_e:<20.4f} | {delta:+.4f}")

if __name__ == "__main__":
    main()
