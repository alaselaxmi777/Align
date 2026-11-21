import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from app.models.user import User, Profile
from app.models.community import Community
from app.models.event import Event
from app.models.place import Place
from app.models.project import Project
from app.models.opportunity import Opportunity
from app.models.assistant import AssistantConversation, AssistantMessage
from app.services.embeddings import generate_embedding, cosine_similarity
from app.services.discovery import tokens, haversine_distance

logger = logging.getLogger(__name__)

INTENT_KEYWORDS = {
    "people": ["people", "person", "peer", "peers", "developer", "developers", "mentor", "friend", "someone", "who", "user", "users"],
    "community": ["community", "communities", "group", "groups", "club", "clubs", "circle", "circles", "learn", "learning"],
    "event": ["event", "events", "meetup", "hackathon", "workshop", "conference", "webinar", "upcoming"],
    "goal": ["goal", "goals", "milestone", "career", "roadmap", "path", "achieve", "journey"],
    "place": ["place", "places", "space", "spaces", "venue", "coworking", "lab", "makerspace", "library", "near me"],
    "project": ["project", "projects", "collaborate", "collaboration", "team", "builder", "builders"],
    "opportunity": ["opportunity", "opportunities", "internship", "internships", "scholarship", "competition"],
}

def classify_user_intent(query: str) -> str:
    q_lower = query.lower()
    for intent, kws in INTENT_KEYWORDS.items():
        if any(kw in q_lower for kw in kws):
            return intent
    return "general"

