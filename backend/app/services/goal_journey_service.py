import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from app.models.goal_journey import GoalJourney, GoalMilestone
from app.models.community import Community
from app.models.event import Event
from app.models.user import User, Profile
from app.models.place import Place
from app.services.embeddings import generate_embedding, cosine_similarity
from app.services.gamification_service import award_xp, check_and_unlock_badge, get_or_create_gamification

logger = logging.getLogger(__name__)

# Template frameworks for popular career & tech goals with customizable milestones
GOAL_FRAMEWORKS = {
    "ai_ml": [
        {
            "step": 1,
            "title": "Foundations: Python, PyTorch & Linear Algebra",
            "desc": "Master tensors, gradient descent, neural network architectures, and vector math.",
            "weeks": 3,
            "resources": ["PyTorch Official Tutorials", "Fast.ai Practical Deep Learning", "3Blue1Brown Linear Algebra"],
        },
        {
            "step": 2,
            "title": "Dense Embeddings & Vector Search",
            "desc": "Build vector indexing pipelines using pgvector, sentence-transformers, and cosine similarity.",
            "weeks": 3,
            "resources": ["pgvector Handbook", "Sentence-Transformers Docs", "Hugging Face Vector Search Guide"],
        },
        {
            "step": 3,
            "title": "Full-Stack AI Application Architecture",
            "desc": "Design zero-latency FastAPI microservices, asynchronous inference, and React interactive frontends.",
            "weeks": 4,
            "resources": ["FastAPI Async Architecture", "React Query + TypeScript Guide", "Docker Deployment Best Practices"],
        },
        {
            "step": 4,
            "title": "Capstone: Production Open-Source Showcase",
            "desc": "Deploy an end-to-end multi-modal discovery or agentic application and present to community peers.",
            "weeks": 4,
            "resources": ["Hugging Face Spaces", "GitHub Actions CI/CD", "Technical Case Study Writing"],
        },
    ],
    "fullstack": [
        {
            "step": 1,
            "title": "Modern Frontend Mastery with React 18 & TypeScript",
            "desc": "Master component lifecycles, custom hooks, Tailwind CSS design tokens, and state management.",
            "weeks": 3,
            "resources": ["React 18 Docs", "TypeScript Deep Dive", "Tailwind CSS Component Patterns"],
        },
        {
            "step": 2,
            "title": "Backend Microservices with Python FastAPI & SQLAlchemy",
            "desc": "Build RESTful API endpoints, JWT auth, schema validation with Pydantic, and database relationships.",
            "weeks": 3,
            "resources": ["FastAPI in Production", "SQLAlchemy 2.0 ORM Guide", "PostgreSQL Indexing Essentials"],
        },
        {
            "step": 3,
            "title": "Knowledge Graph & Semantic Search Integration",
            "desc": "Integrate Neo4j graph databases with pgvector embeddings for hybrid personalized recommendation.",
            "weeks": 4,
            "resources": ["Neo4j Cypher Manual", "Hybrid Search Paradigms", "Knowledge Graph Architecture"],
        },
        {
            "step": 4,
            "title": "End-to-End System Deployment & Monitoring",
            "desc": "Containerize with multi-stage Docker builds, orchestrate with Docker Compose, and automate tests.",
            "weeks": 2,
            "resources": ["Docker Compose Production Guide", "Pytest Suite Best Practices", "Vite Performance Optimization"],
        },
    ],
    "general": [
        {
            "step": 1,
            "title": "Goal Discovery & Core Skill Audit",
            "desc": "Assess current capabilities, outline fundamental prerequisites, and join aligned peer circles.",
            "weeks": 2,
            "resources": ["ALIGN Skills Catalog", "Roadmap.sh Developer Paths"],
        },
        {
            "step": 2,
            "title": "Focused Skill Acquisition & Hands-on Labs",
            "desc": "Complete targeted coursework, practice real problem sets, and participate in local workshops.",
            "weeks": 4,
            "resources": ["Coursera / edX Labs", "Open-Source Community Discussions"],
        },
        {
            "step": 3,
            "title": "Community Collaboration & Hackathon Challenge",
            "desc": "Team up with complementary peers in an ALIGN Project to solve real-world problems under deadlines.",
            "weeks": 4,
            "resources": ["Devpost Hackathons", "ALIGN Project Collaboration Hub"],
        },
        {
            "step": 4,
            "title": "Portfolio Delivery & Peer Review",
            "desc": "Package learnings into documented portfolio assets and receive feedback from mentors and communities.",
            "weeks": 2,
            "resources": ["GitHub Portfolio Guidelines", "LinkedIn Showcase Playbook"],
        },
    ],
}

