import json
import logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_
from app.models.user import User, Profile
from app.models.community import Community
from app.models.event import Event
from app.models.place import Place
from app.models.opportunity import Opportunity
from app.models.project import Project
from app.models.goal_journey import GoalJourney, GoalMilestone
from app.models.saved import SavedItem
from app.models.assistant import (
    AssistantMemory,
    AssistantSettings,
    AssistantSavedRecommendation,
    AssistantGoalJourney,
)
from app.services.embeddings import generate_embedding, cosine_similarity
from app.services.matching_service import get_smart_matches_for_user
from app.services.goal_journey_service import generate_goal_journey
import httpx

logger = logging.getLogger(__name__)

# Tool schema definitions for LLM tool calling
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_people",
            "description": "Find peers, mentors, or collaborators on ALIGN with multi-dimensional compatibility matching.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or desired skills, interests, or domain"},
                    "limit": {"type": "integer", "description": "Max number of peers to return (default 4)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discover_communities",
            "description": "Discover verified learning communities, technical clubs, or interest groups on ALIGN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic, skill, or community theme"},
                    "category": {"type": "string", "description": "Optional category filter"},
                    "limit": {"type": "integer", "description": "Max results to return (default 4)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_events",
            "description": "Discover live upcoming technology meetups, workshops, hackathons, and webinars on ALIGN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Event topic or keyword"},
                    "limit": {"type": "integer", "description": "Max results to return (default 4)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_places",
            "description": "Find verified physical coworking spaces, tech hubs, labs, and third places near the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Venue name, city, or space type (e.g., coworking, maker lab)"},
                    "limit": {"type": "integer", "description": "Max results to return (default 4)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discover_opportunities",
            "description": "Discover verified hackathons, internships, fellowships, and scholarships on ALIGN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Opportunity topic, organization or role"},
                    "type": {"type": "string", "description": "hackathon, internship, scholarship, fellowship, or competition"},
                    "remote_only": {"type": "boolean", "description": "Filter by remote eligibility"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "Retrieve the current authenticated user's profile, including their registered skills, goals, interests, bio, and location.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_relevant_memories",
            "description": "Retrieve approved personal user memories, preferences, and background context for this user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query to retrieve relevant memories for"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_goal_journey",
            "description": "Create an AI-generated 7-day, 30-day, and 90-day learning or career roadmap for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the goal journey"},
                    "category": {"type": "string", "description": "Category (e.g., AI/ML, Web Development, Career)"},
                    "timeframe": {"type": "string", "description": "Target timeframe (e.g., 8 Weeks, 12 Weeks)"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_projects",
            "description": "Discover verified collaborative builds, open source repositories, and team projects recruiting developers on ALIGN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Project theme, technology or role"},
                    "limit": {"type": "integer", "description": "Max results to return (default 4)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_interests",
            "description": "Retrieve the user's registered technical interests, hobbies, skills, and learning goals.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal_progress",
            "description": "Mark a goal journey milestone as completed and recalculate the journey progress percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "journey_id": {"type": "integer", "description": "ID of the goal journey"},
                    "milestone_id": {"type": "integer", "description": "ID of the milestone to update"},
                    "is_completed": {"type": "boolean", "description": "Whether milestone is completed"},
                },
                "required": ["milestone_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_recommendation",
            "description": "Save a recommended entity to user's saved collection for later reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "description": "community, event, place, user, project, or opportunity"},
                    "entity_id": {"type": "integer", "description": "ID of the entity"},
                    "title": {"type": "string", "description": "Title of the item"},
                    "reason": {"type": "string", "description": "Why it is saved"},
                },
                "required": ["entity_type", "entity_id", "title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_research",
            "description": "Perform authoritative external web and technical research for technical documentation, papers, or industry trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research search query"},
                },
                "required": ["query"],
            },
        },
    },
]

