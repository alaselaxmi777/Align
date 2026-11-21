from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.community import Community
from app.models.event import Event
from app.models.place import Place
from app.models.post import Post
from app.models.saved import SavedItem
from app.models.user import User
from app.schemas.catalog import SavedItemCreate, SavedItemResponse

router = APIRouter(prefix="/saved", tags=["saved_items"])

def enrich_saved_item(item: SavedItem, db: Session) -> SavedItemResponse:
    res = SavedItemResponse.model_validate(item)
    if item.item_type == "community":
        comm = db.get(Community, item.item_id)
        if comm:
            res.title = comm.name
            res.description = comm.description
            res.category = comm.category
            res.location = comm.location
    elif item.item_type == "event":
        evt = db.get(Event, item.item_id)
        if evt:
            res.title = evt.title
            res.description = evt.description
            res.category = evt.category
            res.location = evt.location
    elif item.item_type == "place":
        pl = db.get(Place, item.item_id)
        if pl:
            res.title = pl.name
            res.description = pl.description
            res.category = pl.category
            res.location = f"{pl.address}, {pl.city}"
    elif item.item_type == "post":
        p = db.get(Post, item.item_id)
        if p:
            author_name = p.author.name if p.author else "Community Member"
            res.title = f"Post by {author_name}"
            res.description = p.content
            res.category = "Post"
            res.location = p.community.name if p.community else "Feed"
    elif item.item_type == "user":
        u = db.get(User, item.item_id)
        if u:
            res.title = u.name
            res.description = u.profile.bio if u.profile else "ALIGN Member"
            res.category = "Peer"
            res.location = u.profile.location if (u.profile and u.profile.location) else "Online"
    elif item.item_type == "reel":
        res.title = res.title or f"Reel #{item.item_id}"
        res.category = "Reel"
        res.location = "Video"
    return res

@router.get("", response_model=list[SavedItemResponse])
def get_saved_items(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = list(db.scalars(
        select(SavedItem).where(SavedItem.user_id == user.id).order_by(SavedItem.created_at.desc())
    ))
    return [enrich_saved_item(item, db) for item in items]

@router.post("", response_model=SavedItemResponse, status_code=status.HTTP_201_CREATED)
def save_item(payload: SavedItemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.scalar(
        select(SavedItem).where(
            SavedItem.user_id == user.id,
            SavedItem.item_type == payload.item_type,
            SavedItem.item_id == payload.item_id,
        )
    )
    if existing:
        return enrich_saved_item(existing, db)

    item = SavedItem(
        user_id=user.id,
        item_type=payload.item_type,
        item_id=payload.item_id
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return enrich_saved_item(item, db)

@router.post("/{item_type}/{item_id}", response_model=SavedItemResponse, status_code=status.HTTP_201_CREATED)
def save_item_by_path(item_type: str, item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.scalar(
        select(SavedItem).where(
            SavedItem.user_id == user.id,
            SavedItem.item_type == item_type,
            SavedItem.item_id == item_id,
        )
    )
    if existing:
        return enrich_saved_item(existing, db)

    item = SavedItem(
        user_id=user.id,
        item_type=item_type,
        item_id=item_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return enrich_saved_item(item, db)

@router.delete("/{item_type}/{item_id}")
def unsave_item(item_type: str, item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.scalar(
        select(SavedItem).where(
            SavedItem.user_id == user.id,
            SavedItem.item_type == item_type,
            SavedItem.item_id == item_id,
        )
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved item not found")
    
    db.delete(existing)
    db.commit()
    return {"status": "ok", "message": "Item removed from saved list."}
