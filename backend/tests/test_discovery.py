import pytest
from types import SimpleNamespace
from app.services.discovery import score_text, discover, haversine_distance
from app.services.embeddings import cosine_similarity, generate_embedding

def test_haversine_distance():
    # Distance between Pune (18.5204, 73.8567) and Mumbai (19.0760, 72.8777) is ~120-150 km
    d = haversine_distance(18.5204, 73.8567, 19.0760, 72.8777)
    assert 110 < d < 150

def test_cosine_similarity_identity():
    v1 = [1.0, 0.0, 0.5]
    assert cosine_similarity(v1, v1) == pytest.approx(1.0)

def test_semantic_embedding_generation():
    emb = generate_embedding("machine learning with python")
    assert len(emb) == 384
    # Check unit vector normalization
    norm = sum(x * x for x in emb)
    assert 0.98 < norm < 1.02

def test_hybrid_discover_ranking():
    communities = [
        SimpleNamespace(
            id=1,
            name="Watercolor Art Club",
            description="Painting, sketching, and traditional watercolors.",
            category="Art",
            tags="paint, sketching",
            location="Online",
            latitude=None,
            longitude=None,
            embedding=generate_embedding("Watercolor Art Club Painting sketching traditional watercolors"),
        ),
        SimpleNamespace(
            id=2,
            name="Python Data Science & ML Circle",
            description="Deep learning, PyTorch, data science, and neural networks.",
            category="Technology",
            tags="python, machine learning, data science",
            location="Online",
            latitude=None,
            longitude=None,
            embedding=generate_embedding("Python Data Science ML Circle Deep learning PyTorch data science neural networks"),
        ),
    ]
    results = discover("I want to learn deep learning with python", communities, [], [], limit=5)
    assert len(results) > 0
    # Python Data Science should rank first with high score
    assert results[0]["id"] == 2
    assert results[0]["score"] > 0.4
    assert "semantic intent alignment" in results[0]["reason"] or "matched" in results[0]["reason"]


def test_explainable_ai_score_breakdown_and_shapley_exact_sum():
    communities = [
        SimpleNamespace(
            id=10,
            name="Cloud Native DevOps Guild",
            description="Kubernetes, Docker, Go, microservices, and CI/CD pipelines.",
            category="Technology",
            tags="kubernetes, docker, golang, devops",
            location="Berlin, Germany",
            latitude=52.5200,
            longitude=13.4050,
            embedding=generate_embedding("Cloud Native DevOps Guild Kubernetes Docker Go microservices CI/CD"),
        ),
    ]
    results = discover(
        query="DevOps and Kubernetes infrastructure engineering",
        communities=communities,
        events=[],
        places=[],
        user_lat=52.5000,
        user_lon=13.3800,
        preferred_category="Technology",
        limit=5,
    )
    assert len(results) == 1
    item = results[0]

    # 1. Verify score_breakdown structure
    breakdown = item["score_breakdown"]
    assert set(breakdown.keys()) == {"semantic", "keyword", "graph", "geo", "category", "feedback"}

    # 2. Verify exact Shapley sum equality down to 4 decimal places
    breakdown_sum = round(sum(breakdown.values()), 4)
    assert breakdown_sum == pytest.approx(item["score"], abs=1e-4)

    # 3. Verify matched_terms
    assert "matched_terms" in item
    assert any("Kubernetes" in t or "Devops" in t or "Docker" in t for t in item["matched_terms"])

    # 4. Verify natural-language explanation
    assert "why_recommended" in item
    assert item["why_recommended"].startswith("Recommended because")
    assert "Devops" in item["why_recommended"] or "Kubernetes" in item["why_recommended"] or "shares" in item["why_recommended"] or "aligns" in item["why_recommended"]


def test_explainable_ai_privacy_guarantee():
    from app.services.discovery import build_xai_explanation

    # Ensure private user sensitive fields are never exposed in explanation text
    explanation = build_xai_explanation(
        result_type="user",
        title="Alex Chen",
        matched_terms=["Skill: Python", "Skill: Machine Learning"],
        graph_path="You → (connection: Priya) → (connected) → Alex Chen",
        graph_details={"mutual_friends": 1, "mutual_names": ["Priya"]},
        dist_km=2.4,
        loc_str="San Francisco",
        sem_sim=0.82,
    )

    assert "Recommended because" in explanation
    assert "Python" in explanation or "interests" in explanation
    assert "mutual connection" in explanation or "Priya" in explanation
    assert "2.4 km away" in explanation

    # Strict check: never contain emails, tokens, or hashed passwords
    assert "@" not in explanation
    assert "password" not in explanation.lower()
    assert "hash" not in explanation.lower()
    assert "secret" not in explanation.lower()

