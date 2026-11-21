from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class PostMediaItem(BaseModel):
    id: int | None = None
    position: int = 0
    media_type: str = "image"
    original_url: str
    feed_url: str
    thumbnail_url: str
    width: int | None = None
    height: int | None = None
    alt_text: str | None = None
    model_config = ConfigDict(from_attributes=True)

class PostMediaCreate(BaseModel):
    position: int = 0
    media_type: str = "image"
    original_url: str
    feed_url: str
    thumbnail_url: str
    width: int | None = None
    height: int | None = None
    alt_text: str | None = None

class PostCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2200)
    community_id: int | None = None
    image_url: str | None = None
    visibility: str = Field(default="connections_only", pattern="^(public|connections_only)$")
    location_area: str | None = Field(default=None, max_length=120)
    media_items: list[PostMediaCreate] = Field(default_factory=list, max_length=10)

class PostAuthor(BaseModel):
    id: int
    name: str
    avatar_url: str | None = None
    model_config = ConfigDict(from_attributes=True)

class PostResponse(BaseModel):
    id: int
    author_id: int
    community_id: int | None = None
    content: str
    image_url: str | None = None
    visibility: str = "connections_only"
    location_area: str | None = None
    is_pinned: bool = False
    media: list[PostMediaItem] = Field(default_factory=list)
    created_at: datetime
    author: PostAuthor | None = None
    community_name: str | None = None
    likes_count: int = 0
    is_liked: bool = False
    comments_count: int = 0
    score: float | None = None
    score_breakdown: dict[str, float] | None = None
    why_recommended: str | None = None
    model_config = ConfigDict(from_attributes=True)

class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = None

class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    parent_id: int | None = None
    created_at: datetime
    author_name: str | None = None
    author_avatar: str | None = None
    replies: list["CommentResponse"] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class ShareRequest(BaseModel):
    recipient_id: int
    note: str | None = Field(default=None, max_length=500)

class MessageCreate(BaseModel):
    receiver_id: int
    content: str = Field(min_length=1, max_length=5000)

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    is_read: bool = False
    created_at: datetime
    sender_name: str | None = None
    receiver_name: str | None = None
    model_config = ConfigDict(from_attributes=True)

class AdminStatsResponse(BaseModel):
    total_users: int
    total_communities: int
    total_events: int
    total_places: int
    total_posts: int
    total_registrations: int
    total_dataset_records: int = 0
    total_reports: int = 0
    database_status: str
    pgvector_status: str
    neo4j_status: str = "connected"

class CreateReportRequest(BaseModel):
    target_type: str = Field(default="post", pattern="^(post|reel|user|comment)$")
    target_id: int
    reason: str = Field(min_length=2, max_length=100)
    details: str | None = Field(default=None, max_length=1000)

class ModerationActionRequest(BaseModel):
    action: str = Field(pattern="^(remove_content|warn_user|suspend_user|dismiss_report)$")
    note: str | None = Field(default=None, max_length=500)

class ReportDetailResponse(BaseModel):
    id: int
    reporter_id: int
    reporter_name: str
    reported_user_id: int | None = None
    reported_user_name: str | None = None
    target_type: str
    post_id: int | None = None
    reel_id: int | None = None
    content_snippet: str | None = None
    reason: str
    details: str | None = None
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
