from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.community import Community, CommunityMembership
from app.models.post import Post, PostLike, PostComment
from app.models.notification import Notification
from app.models.user import User
from app.schemas.catalog import CommunityCreate, CommunityUpdate, CommunityResponse
from app.schemas.social import PostResponse, PostAuthor, PostCreate
from app.services.embeddings import generate_embedding
from app.services.gamification_service import award_xp, check_and_unlock_badge, get_or_create_gamification
from app.services.graph_service import graph_service

CATEGORY_COVER_IMAGES = {
    "technology": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80",
    "outdoors": "https://images.unsplash.com/photo-1551632811-561732d1e306?w=1200&auto=format&fit=crop&q=80",
    "design": "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=1200&auto=format&fit=crop&q=80",
    "career": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=1200&auto=format&fit=crop&q=80",
    "arts": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=1200&auto=format&fit=crop&q=80",
    "general": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&auto=format&fit=crop&q=80",
}

router = APIRouter(prefix="/communities", tags=["communities"])

def populate_community_response(comm: Community, user: User | None, db: Session) -> CommunityResponse:
    count = db.scalar(
        select(func.count(CommunityMembership.id)).where(
            CommunityMembership.community_id == comm.id,
            CommunityMembership.status == "active"
        )
    ) or 0
    is_mem = False
    if user:
        is_mem = db.scalar(
            select(func.count(CommunityMembership.id)).where(
                CommunityMembership.community_id == comm.id,
                CommunityMembership.user_id == user.id,
                CommunityMembership.status == "active"
            )
        ) > 0
    owner = db.get(User, comm.created_by_id) if comm.created_by_id else None
    owner_name = owner.name if owner else "ALIGN Team"
    owner_avatar = owner.profile.avatar_url if (owner and owner.profile) else None

    # Ensure category cover image is populated in row
    if not comm.image_url:
        cat_key = (comm.category or "general").strip().lower()
        comm.image_url = CATEGORY_COVER_IMAGES.get(cat_key, CATEGORY_COVER_IMAGES["general"])

    res = CommunityResponse.model_validate(comm)
    res.image_url = comm.image_url
    res.member_count = count
    res.is_member = is_mem
    res.owner_name = owner_name
    res.owner_avatar = owner_avatar
    return res

@router.get("", response_model=list[CommunityResponse])
def list_communities(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    stmt = select(Community).where(Community.is_test == False).order_by(Community.created_at.desc())
    if category:
        stmt = stmt.where(Community.category.ilike(f"%{category.strip()}%"))
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Community.name.ilike(term),
                Community.description.ilike(term),
                Community.tags.ilike(term),
                Community.location.ilike(term),
            )
        )
    stmt = stmt.limit(limit)
    items = list(db.scalars(stmt))
    return [populate_community_response(c, user, db) for c in items]

