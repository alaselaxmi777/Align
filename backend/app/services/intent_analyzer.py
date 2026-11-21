"""
Natural Language User Intent Analyzer for ALIGN Recommendation Framework.

Parses arbitrary user expressions such as:
"I want to learn artificial intelligence, meet programming enthusiasts and attend technology events near me."
Extracts:
- Multi-Class Intent Category Classification (embedding similarity + heuristic prior + calibrated confidence)
- Identified Interests
- Identified Skills
- Identified Goals
- Target Modality / Entity Preferences
- Geospatial / Location Intent
"""

import math
import re
from typing import TypedDict
from app.services.embeddings import generate_embedding, cosine_similarity

class ParsedIntent(TypedDict):
    raw_query: str
    primary_category: str
    category_confidence: float
    category_scores: dict[str, float]
    identified_interests: list[str]
    identified_skills: list[str]
    identified_goals: list[str]
    target_entities: list[str]  # e.g. ["community", "event", "user", "place"]
    location_intent: str | None
    is_near_me: bool
    modality: str  # "in-person", "online", "any"

# Domain taxonomies compiled from ALIGN's 15,000 dataset records
DOMAIN_INTERESTS = [
    "artificial intelligence", "machine learning", "deep learning", "data science",
    "web development", "mobile development", "cloud computing", "cybersecurity",
    "blockchain", "robotics", "devops", "ui/ux design", "product management",
    "entrepreneurship", "startups", "finance", "investing",
    "photography", "painting", "ceramics", "graphic design", "creative writing",
    "hiking", "trekking", "cycling", "running", "yoga", "fitness",
    "cooking", "baking", "coffee", "gardening", "board games", "reading",
    "music production", "guitar", "piano", "astronomy", "languages"
]

DOMAIN_SKILLS = [
    "python", "pytorch", "tensorflow", "scikit-learn", "keras", "pandas", "numpy",
    "react", "typescript", "javascript", "nextjs", "vue", "angular", "node.js",
    "fastapi", "django", "flask", "postgresql", "neo4j", "mongodb", "docker",
    "kubernetes", "aws", "gcp", "azure", "git", "linux", "c++", "c#", "java",
    "golang", "rust", "figma", "illustrator", "photoshop", "sql"
]

COMMON_INDIAN_CITIES = [
    "mumbai", "pune", "bangalore", "bengaluru", "delhi", "hyderabad", "chennai",
    "kolkata", "kolhapur", "ahmedabad", "jaipur", "satara", "sangli"
]

CATEGORY_PROTOTYPES: dict[str, str] = {
    "Tech & AI": "artificial intelligence machine learning python programming data science software web development cloud robotics coding algorithms devops technology ai",
    "Design & Creative Arts": "design ui ux graphic design photography creative writing digital art illustration painting animation multimedia typography",
    "Outdoor & Fitness": "outdoor hiking running sports fitness yoga cycling trekking adventures athletics workout nature wellness gym",
    "Social & Community": "social networking community gatherings meetups book club board games casual socializing friendship cultural events hangouts",
    "Career & Entrepreneurship": "startups entrepreneurship business leadership career growth finance venture capital investing management pitch hiring",
    "Education & Research": "academic scientific research university tutorials study groups higher education curriculum courses lectures mentoring thesis pedagogy",
}

_PROTOTYPE_EMBEDDINGS: dict[str, list[float]] | None = None

def _get_prototype_embeddings() -> dict[str, list[float]]:
    global _PROTOTYPE_EMBEDDINGS
    if _PROTOTYPE_EMBEDDINGS is None:
        _PROTOTYPE_EMBEDDINGS = {
            cat: generate_embedding(proto)
            for cat, proto in CATEGORY_PROTOTYPES.items()
        }
    return _PROTOTYPE_EMBEDDINGS