def process_assistant_chat(
    db: Session,
    user: User,
    message: str,
    conversation_id: int | None = None,
) -> dict:
    # 1. Manage conversation
    if conversation_id:
        conv = db.get(AssistantConversation, conversation_id)
        if not conv or conv.user_id != user.id:
            conv = AssistantConversation(user_id=user.id, title=message[:40])
            db.add(conv)
            db.flush()
    else:
        conv = AssistantConversation(user_id=user.id, title=message[:40])
        db.add(conv)
        db.flush()

    # Save user message
    user_msg = AssistantMessage(
        conversation_id=conv.id,
        role="user",
        content=message.strip(),
    )
    db.add(user_msg)
    db.flush()

    # 2. Extract Intent and Query Real Entities
    intent = classify_user_intent(message)
    query_emb = generate_embedding(message.strip())

    action_cards = []
    reply_text = ""
    suggested_prompts = []

    if intent == "people":
        # Search real registered users
        users = list(
            db.scalars(
                select(User)
                .join(Profile, User.id == Profile.user_id, isouter=True)
                .where(User.id != user.id)
                .where(User.is_active == True)
            )
        )
        scored = []
        for u in users:
            p_emb = u.profile.embedding if u.profile else None
            sim = cosine_similarity(query_emb, p_emb) if p_emb else 0.4
            scored.append((u, sim))
        scored.sort(key=lambda x: x[1], reverse=True)

        top_peers = scored[:3]
        if top_peers:
            reply_text = f"I discovered {len(top_peers)} peers aligned with your query on ALIGN. Here are your top matches:"
            for peer, score in top_peers:
                action_cards.append({
                    "card_type": "user",
                    "id": peer.id,
                    "title": peer.name,
                    "subtitle": peer.profile.skills if peer.profile else "ALIGN Member",
                    "location": peer.profile.location if peer.profile else "Global",
                    "avatar_url": peer.profile.avatar_url if peer.profile else None,
                    "match_percentage": int(round(score * 100)),
                    "link": f"/people",
                })
            suggested_prompts = [
                "Find more peers nearby",
                "Recommend communities for our shared skills",
                "Start a project collaboration",
            ]
        else:
            reply_text = "I couldn't find any direct peer matches yet. Check out the People directory to discover new members!"
            suggested_prompts = ["Browse all members", "Explore communities"]

    elif intent == "community":
        # Search communities
        comms = list(db.scalars(select(Community)))
        scored = []
        for c in comms:
            sim = cosine_similarity(query_emb, c.embedding) if c.embedding else 0.4
            scored.append((c, sim))
        scored.sort(key=lambda x: x[1], reverse=True)

        top_comms = scored[:3]
        if top_comms:
            reply_text = f"Here are the most active and relevant communities tailored to learning and programming:"
            for c, score in top_comms:
                action_cards.append({
                    "card_type": "community",
                    "id": c.id,
                    "title": c.name,
                    "subtitle": c.category,
                    "description": c.description[:140] + ("..." if len(c.description) > 140 else ""),
                    "location": c.location,
                    "match_percentage": int(round(score * 100)),
                    "link": f"/communities/{c.id}",
                })
            suggested_prompts = [
                "Find events hosted by these communities",
                "Connect with community members",
                "Create a new interest circle",
            ]
        else:
            reply_text = "No exact community matches found. You can easily start a new community on ALIGN!"
            suggested_prompts = [
                "Explore all communities",
                "Find people interested in tech",
                "Browse upcoming events",
            ]

    elif intent == "event":
        # Search events
        evts = list(db.scalars(select(Event).where(Event.is_cancelled == False)))
        scored = []
        for e in evts:
            sim = cosine_similarity(query_emb, e.embedding) if e.embedding else 0.4
            scored.append((e, sim))
        scored.sort(key=lambda x: x[1], reverse=True)

        top_evts = scored[:3]
        if top_evts:
            reply_text = f"Found {len(top_evts)} upcoming live technology sessions and meetups for you:"
            for e, score in top_evts:
                action_cards.append({
                    "card_type": "event",
                    "id": e.id,
                    "title": e.title,
                    "subtitle": e.category,
                    "location": e.location,
                    "starts_at": e.starts_at.isoformat() if e.starts_at else None,
                    "source": e.source,
                    "link": f"/events",
                })
            suggested_prompts = [
                "RSVP to an upcoming event",
                "Find people attending these events",
                "Search online hackathons",
            ]
        else:
            reply_text = "No live events match this topic right now. Synchronizing from Eventbrite..."

    elif intent == "place":
        places = list(db.scalars(select(Place)))
        scored = []
        for p in places:
            sim = cosine_similarity(query_emb, p.embedding) if p.embedding else 0.4
            scored.append((p, sim))
        scored.sort(key=lambda x: x[1], reverse=True)

        top_places = scored[:3]
        if top_places:
            reply_text = f"Here are verified physical innovation labs, makerspaces, and third places near you:"
            for p, score in top_places:
                action_cards.append({
                    "card_type": "place",
                    "id": p.id,
                    "title": p.name,
                    "subtitle": p.category,
                    "location": f"{p.address}, {p.city}",
                    "link": f"/places",
                })
            suggested_prompts = [
                "View on Discovery Map",
                "Find coworking hubs with high-speed internet",
                "Meet peers at these venues",
            ]

    elif intent == "goal":
        reply_text = (
            f"Achieving your career and learning goals is what ALIGN was built for! "
            f"I can generate a customized multi-stage AI Goal Journey for '{message[:50]}' complete with milestones, "
            f"curated resources, and relevant peer mentors."
        )
        action_cards.append({
            "card_type": "action_cta",
            "title": "Start AI Goal Journey",
            "subtitle": f"Generate roadmap for: {message[:60]}",
            "link": "/goals/journey",
            "action_text": "Create Roadmap",
        })
        suggested_prompts = [
            "Show my current milestone progress",
            "Find peers with similar career goals",
            "Recommend internships for this path",
        ]

    else:
        # General assistance
        reply_text = (
            f"Hello! I am your ALIGN Discovery Assistant. I can help you find like-minded people, "
            f"recommend specialized learning communities, track upcoming events, generate AI Goal Journeys, "
            f"and discover project collaborators. What are you looking to achieve today?"
        )
        suggested_prompts = [
            "Find people interested in AI near me",
            "Recommend communities for learning programming",
            "Find upcoming technology events",
            "Help me achieve my career goals",
        ]

    if not suggested_prompts:
        suggested_prompts = [
            "Find people interested in AI near me",
            "Recommend communities for learning programming",
            "Find upcoming technology events",
        ]

    # Save assistant response
    assistant_msg = AssistantMessage(
        conversation_id=conv.id,
        role="assistant",
        content=reply_text,
        intent=intent,
        action_data=json.dumps(action_cards) if action_cards else None,
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "conversation_id": conv.id,
        "role": "assistant",
        "content": reply_text,
        "intent": intent,
        "action_cards": action_cards,
        "suggested_prompts": suggested_prompts,
        "created_at": assistant_msg.created_at.isoformat(),
    }