def generate_goal_journey(
    db: Session,
    user: User,
    goal_title: str,
    timeframe: str = "3-6 months",
    category: str = "Career & Learning",
) -> GoalJourney:
    text_content = f"{goal_title} {category} {timeframe}"
    emb = generate_embedding(text_content)

    journey = GoalJourney(
        user_id=user.id,
        title=goal_title.strip(),
        target_category=category,
        timeframe=timeframe,
        description=f"AI-generated personalized learning and career milestone path for '{goal_title}'.",
        status="in_progress",
        progress_percentage=0,
        embedding=emb,
    )
    db.add(journey)
    db.flush()

    # Determine framework
    lower_title = goal_title.lower()
    if any(k in lower_title for k in ["ai", "machine learning", "ml", "deep learning", "llm", "data science"]):
        template = GOAL_FRAMEWORKS["ai_ml"]
    elif any(k in lower_title for k in ["fullstack", "full-stack", "react", "fastapi", "web", "software", "frontend", "backend"]):
        template = GOAL_FRAMEWORKS["fullstack"]
    else:
        template = GOAL_FRAMEWORKS["general"]

    # Retrieve real communities, events, and peers for embedding relevance
    all_communities = list(db.scalars(select(Community).limit(20)))
    all_events = list(db.scalars(select(Event).where(Event.is_cancelled == False).limit(20)))
    all_peers = list(
        db.scalars(
            select(User)
            .join(Profile, User.id == Profile.user_id, isouter=True)
            .where(User.id != user.id)
            .limit(15)
        )
    )

    for item in template:
        step_emb = generate_embedding(f"{item['title']} {item['desc']}")

        # Match relevant communities
        matched_comms = []
        for c in all_communities:
            sim = cosine_similarity(step_emb, c.embedding) if c.embedding else 0.4
            if sim >= 0.35:
                matched_comms.append({"id": c.id, "name": c.name, "category": c.category, "similarity": round(sim, 2)})
        matched_comms.sort(key=lambda x: x["similarity"], reverse=True)

        # Match relevant events
        matched_evts = []
        for e in all_events:
            sim = cosine_similarity(step_emb, e.embedding) if e.embedding else 0.4
            if sim >= 0.35:
                matched_evts.append({"id": e.id, "title": e.title, "location": e.location, "similarity": round(sim, 2)})
        matched_evts.sort(key=lambda x: x["similarity"], reverse=True)

        # Match relevant peers
        matched_peers = []
        for p in all_peers:
            p_emb = p.profile.embedding if p.profile else None
            sim = cosine_similarity(step_emb, p_emb) if p_emb else 0.4
            if sim >= 0.40:
                matched_peers.append({
                    "id": p.id,
                    "name": p.name,
                    "avatar_url": p.profile.avatar_url if p.profile else None,
                    "skills": p.profile.skills if p.profile else "",
                })

        milestone = GoalMilestone(
            journey_id=journey.id,
            step_order=item["step"],
            title=item["title"],
            description=item["desc"],
            estimated_weeks=item["weeks"],
            is_completed=False,
            recommended_resources=json.dumps(item["resources"]),
            recommended_communities_json=json.dumps(matched_comms[:2]),
            recommended_events_json=json.dumps(matched_evts[:2]),
            recommended_peers_json=json.dumps(matched_peers[:2]),
        )
        db.add(milestone)

    # Award starter XP
    award_xp(db, user.id, "goal_journey_started", 40, f"Created Goal Journey: {goal_title[:40]}")
    game = get_or_create_gamification(db, user.id)
    check_and_unlock_badge(db, game, "GOAL_CRUSHER")

    db.commit()
    db.refresh(journey)
    return journey