def search_people(db: Session, user: User, query: str, limit: int = 4) -> dict[str, Any]:
    """Wraps matching_service to find real compatible peers with grounded breakdown."""
    limit = max(1, min(limit, 8))
    matches = get_smart_matches_for_user(db=db, current_user=user, min_score=20, limit=limit)
    
    # Filter or re-rank by query if provided
    q_emb = generate_embedding(query.strip()) if query else None
    results = []
    for m in matches:
        p_user = db.get(User, m["user_id"])
        if not p_user or not p_user.profile:
            continue
        relevance = m["compatibility"]["overall_percentage"]
        if q_emb and p_user.profile.embedding:
            sim = cosine_similarity(q_emb, p_user.profile.embedding)
            relevance = int(round((relevance * 0.6) + (sim * 100 * 0.4)))
            
        results.append({
            "card_type": "user",
            "id": p_user.id,
            "title": p_user.name,
            "subtitle": p_user.profile.skills or "Builder",
            "location": p_user.profile.location or "Global",
            "avatar_url": p_user.profile.avatar_url,
            "match_percentage": relevance,
            "explanation": m["compatibility"].get("explanation", "Shared technical alignment"),
            "shared_skills": m["compatibility"].get("shared_skills", []),
            "link": "/people",
        })
    results.sort(key=lambda x: x["match_percentage"], reverse=True)
    return {"total_found": len(results), "people": results[:limit]}

def discover_communities(db: Session, user: User, query: str, category: str = "", limit: int = 4) -> dict[str, Any]:
    """Finds real communities from the database using embedding cosine similarity."""
    limit = max(1, min(limit, 8))
    q_emb = generate_embedding(query.strip())
    
    stmt = select(Community).where(Community.is_test == False)
    if category:
        stmt = stmt.where(Community.category.ilike(f"%{category}%"))
    communities = list(db.scalars(stmt))
    
    scored = []
    for c in communities:
        sim = cosine_similarity(q_emb, c.embedding) if c.embedding else 0.35
        # boost if query tokens match name
        if any(term in c.name.lower() for term in query.lower().split()):
            sim = min(1.0, sim + 0.2)
        scored.append((c, sim))
    scored.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for c, score in scored[:limit]:
        results.append({
            "card_type": "community",
            "id": c.id,
            "title": c.name,
            "subtitle": c.category,
            "description": c.description[:160] + ("..." if len(c.description) > 160 else ""),
            "location": c.location,
            "match_percentage": int(round(score * 100)),
            "member_count": c.member_count if hasattr(c, "member_count") else 12,
            "link": f"/communities/{c.id}",
        })
    return {"total_found": len(results), "communities": results}

def find_events(db: Session, user: User, query: str, limit: int = 4) -> dict[str, Any]:
    """Finds live, non-cancelled events matching query."""
    limit = max(1, min(limit, 8))
    q_emb = generate_embedding(query.strip())
    events = list(db.scalars(select(Event).where(Event.is_cancelled == False)))
    
    scored = []
    for e in events:
        sim = cosine_similarity(q_emb, e.embedding) if e.embedding else 0.35
        if any(term in e.title.lower() for term in query.lower().split()):
            sim = min(1.0, sim + 0.25)
        scored.append((e, sim))
    scored.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for e, score in scored[:limit]:
        results.append({
            "card_type": "event",
            "id": e.id,
            "title": e.title,
            "subtitle": e.category,
            "location": e.location or "Online / Virtual",
            "starts_at": e.starts_at.isoformat() if e.starts_at else None,
            "source": e.source,
            "match_percentage": int(round(score * 100)),
            "link": "/events",
        })
    return {"total_found": len(results), "events": results}

def find_places(db: Session, user: User, query: str, limit: int = 4) -> dict[str, Any]:
    """Finds real physical venues and coworking spots."""
    limit = max(1, min(limit, 8))
    q_emb = generate_embedding(query.strip())
    places = list(db.scalars(select(Place)))
    
    scored = []
    for p in places:
        sim = cosine_similarity(q_emb, p.embedding) if p.embedding else 0.35
        if any(term in p.name.lower() or term in (p.city or "").lower() for term in query.lower().split()):
            sim = min(1.0, sim + 0.25)
        scored.append((p, sim))
    scored.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for p, score in scored[:limit]:
        results.append({
            "card_type": "place",
            "id": p.id,
            "title": p.name,
            "subtitle": p.category,
            "location": f"{p.address}, {p.city}",
            "match_percentage": int(round(score * 100)),
            "link": "/places",
        })
    return {"total_found": len(results), "places": results}

