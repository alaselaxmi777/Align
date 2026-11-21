import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func

from app.core.config import settings
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.assistant import (
    AssistantConversation,
    AssistantMessage,
    AssistantMemory,
    AssistantSettings,
    AssistantSavedRecommendation,
    AssistantGoalJourney,
)
from app.services.assistant_service import process_assistant_chat
from app.services.assistant_v2_service import stream_assistant_chat, sanitize_user_input
from app.services.embeddings import generate_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])

# Schemas
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2500)
    conversation_id: int | None = None

class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New Discovery Session", max_length=200)

class ConversationUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    pinned: bool | None = None
    archived: bool | None = None

class MemoryUpdateRequest(BaseModel):
    content: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, pattern="^(approved|rejected|pending)$")

class SettingsUpdateRequest(BaseModel):
    memory_enabled: bool | None = None
    auto_suggest_followups: bool | None = None
    research_enabled: bool | None = None

class SaveRecommendationRequest(BaseModel):
    entity_type: str = Field(pattern="^(user|community|event|place|opportunity|resource)$")
    entity_id: int
    title: str = Field(max_length=255)
    reason: str | None = None

class RecommendationFeedbackRequest(BaseModel):
    feedback: str = Field(pattern="^(useful|not_useful|dismissed)$")

# --- CONVERSATIONS CRUD ---

