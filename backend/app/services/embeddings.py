import os
import math
import hashlib
import logging
from functools import lru_cache
from typing import Sequence

# Enable offline execution for cached local sentence-transformers models
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None
_model_failed = False

def get_embedding_model():
    global _model, _model_failed
    if _model is not None:
        return _model
    if _model_failed:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {settings.embedding_model_name}...")
        _model = SentenceTransformer(settings.embedding_model_name)
        logger.info("Embedding model loaded successfully.")
        return _model
    except Exception as e:
        logger.warning(f"Could not load SentenceTransformer model ({e}). Attempting fallback...")
        try:
            if "paraphrase-multilingual" in settings.embedding_model_name:
                _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                return _model
        except Exception:
            pass
        _model_failed = True
        return None

def generate_deterministic_vector(text: str, dim: int = 384) -> list[float]:
    """
    Fallback deterministic unit vector generator based on token hashing.
    Used when PyTorch/SentenceTransformers model weights are not downloaded or offline.
    """
    vec = [0.0] * dim
    words = text.lower().split()
    if not words:
        return vec
    for word in words:
        h = int(hashlib.sha256(word.encode()).hexdigest(), 16)
        for i in range(4):
            idx = (h >> (i * 16)) % dim
            val = ((h >> (i * 8)) & 0xFF) / 128.0 - 1.0
            vec[idx] += val
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [round(x / norm, 6) for x in vec]
    return vec

def build_profile_text(
    bio: str | None = None,
    interests: str | None = None,
    skills: str | None = None,
    hobbies: str | None = None,
    skill_proficiency: str | None = None,
    hobby_engagement_level: str | None = None,
    goals: str | None = None,
    preferred_activities: str | None = None,
    preferred_community_types: str | None = None,
) -> str:
    """Combines profile attributes into a structured string for semantic embedding."""
    parts = []
    if bio and bio.strip():
        parts.append(f"Bio: {bio.strip()}")
    if interests and interests.strip():
        parts.append(f"Interests: {interests.strip()}")
    if skills and skills.strip():
        prof = f" ({skill_proficiency.strip()})" if skill_proficiency and skill_proficiency.strip() else ""
        parts.append(f"Skills: {skills.strip()}{prof}")
    if hobbies and hobbies.strip():
        eng = f" ({hobby_engagement_level.strip()})" if hobby_engagement_level and hobby_engagement_level.strip() else ""
        parts.append(f"Hobbies: {hobbies.strip()}{eng}")
    if goals and goals.strip():
        parts.append(f"Goals: {goals.strip()}")
    if preferred_activities and preferred_activities.strip():
        parts.append(f"Activities: {preferred_activities.strip()}")
    if preferred_community_types and preferred_community_types.strip():
        parts.append(f"Community Types: {preferred_community_types.strip()}")
    return " · ".join(parts).strip()

@lru_cache(maxsize=2048)
def _cached_embedding_tuple(text: str) -> tuple[float, ...]:
    model = get_embedding_model()
    if model is not None:
        try:
            vector = model.encode(text, normalize_embeddings=True)
            return tuple(float(x) for x in vector)
        except Exception as e:
            logger.warning(f"Embedding encoding failed ({e}). Falling back to hash vector.")
    return tuple(generate_deterministic_vector(text, settings.embedding_dim))

def generate_embedding(text: str) -> list[float]:
    """Generates a 384-dimensional unit vector for text with LRU caching."""
    if not text or not text.strip():
        return [0.0] * settings.embedding_dim
    return list(_cached_embedding_tuple(text.strip()))

def get_embedding_cache_info() -> dict:
    """Returns runtime LRU cache statistics for embedding generation."""
    info = _cached_embedding_tuple.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "maxsize": info.maxsize,
        "currsize": info.currsize,
    }

EMBEDDING_DIM = settings.embedding_dim

def cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Computes cosine similarity between two vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return round(max(0.0, min(1.0, dot / (norm_a * norm_b))), 6)