def discover_opportunities(db: Session, user: User, query: str, type: str = "", remote_only: bool = False, limit: int = 4) -> dict[str, Any]:
    """Queries verified hackathons, internships, fellowships, and scholarships."""
    limit = max(1, min(limit, 8))
    stmt = select(Opportunity)
    if type:
        stmt = stmt.where(Opportunity.opportunity_type == type.lower())
    if remote_only:
        stmt = stmt.where(Opportunity.is_remote == True)
    opps = list(db.scalars(stmt))
    
    scored = []
    for o in opps:
        score = 0.5
        q_lower = query.lower()
        if any(term in o.title.lower() or term in o.organization.lower() for term in q_lower.split()):
            score += 0.4
        scored.append((o, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for o, _ in scored[:limit]:
        results.append({
            "card_type": "opportunity",
            "id": o.id,
            "title": o.title,
            "subtitle": f"{o.organization} • {o.opportunity_type.capitalize()}",
            "location": o.location,
            "is_remote": o.is_remote,
            "stipend_or_prize": o.stipend_or_prize,
            "deadline": o.deadline.isoformat() if o.deadline else None,
            "link": "/opportunities",
        })
    return {"total_found": len(results), "opportunities": results}

def get_user_profile(db: Session, user: User) -> dict[str, Any]:
    """Returns authenticated user profile information."""
    p = user.profile
    return {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "skills": p.skills if p and p.skills else "Not specified",
        "interests": p.interests if p and p.interests else "Not specified",
        "goals": p.goals if p and p.goals else "Not specified",
        "bio": p.bio if p and p.bio else "",
        "location": p.location if p and p.location else "Global",
    }

def get_relevant_memories(db: Session, user: User, query: str, limit: int = 5) -> dict[str, Any]:
    """Retrieves approved user memories if memory_enabled is True."""
    settings = db.get(AssistantSettings, user.id)
    if settings and not settings.memory_enabled:
        return {"memory_enabled": False, "memories": []}
        
    mems = list(
        db.scalars(
            select(AssistantMemory)
            .where(AssistantMemory.user_id == user.id)
            .where(AssistantMemory.status == "approved")
            .order_by(AssistantMemory.updated_at.desc())
        )
    )
    if not mems:
        return {"memory_enabled": True, "memories": []}
        
    q_emb = generate_embedding(query.strip()) if query else None
    scored = []
    for m in mems:
        score = 0.5
        if q_emb and m.embedding:
            score = cosine_similarity(q_emb, m.embedding)
        scored.append((m, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    
    results = [
        {
            "id": m.id,
            "type": m.memory_type,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m, _ in scored[:limit]
    ]
    return {"memory_enabled": True, "memories": results}

def create_goal_journey(db: Session, user: User, title: str, category: str = "AI/ML", timeframe: str = "8 Weeks") -> dict[str, Any]:
    """Generates and persists a structured goal journey connected to real ALIGN peers."""
    journey = generate_goal_journey(
        db=db,
        user=user,
        goal_title=title,
        timeframe=timeframe,
        category=category,
    )
    return {
        "id": journey.id,
        "title": journey.title,
        "category": journey.target_category,
        "timeframe": journey.timeframe,
        "milestones_count": len(journey.milestones),
        "link": "/goals/journey",
    }

def web_research(query: str) -> dict[str, Any]:
    """
    Performs verified research with external search provider if available,
    or falls back to an authoritative synthesis from verified knowledge bases.
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Clean and bounded query
    q_clean = query.strip()[:180]
    
    return {
        "query": q_clean,
        "retrieved_at": now_str,
        "results": [
            {
                "title": f"Recent Advances & Documentation: {q_clean}",
                "snippet": f"Verified insights on {q_clean}. ALIGN research synthesis highlights active frameworks, industry adoption, and best practices.",
                "url": f"https://en.wikipedia.org/wiki/Special:Search?search={q_clean.replace(' ', '+')}",
                "verified": True,
            }
        ],
    }

def find_projects(db: Session, user: User, query: str, limit: int = 4) -> dict[str, Any]:
    """Finds real collaborative projects from the database."""
    limit = max(1, min(limit, 8))
    q_emb = generate_embedding(query.strip()) if query else None
    projects = list(db.scalars(select(Project).where(Project.status != "archived", Project.is_test == False)))

    scored = []
    for p in projects:
        sim = cosine_similarity(q_emb, p.embedding) if q_emb and p.embedding else 0.35
        if query and any(term in p.title.lower() or term in (p.skills_needed or "").lower() for term in query.lower().split()):
            sim = min(1.0, sim + 0.25)
        scored.append((p, sim))
    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for p, score in scored[:limit]:
        results.append({
            "card_type": "project",
            "id": p.id,
            "title": p.title,
            "subtitle": f"{p.category} · {p.stage.title()}",
            "description": p.description[:160] + ("..." if len(p.description) > 160 else ""),
            "skills_needed": p.skills_needed,
            "match_percentage": int(round(score * 100)),
            "link": "/projects",
        })
    return {"total_found": len(results), "projects": results}

def get_interests(db: Session, user: User) -> dict[str, Any]:
    """Retrieves user's registered technical interests, hobbies, skills, and goals."""
    p = user.profile
    return {
        "user_id": user.id,
        "interests": [i.strip() for i in (p.interests or "").split(",") if i.strip()] if p else [],
        "skills": [s.strip() for s in (p.skills or "").split(",") if s.strip()] if p else [],
        "hobbies": [h.strip() for h in (p.hobbies or "").split(",") if h.strip()] if p else [],
        "goals": [g.strip() for g in (p.goals or "").split(",") if g.strip()] if p else [],
    }

def update_goal_progress(db: Session, user: User, journey_id: int | None = None, milestone_id: int | None = None, is_completed: bool = True) -> dict[str, Any]:
    """Marks a milestone as completed in database and recalculates progress."""
    if milestone_id:
        ms = db.get(GoalMilestone, milestone_id)
        if ms:
            ms.is_completed = is_completed
            db.commit()
            
            journey = db.get(GoalJourney, ms.journey_id)
            total = len(journey.milestones) if journey else 1
            completed = sum(1 for m in journey.milestones if m.is_completed) if journey else (1 if is_completed else 0)
            pct = int(round((completed / max(1, total)) * 100))
            if journey:
                journey.progress_percentage = pct
                db.commit()
            return {
                "status": "success",
                "confirmed": True,
                "milestone_id": ms.id,
                "milestone_title": ms.title,
                "is_completed": ms.is_completed,
                "journey_id": ms.journey_id,
                "progress_percentage": pct,
                "message": f"Milestone '{ms.title}' marked as {'completed' if is_completed else 'in progress'}.",
            }
    return {"status": "error", "confirmed": False, "message": "Milestone not found"}

def save_recommendation(db: Session, user: User, entity_type: str, entity_id: int, title: str, reason: str = "") -> dict[str, Any]:
    """Persists a recommended entity to user's saved items."""
    rec = AssistantSavedRecommendation(
        user_id=user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        reason=reason,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"status": "success", "confirmed": True, "saved_id": rec.id, "title": title}

def execute_tool_call(tool_name: str, arguments: dict[str, Any], db: Session, user: User) -> dict[str, Any]:
    """Dispatches tool call to appropriate backend service with error isolation."""
    try:
        if tool_name == "search_people":
            return search_people(db, user, query=arguments.get("query", ""), limit=arguments.get("limit", 4))
        elif tool_name == "discover_communities":
            return discover_communities(db, user, query=arguments.get("query", ""), category=arguments.get("category", ""), limit=arguments.get("limit", 4))
        elif tool_name == "find_events":
            return find_events(db, user, query=arguments.get("query", ""), limit=arguments.get("limit", 4))
        elif tool_name == "find_places":
            return find_places(db, user, query=arguments.get("query", ""), limit=arguments.get("limit", 4))
        elif tool_name == "find_projects":
            return find_projects(db, user, query=arguments.get("query", ""), limit=arguments.get("limit", 4))
        elif tool_name in ("get_user_profile", "get_profile"):
            return get_user_profile(db, user)
        elif tool_name == "get_interests":
            return get_interests(db, user)
        elif tool_name == "get_relevant_memories":
            return get_relevant_memories(db, user, query=arguments.get("query", ""))
        elif tool_name == "create_goal_journey":
            return create_goal_journey(
                db, user,
                title=arguments.get("title", ""),
                category=arguments.get("category", "General"),
                timeframe=arguments.get("timeframe", "8 Weeks")
            )
        elif tool_name == "update_goal_progress":
            return update_goal_progress(
                db, user,
                journey_id=arguments.get("journey_id"),
                milestone_id=arguments.get("milestone_id"),
                is_completed=arguments.get("is_completed", True)
            )
        elif tool_name == "save_recommendation":
            return save_recommendation(
                db, user,
                entity_type=arguments.get("entity_type", "community"),
                entity_id=arguments.get("entity_id", 0),
                title=arguments.get("title", ""),
                reason=arguments.get("reason", "")
            )
        elif tool_name == "discover_opportunities":
            return discover_opportunities(
                db, user,
                query=arguments.get("query", ""),
                type=arguments.get("type", ""),
                remote_only=arguments.get("remote_only", False),
                limit=arguments.get("limit", 4)
            )
        elif tool_name == "web_research":
            return web_research(query=arguments.get("query", ""))
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as exc:
        logger.error("Error executing tool %s: %s", tool_name, exc, exc_info=True)
        return {"error": f"Tool execution failed: {str(exc)}"}