@router.get("/conversations")
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    filter_type: str = Query(default="active", pattern="^(all|active|pinned|archived)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(AssistantConversation).where(AssistantConversation.user_id == user.id)

    if filter_type == "active":
        stmt = stmt.where(AssistantConversation.archived == False)
    elif filter_type == "pinned":
        stmt = stmt.where(AssistantConversation.pinned == True, AssistantConversation.archived == False)
    elif filter_type == "archived":
        stmt = stmt.where(AssistantConversation.archived == True)

    if search:
        stmt = stmt.where(AssistantConversation.title.ilike(f"%{search.strip()}%"))

    # Order pinned first, then last_message_at desc
    stmt = stmt.order_by(
        AssistantConversation.pinned.desc(),
        AssistantConversation.last_message_at.desc().nullslast(),
        AssistantConversation.created_at.desc(),
    ).offset(offset).limit(limit)

    convs = list(db.scalars(stmt))
    return [
        {
            "id": c.id,
            "title": c.title,
            "pinned": c.pinned,
            "archived": c.archived,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else c.created_at.isoformat(),
            "message_count": len(c.messages),
        }
        for c in convs
    ]

@router.post("/conversations")
def create_conversation(
    payload: ConversationCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = AssistantConversation(
        user_id=user.id,
        title=payload.title.strip() or "New Discovery Session",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {
        "id": conv.id,
        "title": conv.title,
        "pinned": conv.pinned,
        "archived": conv.archived,
        "created_at": conv.created_at.isoformat(),
    }

@router.get("/conversations/{conv_id}")
def get_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.get(AssistantConversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return {
        "id": conv.id,
        "title": conv.title,
        "pinned": conv.pinned,
        "archived": conv.archived,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else conv.created_at.isoformat(),
        "message_count": len(conv.messages),
    }

@router.patch("/conversations/{conv_id}")
def update_conversation(
    conv_id: int,
    payload: ConversationUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.get(AssistantConversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if payload.title is not None:
        conv.title = payload.title.strip()
    if payload.pinned is not None:
        conv.pinned = payload.pinned
    if payload.archived is not None:
        conv.archived = payload.archived

    db.commit()
    return {
        "id": conv.id,
        "title": conv.title,
        "pinned": conv.pinned,
        "archived": conv.archived,
    }

@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.get(AssistantConversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    db.delete(conv)
    db.commit()
    return {"status": "success", "message": "Conversation deleted"}

@router.get("/conversations/{conv_id}/messages")
def get_conversation_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.get(AssistantConversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    msgs = []
    for m in conv.messages:
        action_cards = []
        if m.action_data:
            try:
                action_cards = json.loads(m.action_data)
            except Exception:
                pass
        
        meta = {}
        if m.metadata_json:
            try:
                meta = json.loads(m.metadata_json)
            except Exception:
                pass

        msgs.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "intent": m.intent,
            "action_cards": action_cards,
            "citations": meta.get("citations", []),
            "suggested_followups": meta.get("suggested_followups", []),
            "created_at": m.created_at.isoformat(),
        })
    return msgs

# --- STREAMING & SYNC CHAT ---

@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Server-Sent Events streaming chat endpoint with real tool execution."""
    return StreamingResponse(
        stream_assistant_chat(
            db=db,
            user=user,
            message=payload.message,
            conversation_id=payload.conversation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.post("/chat")
def chat_sync(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Synchronous fallback endpoint."""
    return process_assistant_chat(
        db=db,
        user=user,
        message=payload.message,
        conversation_id=payload.conversation_id,
    )

@router.post("/chat/regenerate")
async def chat_regenerate(
    conv_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Regenerates the last assistant turn using the last user prompt."""
    conv = db.get(AssistantConversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Find last user message
    user_msgs = [m for m in conv.messages if m.role == "user"]
    if not user_msgs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No prior user messages to regenerate")

    last_user_msg = user_msgs[-1]
    return StreamingResponse(
        stream_assistant_chat(
            db=db,
            user=user,
            message=last_user_msg.content,
            conversation_id=conv.id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )

# --- MEMORIES SYSTEM ---

@router.get("/memories")
def list_memories(
    status_filter: str | None = Query(default=None, pattern="^(all|approved|pending|rejected)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(AssistantMemory).where(AssistantMemory.user_id == user.id)
    if status_filter and status_filter != "all":
        stmt = stmt.where(AssistantMemory.status == status_filter)
    stmt = stmt.order_by(AssistantMemory.updated_at.desc())

    memories = list(db.scalars(stmt))
    return [
        {
            "id": m.id,
            "type": m.memory_type,
            "content": m.content,
            "status": m.status,
            "created_at": m.created_at.isoformat(),
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in memories
    ]

@router.patch("/memories/{mem_id}")
def update_memory(
    mem_id: int,
    payload: MemoryUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mem = db.get(AssistantMemory, mem_id)
    if not mem or mem.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    if payload.content is not None:
        mem.content = payload.content.strip()
        mem.embedding = generate_embedding(mem.content)
    if payload.status is not None:
        mem.status = payload.status

    db.commit()
    return {"id": mem.id, "content": mem.content, "status": mem.status}

@router.delete("/memories/{mem_id}")
def delete_memory(
    mem_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mem = db.get(AssistantMemory, mem_id)
    if not mem or mem.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    db.delete(mem)
    db.commit()
    return {"status": "success", "message": "Memory removed"}

@router.delete("/memories")
def clear_all_memories(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mems = list(db.scalars(select(AssistantMemory).where(AssistantMemory.user_id == user.id)))
    for m in mems:
        db.delete(m)
    db.commit()
    return {"status": "success", "message": f"Cleared {len(mems)} memories"}

# --- SETTINGS ---

@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asst_set = db.get(AssistantSettings, user.id)
    if not asst_set:
        asst_set = AssistantSettings(user_id=user.id, memory_enabled=True)
        db.add(asst_set)
        db.commit()
        db.refresh(asst_set)

    return {
        "user_id": user.id,
        "memory_enabled": asst_set.memory_enabled,
        "auto_suggest_followups": asst_set.auto_suggest_followups,
        "research_enabled": asst_set.research_enabled,
    }

@router.patch("/settings")
def update_settings(
    payload: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asst_set = db.get(AssistantSettings, user.id)
    if not asst_set:
        asst_set = AssistantSettings(user_id=user.id)
        db.add(asst_set)

    if payload.memory_enabled is not None:
        asst_set.memory_enabled = payload.memory_enabled
    if payload.auto_suggest_followups is not None:
        asst_set.auto_suggest_followups = payload.auto_suggest_followups
    if payload.research_enabled is not None:
        asst_set.research_enabled = payload.research_enabled

    db.commit()
    return {
        "user_id": user.id,
        "memory_enabled": asst_set.memory_enabled,
        "auto_suggest_followups": asst_set.auto_suggest_followups,
        "research_enabled": asst_set.research_enabled,
    }

# --- SAVED RECOMMENDATIONS ---

@router.get("/recommendations")
def list_saved_recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    recs = list(
        db.scalars(
            select(AssistantSavedRecommendation)
            .where(AssistantSavedRecommendation.user_id == user.id)
            .order_by(AssistantSavedRecommendation.created_at.desc())
        )
    )
    return [
        {
            "id": r.id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "title": r.title,
            "reason": r.reason,
            "feedback": r.feedback,
            "created_at": r.created_at.isoformat(),
        }
        for r in recs
    ]

@router.post("/recommendations")
def save_recommendation(
    payload: SaveRecommendationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = AssistantSavedRecommendation(
        user_id=user.id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        title=payload.title,
        reason=payload.reason,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"status": "success", "id": rec.id, "title": rec.title}

@router.post("/recommendations/{rec_id}/feedback")
def submit_recommendation_feedback(
    rec_id: int,
    payload: RecommendationFeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = db.get(AssistantSavedRecommendation, rec_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    rec.feedback = payload.feedback
    db.commit()
    return {"status": "success", "id": rec.id, "feedback": rec.feedback}
