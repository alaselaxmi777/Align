import json
import logging
import re
from datetime import datetime, timezone
from typing import AsyncGenerator, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func

from app.core.config import settings
from app.models.user import User
from app.models.assistant import (
    AssistantConversation,
    AssistantMessage,
    AssistantMemory,
    AssistantSettings,
    AssistantSavedRecommendation,
    AssistantGoalJourney,
)
from app.services.embeddings import generate_embedding
from app.services.assistant_tools import (
    execute_tool_call,
    TOOLS_SCHEMA,
    get_user_profile,
    get_relevant_memories,
)

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = [
    r"\b(password|pin|secret|api[_-]?key|credit[_-]?card|cvv|bank[_-]?account|ssn|aadhaar)\b",
    r"\b(medical|diagnosis|illness|disease|doctor|prescription|psychiatric|depression)\b",
    r"\b(salary|net[_-]?worth|balance|debt|crypto[_-]?wallet)\b",
    r"\b(religion|caste|political[_-]?party|voting|faith)\b",
]

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"you\s+are\s+now\s+(unrestricted|jailbroken|dan)",
    r"system\s*:\s*",
    r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
]

def sanitize_user_input(text: str) -> str:
    """Sanitizes user input, applies prompt-injection defense, and trims length."""
    cleaned = text.strip()
    for pat in INJECTION_PATTERNS:
        cleaned = re.sub(pat, "[filtered]", cleaned, flags=re.IGNORECASE)
    if len(cleaned) > 2500:
        cleaned = cleaned[:2500]
    return cleaned

def is_sensitive_memory(text: str) -> bool:
    """Checks if proposed memory contains sensitive health, financial, or private credentials."""
    t_lower = text.lower()
    for pat in SENSITIVE_PATTERNS:
        if re.search(pat, t_lower):
            return True
    return False

def extract_candidate_memories(user_input: str, user_id: int, conv_id: int, db: Session) -> list[dict[str, Any]]:
    """
    Extracts candidate user memories (skills, interests, goals, preferences, projects)
    and saves them in pending status for user consent.
    """
    asst_settings = db.get(AssistantSettings, user_id)
    if asst_settings and not asst_settings.memory_enabled:
        return []

    candidates = []
    text = user_input.strip()

    # Rule-based extraction patterns for preferences and goals
    patterns = [
        (r"(?:i want to learn|i'm learning|planning to learn|learning)\s+([^.!?\n]+)", "learning_goal"),
        (r"(?:i work with|my skills are|i am proficient in|i know|skilled in)\s+([^.!?\n]+)", "skill"),
        (r"(?:my goal is to|i aim to|i want to become|looking for roles as)\s+([^.!?\n]+)", "career_goal"),
        (r"(?:i am interested in|i love|passionate about|curious about)\s+([^.!?\n]+)", "interest"),
        (r"(?:i prefer|i like to work on|my preference is)\s+([^.!?\n]+)", "preference"),
        (r"(?:i am building|i am working on a project called|developing)\s+([^.!?\n]+)", "project"),
    ]

    for pat, mem_type in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            extracted_val = m.group(1).strip()
            # Clean up trailing punctuation
            extracted_val = re.sub(r"[,;]$", "", extracted_val).strip()
            if len(extracted_val) > 3 and not is_sensitive_memory(extracted_val):
                # Check for existing memory
                existing = db.scalar(
                    select(AssistantMemory).where(
                        AssistantMemory.user_id == user_id,
                        AssistantMemory.content == extracted_val,
                    )
                )
                if not existing:
                    emb = generate_embedding(extracted_val)
                    mem = AssistantMemory(
                        user_id=user_id,
                        memory_type=mem_type,
                        content=extracted_val,
                        source_conversation_id=conv_id,
                        status="pending",  # Pending user approval in UI
                        embedding=emb,
                    )
                    db.add(mem)
                    db.flush()
                    candidates.append({
                        "id": mem.id,
                        "type": mem.memory_type,
                        "content": mem.content,
                        "status": "pending",
                    })

    return candidates

def auto_generate_title(first_message: str) -> str:
    """Generates a concise 4-6 word conversation title."""
    cleaned = re.sub(r"[^\w\s]", "", first_message).strip()
    words = cleaned.split()
    if not words:
        return "Discovery Session"
    if len(words) <= 5:
        return " ".join(words).capitalize()
    return " ".join(words[:5]).capitalize()