@router.post("", response_model=CommunityResponse, status_code=status.HTTP_201_CREATED)
def create_community(
    payload: CommunityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    text_content = f"{payload.name} {payload.description} {payload.category} {payload.tags} {payload.location}"
    emb = generate_embedding(text_content)
    comm_data = payload.model_dump()
    if not comm_data.get("image_url"):
        cat_key = (payload.category or "general").strip().lower()
        comm_data["image_url"] = CATEGORY_COVER_IMAGES.get(cat_key, CATEGORY_COVER_IMAGES["general"])

    item = Community(
        **comm_data,
        created_by_id=user.id,
        is_test=getattr(user, "is_test", False),
        embedding=emb,
    )
    db.add(item)
    db.flush()

    # Automatically add creator as admin member
    membership = CommunityMembership(
        user_id=user.id,
        community_id=item.id,
        role="admin",
        status="active"
    )
    db.add(membership)
    db.commit()
    db.refresh(item)

    # Real-time sync to Neo4j Knowledge Graph
    try:
        graph_service.sync_community_membership(user.id, item.id, joined=True, role="admin")
    except Exception:
        pass

    # Award authentic XP & Badge
    award_xp(db, user.id, "community_created", 100, f"Created community: {item.name[:30]}", dedup_key=f"community_create:{item.id}")
    game = get_or_create_gamification(db, user.id)
    check_and_unlock_badge(db, game, "PIONEER")

    return populate_community_response(item, user, db)

@router.get("/{community_id}", response_model=CommunityResponse)
def get_community(
    community_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    comm = db.get(Community, community_id)
    if not comm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    return populate_community_response(comm, user, db)

@router.put("/{community_id}", response_model=CommunityResponse)
def update_community(
    community_id: int,
    payload: CommunityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comm = db.get(Community, community_id)
    if not comm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    if comm.created_by_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the community creator or an administrator can update this community.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(comm, field, val)

    if any(k in update_data for k in ("name", "description", "category", "tags", "location")):
        ctx = f"{comm.name} {comm.description} {comm.category} {comm.tags} {comm.location}"
        comm.embedding = generate_embedding(ctx)

    db.commit()
    db.refresh(comm)
    return populate_community_response(comm, user, db)

@router.delete("/{community_id}")
def delete_community(
    community_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comm = db.get(Community, community_id)
    if not comm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    if comm.created_by_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the community creator or an administrator can delete this community.")

    db.delete(comm)
    db.commit()
    return {"status": "ok", "message": f"Community '{comm.name}' deleted successfully."}

@router.post("/{community_id}/join")
def join_community(
    community_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comm = db.get(Community, community_id)
    if not comm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    
    existing = db.scalar(
        select(CommunityMembership).where(
            CommunityMembership.community_id == community_id,
            CommunityMembership.user_id == user.id,
        )
    )
    if existing:
        if existing.status == "active":
            return {"status": "ok", "message": "You are already an active member of this community."}
        existing.status = "active"
        db.commit()
        return {"status": "ok", "message": "Re-joined community successfully."}

    membership = CommunityMembership(
        user_id=user.id,
        community_id=comm.id,
        role="member",
        status="active"
    )
    db.add(membership)

    # Award authentic XP with anti-duplicate dedup key
    award_xp(db, user.id, "community_joined", 25, f"Joined community: {comm.name[:30]}", dedup_key=f"community_join:{comm.id}:{user.id}")

    # Notify community lead
    if comm.created_by_id and comm.created_by_id != user.id:
        db.add(
            Notification(
                user_id=comm.created_by_id,
                title="New Community Member",
                message=f"{user.name} joined your community '{comm.name}'.",
                link=f"/communities/{comm.id}",
            )
        )

    db.commit()

    # Real-time sync to Neo4j Knowledge Graph
    try:
        graph_service.sync_community_membership(user.id, comm.id, joined=True, role="member")
    except Exception:
        pass

    return {"status": "ok", "message": "Joined community successfully."}

@router.post("/{community_id}/leave")
def leave_community(
    community_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = db.scalar(
        select(CommunityMembership).where(
            CommunityMembership.community_id == community_id,
            CommunityMembership.user_id == user.id,
        )
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not a member of this community.")
    
    db.delete(existing)
    db.commit()

    # Real-time sync to Neo4j Knowledge Graph
    try:
        graph_service.sync_community_membership(user.id, community_id, joined=False)
    except Exception:
        pass

    return {"status": "ok", "message": "Left community successfully."}

@router.get("/{community_id}/posts", response_model=list[PostResponse])
def get_community_posts(
    community_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    comm = db.get(Community, community_id)
    if not comm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")

    stmt = (
        select(Post)
        .where(Post.community_id == community_id)
        .order_by(desc(Post.created_at))
        .limit(limit)
    )
    posts = list(db.scalars(stmt))
    results: list[PostResponse] = []
    for p in posts:
        author_data = (
            PostAuthor(
                id=p.author.id,
                name=p.author.name,
                avatar_url=p.author.profile.avatar_url if p.author.profile else None,
            )
            if p.author
            else None
        )
        likes_count = db.scalar(select(func.count(PostLike.id)).where(PostLike.post_id == p.id)) or 0
        comments_count = db.scalar(select(func.count(PostComment.id)).where(PostComment.post_id == p.id)) or 0
        is_liked = False
        if user:
            is_liked = (db.scalar(select(func.count(PostLike.id)).where(PostLike.post_id == p.id, PostLike.user_id == user.id)) or 0) > 0

        results.append(
            PostResponse(
                id=p.id,
                author_id=p.author_id,
                community_id=p.community_id,
                content=p.content,
                image_url=p.image_url,
                created_at=p.created_at,
                author=author_data,
                community_name=comm.name,
                likes_count=likes_count,
                comments_count=comments_count,
                is_liked=is_liked,
            )
        )
    return results

@router.post("/{community_id}/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_community_post(
    community_id: int,
    payload: PostCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comm = db.get(Community, community_id)
    if not comm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")

    new_post = Post(
        author_id=user.id,
        community_id=community_id,
        content=payload.content.strip(),
        image_url=payload.image_url,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    author_data = PostAuthor(
        id=user.id,
        name=user.name,
        avatar_url=user.profile.avatar_url if user.profile else None,
    )

    return PostResponse(
        id=new_post.id,
        author_id=new_post.author_id,
        community_id=new_post.community_id,
        content=new_post.content,
        image_url=new_post.image_url,
        created_at=new_post.created_at,
        author=author_data,
        community_name=comm.name,
        likes_count=0,
        comments_count=0,
        is_liked=False,
    )