def classify_discovery_intent(query: str, q_emb: list[float] | None = None) -> tuple[str, float, dict[str, float]]:
    """
    Classifies a natural language query into primary discovery intent category
    with calibrated softmax confidence scores.
    Combines semantic sentence embedding similarity with heuristic token priors.
    """
    if not query or not query.strip():
        return "General Discovery", 0.0, {}

    q_lower = query.lower()
    if q_emb is None:
        q_emb = generate_embedding(query)

    proto_embs = _get_prototype_embeddings()

    # 1. Semantic embedding similarity
    sim_scores: dict[str, float] = {}
    for cat, p_emb in proto_embs.items():
        sim_scores[cat] = max(0.0, cosine_similarity(q_emb, p_emb))

    # 2. Rule-based heuristic prior from lexical keywords
    heuristic_prior: dict[str, float] = {}
    for cat, proto_text in CATEGORY_PROTOTYPES.items():
        score = 0.0
        for token in proto_text.split():
            if len(token) > 3 and token in q_lower:
                score += 0.20
        heuristic_prior[cat] = min(0.60, score)

    # 3. Ensemble combining semantic and heuristic signals
    combined: dict[str, float] = {}
    for cat in CATEGORY_PROTOTYPES:
        combined[cat] = (sim_scores[cat] * 0.70) + (heuristic_prior[cat] * 0.30)

    # 4. Softmax probability calibration (temperature tau = 0.15)
    tau = 0.15
    max_val = max(combined.values()) if combined else 0.0
    exp_vals = {cat: math.exp((v - max_val) / tau) for cat, v in combined.items()}
    sum_exp = sum(exp_vals.values()) or 1.0

    category_scores = {cat: round(exp_vals[cat] / sum_exp, 4) for cat in combined}
    primary_category = max(category_scores, key=lambda k: category_scores[k])
    confidence = category_scores[primary_category]

    return primary_category, confidence, category_scores

def analyze_user_intent(query: str) -> ParsedIntent:
    if not query:
        return {
            "raw_query": "",
            "primary_category": "General Discovery",
            "category_confidence": 0.0,
            "category_scores": {},
            "identified_interests": [],
            "identified_skills": [],
            "identified_goals": [],
            "target_entities": [],
            "location_intent": None,
            "is_near_me": False,
            "modality": "any",
        }

    q_lower = query.lower()
    q_emb = generate_embedding(query)

    # Primary discovery category classification
    primary_category, confidence, category_scores = classify_discovery_intent(query, q_emb=q_emb)

    # 1. Identify Target Entities
    target_entities = []
    if any(k in q_lower for k in ["meet", "people", "enthusiast", "enthusiasts", "collaborator", "collaborators", "peer", "peers", "mentor", "mentors", "developer", "developers"]):
        target_entities.append("user")
    if any(k in q_lower for k in ["community", "communities", "group", "groups", "club", "clubs", "circle", "circles", "society"]):
        target_entities.append("community")
    if any(k in q_lower for k in ["event", "events", "attend", "meetup", "meetups", "hackathon", "hackathons", "workshop", "workshops", "conference"]):
        target_entities.append("event")
    if any(k in q_lower for k in ["place", "places", "cafe", "cafes", "coffee", "workspace", "co-working", "library", "venue", "studio"]):
        target_entities.append("place")

    # 2. Identify Interests
    identified_interests = []
    for interest in DOMAIN_INTERESTS:
        if re.search(rf"\b{re.escape(interest)}\b", q_lower):
            identified_interests.append(interest.title())

    # 3. Identify Skills
    identified_skills = []
    for skill in DOMAIN_SKILLS:
        if re.search(rf"\b{re.escape(skill)}\b", q_lower):
            identified_skills.append(skill.upper() if len(skill) <= 3 else skill.capitalize())

    # 4. Identify Goals & Action Phrases
    identified_goals = []
    goal_patterns = [
        r"(?:want to|looking to|aiming to|hoping to|wish to)\s+([^,.;]+)",
        r"(?:learn|master|study)\s+([^,.;]+)",
        r"(?:build|create|launch|develop)\s+([^,.;]+)",
        r"(?:meet|connect with|find)\s+([^,.;]+)",
        r"(?:attend|join|participate in)\s+([^,.;]+)",
    ]
    for pattern in goal_patterns:
        matches = re.finditer(pattern, q_lower)
        for m in matches:
            cleaned = m.group(0).strip()
            if len(cleaned) > 5 and cleaned not in identified_goals:
                identified_goals.append(cleaned)

    # 5. Location and Proximity Intent
    is_near_me = bool(re.search(r"\b(near me|nearby|local|in my area|close to me|in my city)\b", q_lower))
    location_intent = None
    for city in COMMON_INDIAN_CITIES:
        if re.search(rf"\b{city}\b", q_lower):
            location_intent = city.capitalize()
            break
    if not location_intent and is_near_me:
        location_intent = "Near User"

    # 6. Modality
    modality = "any"
    if re.search(r"\b(online|virtual|remote|zoom)\b", q_lower):
        modality = "online"
    elif re.search(r"\b(in[- ]person|offline|physical|walk[- ]in)\b", q_lower) or is_near_me:
        modality = "in-person"

    return {
        "raw_query": query,
        "primary_category": primary_category,
        "category_confidence": confidence,
        "category_scores": category_scores,
        "identified_interests": identified_interests,
        "identified_skills": identified_skills,
        "identified_goals": identified_goals[:3],
        "target_entities": target_entities,
        "location_intent": location_intent,
        "is_near_me": is_near_me,
        "modality": modality,
    }