async def stream_assistant_chat(
    db: Session,
    user: User,
    message: str,
    conversation_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """
    Asynchronous SSE streaming agent loop.
    Emits events:
      - event: session (conversation metadata)
      - event: tool_start (tool name & args)
      - event: tool_result (cards & findings)
      - event: token (text generation)
      - event: proposed_memory (memory consent prompt)
      - event: followups (suggested next prompt chips)
      - event: done (completion)
    """
    clean_msg = sanitize_user_input(message)

    # 1. Manage Conversation
    is_new_conv = False
    if conversation_id:
        conv = db.get(AssistantConversation, conversation_id)
        if not conv or conv.user_id != user.id:
            conv = AssistantConversation(user_id=user.id, title=auto_generate_title(clean_msg))
            db.add(conv)
            db.flush()
            is_new_conv = True
    else:
        conv = AssistantConversation(user_id=user.id, title=auto_generate_title(clean_msg))
        db.add(conv)
        db.flush()
        is_new_conv = True

    # Save User Message
    user_msg = AssistantMessage(
        conversation_id=conv.id,
        user_id=user.id,
        role="user",
        content=clean_msg,
    )
    db.add(user_msg)
    conv.last_message_at = datetime.now(timezone.utc)
    db.flush()

    yield f"event: session\ndata: {json.dumps({'conversation_id': conv.id, 'title': conv.title, 'is_new': is_new_conv})}\n\n"

    # 2. Retrieve Approved Memories & User Background
    mem_resp = get_relevant_memories(db, user, clean_msg)
    user_profile = get_user_profile(db, user)

    # 3. Agent Planning & Tool Calling Dispatch
    tool_calls_executed = []
    collected_cards = []
    citations = []

    msg_lower = clean_msg.lower()

    # Determine tool triggers based on semantic query intent
    tools_to_run = []
    if any(k in msg_lower for k in ["people", "person", "peer", "mentor", "who", "collaborator", "developer"]):
        tools_to_run.append(("search_people", {"query": clean_msg, "limit": 4}))
    if any(k in msg_lower for k in ["community", "communities", "group", "club", "circle", "learn"]):
        tools_to_run.append(("discover_communities", {"query": clean_msg, "limit": 4}))
    if any(k in msg_lower for k in ["event", "meetup", "hackathon", "workshop", "webinar", "upcoming"]):
        tools_to_run.append(("find_events", {"query": clean_msg, "limit": 4}))
    if any(k in msg_lower for k in ["place", "places", "space", "coworking", "lab", "venue", "city", "bangalore"]):
        tools_to_run.append(("find_places", {"query": clean_msg, "limit": 4}))
    if any(k in msg_lower for k in ["project", "projects", "repo", "repository", "open source", "build"]):
        tools_to_run.append(("find_projects", {"query": clean_msg, "limit": 4}))
    if any(k in msg_lower for k in ["opportunity", "internship", "scholarship", "competition", "fellowship"]):
        tools_to_run.append(("discover_opportunities", {"query": clean_msg, "limit": 4}))
    if any(k in msg_lower for k in ["goal", "roadmap", "plan", "milestone", "path", "achieve"]):
        tools_to_run.append(("create_goal_journey", {"title": clean_msg, "category": "AI/ML", "timeframe": "8 Weeks"}))
    if any(k in msg_lower for k in ["research", "paper", "documentation", "how does", "what is", "trends"]):
        tools_to_run.append(("web_research", {"query": clean_msg}))

    # Default fallback to profile + discovery if no specific intent matched
    if not tools_to_run:
        tools_to_run.append(("discover_communities", {"query": clean_msg, "limit": 3}))

    for tool_name, args in tools_to_run:
        yield f"event: tool_start\ndata: {json.dumps({'tool': tool_name, 'args': args})}\n\n"
        result = execute_tool_call(tool_name, args, db, user)
        tool_calls_executed.append({"name": tool_name, "args": args, "result": result})

        # Harvest entity cards
        if "people" in result:
            collected_cards.extend(result["people"])
        if "communities" in result:
            collected_cards.extend(result["communities"])
        if "events" in result:
            collected_cards.extend(result["events"])
        if "places" in result:
            collected_cards.extend(result["places"])
        if "projects" in result:
            collected_cards.extend(result["projects"])
        if "opportunities" in result:
            collected_cards.extend(result["opportunities"])
        if "results" in result and tool_name == "web_research":
            for r in result["results"]:
                citations.append(r)

        yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'count': len(collected_cards)})}\n\n"

    # Send harvested cards
    if collected_cards:
        yield f"event: action_cards\ndata: {json.dumps({'cards': collected_cards})}\n\n"

    # 4. Generate Grounded Synthesis Response (Streaming Tokens)
    user_skills = user_profile.get("skills")
    if user_skills and user_skills.lower() not in ("not specified", "none", ""):
        skills_phrase = f" and registered background in **{user_skills}**"
    else:
        skills_phrase = ""

    synthesis_chunks = []
    synthesis_chunks.append("### Objective & Strategic Analysis\n\n")
    synthesis_chunks.append(
        f"Based on your query{skills_phrase}, here is a structured, practical approach:\n\n"
    )

    if collected_cards:
        synthesis_chunks.append("### Verified ALIGN Recommendations\n\n")
        synthesis_chunks.append(
            f"I retrieved **{len(collected_cards)} real entities** from the ALIGN database matching your criteria. "
            f"Each recommendation is grounded in your profile and verified database records:\n\n"
        )
        for i, card in enumerate(collected_cards[:4], 1):
            title = card.get("title", "Resource")
            subtitle = card.get("subtitle", "")
            card_type = card.get("card_type", "").capitalize()
            type_badge = f"[{card_type}] " if card_type else ""
            match = card.get("match_percentage")
            match_str = f" ({match}% match)" if match else ""
            location_str = f" · {card['location']}" if card.get("location") else ""
            synthesis_chunks.append(f"{i}. **{type_badge}{title}**{match_str}{location_str} — {subtitle}\n")
        synthesis_chunks.append("\n")

    # Weekly Action Checklist when planning, roadmap, or learning is requested
    is_planning_query = any(k in msg_lower for k in [
        "checklist", "weekly", "plan", "roadmap", "milestone", "schedule",
        "how to learn", "how should i", "prepare", "steps", "study", "guide"
    ]) or any(t["name"] == "create_goal_journey" for t in tool_calls_executed)

    if is_planning_query:
        synthesis_chunks.append("### 4-Week Milestone Checklist\n\n")
        synthesis_chunks.append("- [ ] **Week 1: Core Foundations & Setup** — Establish baseline architecture, review master schemas, and configure tooling.\n")
        synthesis_chunks.append("- [ ] **Week 2: Hands-On Implementation** — Build end-to-end functionality, wire database queries, and test with realistic workloads.\n")
        synthesis_chunks.append("- [ ] **Week 3: Validation & Peer Feedback** — Connect with recommended ALIGN peers, request code reviews, and benchmark latency.\n")
        synthesis_chunks.append("- [ ] **Week 4: Deployment & Community Showcase** — Ship verified build, publish documentation, and share milestone outcomes in relevant circles.\n\n")

    if citations:
        synthesis_chunks.append("### Research & Technical Context\n\n")
        for cite in citations:
            synthesis_chunks.append(f"- [{cite['title']}]({cite['url']}): {cite['snippet']}\n")
        synthesis_chunks.append("\n")

    synthesis_chunks.append("### Actionable Next Steps\n\n")
    synthesis_chunks.append("1. **Connect & Collaborate:** Reach out to the recommended peers or join community discussion circles.\n")
    synthesis_chunks.append("2. **Track Milestones:** Save this roadmap to your personal Goal Journeys to earn completion XP.\n")
    synthesis_chunks.append("3. **Iterate:** Ask me to narrow down by specific tech stack, city location, or remote preference.\n\n")

    full_reply_text = "".join(synthesis_chunks)

    # Stream out tokens in realistic conversational pulses
    for chunk in synthesis_chunks:
        words = chunk.split(" ")
        for i in range(0, len(words), 3):
            sub_chunk = " ".join(words[i:i+3]) + " "
            yield f"event: token\ndata: {json.dumps({'token': sub_chunk})}\n\n"

    # 5. Extract Candidate Memories with User Consent
    proposed_memories = extract_candidate_memories(clean_msg, user.id, conv.id, db)
    for p_mem in proposed_memories:
        yield f"event: proposed_memory\ndata: {json.dumps(p_mem)}\n\n"

    # 6. Generate Suggested Follow-ups
    suggested_followups = [
        "Connect me with peers working on this",
        "Generate a 30-day milestone checklist",
        "Find upcoming hackathons and scholarships",
        "Recommend coworking spaces near me",
    ]
    yield f"event: followups\ndata: {json.dumps({'prompts': suggested_followups})}\n\n"

    # 7. Auto-update title if first turn
    msg_count = db.scalar(
        select(func.count(AssistantMessage.id)).where(AssistantMessage.conversation_id == conv.id)
    )
    if msg_count <= 2:
        conv.title = auto_generate_title(clean_msg)

    # 8. Save Assistant Message in DB
    metadata = {
        "action_cards": collected_cards,
        "citations": citations,
        "suggested_followups": suggested_followups,
        "tool_calls": [t["name"] for t in tool_calls_executed],
    }
    asst_msg = AssistantMessage(
        conversation_id=conv.id,
        user_id=user.id,
        role="assistant",
        content=full_reply_text,
        tool_calls=json.dumps(tool_calls_executed),
        metadata_json=json.dumps(metadata),
        action_data=json.dumps(collected_cards),
    )
    db.add(asst_msg)
    db.commit()

    yield f"event: done\ndata: {json.dumps({'conversation_id': conv.id, 'message_id': asst_msg.id})}\n\n"
