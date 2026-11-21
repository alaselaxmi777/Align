from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.graph_service import graph_service

router = APIRouter(prefix="/graph", tags=["Graph & Knowledge Base"])


@router.get("/health")
def get_graph_health():
    """Returns connectivity and basic counts of the Neo4j Knowledge Graph."""
    return graph_service.check_health()


@router.get("/stats")
def get_graph_stats():
    """Returns detailed counts of nodes and relationships by label/type in the Neo4j Knowledge Graph."""
    stats = graph_service.get_graph_stats()
    return stats


@router.post("/sync")
def sync_graph_database(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Synchronizes all users, profiles, communities, events, places, and memberships
    from PostgreSQL into the Neo4j Knowledge Graph.
    """
    result = graph_service.sync_all_from_postgres(db)
    return result


@router.get("/affinity/community/{community_id}")
def get_community_affinity(
    community_id: int,
    current_user: User = Depends(get_current_user),
):
    """Calculates graph-based affinity between the current user and a community."""
    score = graph_service.get_community_graph_score(current_user.id, community_id)
    return {
        "user_id": current_user.id,
        "community_id": community_id,
        "graph_affinity_score": score,
    }


@router.get("/affinity/peer/{target_user_id}")
def get_peer_affinity(
    target_user_id: int,
    current_user: User = Depends(get_current_user),
):
    """Calculates graph-based affinity between the current user and another peer."""
    score = graph_service.get_peer_graph_score(current_user.id, target_user_id)
    return {
        "user_id": current_user.id,
        "target_user_id": target_user_id,
        "graph_affinity_score": score,
    }
