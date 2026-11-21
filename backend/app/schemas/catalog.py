from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class CommunityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5, max_length=5000)
    category: str = "General"
    tags: str = ""
    location: str = "Online"
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    is_private: bool = False

class CommunityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, min_length=5, max_length=5000)
    category: str | None = None
    tags: str | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    is_private: bool | None = None

class CommunityResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    tags: str
    location: str
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    is_private: bool = False
    is_test: bool = False
    created_by_id: int | None = None
    owner_name: str | None = None
    owner_avatar: str | None = None
    created_at: datetime | None = None
    member_count: int = 0
    is_member: bool = False
    model_config = ConfigDict(from_attributes=True)

class EventCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5, max_length=5000)
    category: str = "Meetup"
    location: str = "Online"
    latitude: float | None = None
    longitude: float | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = None
    community_id: int | None = None

class EventResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    location: str
    latitude: float | None = None
    longitude: float | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = None
    is_cancelled: bool = False
    source: str = "ALIGN"
    external_id: str | None = None
    event_url: str | None = None
    created_by_id: int | None = None
    community_id: int | None = None
    created_at: datetime | None = None
    registered_count: int = 0
    is_registered: bool = False
    is_external: bool = False
    is_expired: bool = False
    model_config = ConfigDict(from_attributes=True)

class PlaceResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    address: str
    city: str
    source: str = "ALIGN"
    latitude: float
    longitude: float
    image_url: str | None = None
    distance_km: float | None = None
    model_config = ConfigDict(from_attributes=True)

class SavedItemCreate(BaseModel):
    item_type: str = Field(pattern="^(community|event|place|user|post|reel)$")
    item_id: int

class SavedItemResponse(BaseModel):
    id: int
    item_type: str
    item_id: int
    created_at: datetime
    title: str | None = None
    description: str | None = None
    category: str | None = None
    location: str | None = None
    model_config = ConfigDict(from_attributes=True)

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    link: str | None = None
    is_read: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DiscoveryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=12, ge=1, le=50)
    user_lat: float | None = None
    user_lon: float | None = None
    category: str | None = None

class DiscoveryResult(BaseModel):
    result_type: str  # "community" | "event" | "place" | "user" | "project" | "opportunity"
    id: int
    title: str
    description: str
    category: str
    location: str
    score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    matched_terms: list[str] = Field(default_factory=list)
    graph_path: str | None = None
    reason: str
    why_recommended: str | None = None
    matching_factors: list[str] = Field(default_factory=list)
    location_relevance: str | None = None
    source: str | None = "ALIGN"
    is_verified: bool = True
    distance_km: float | None = None
    distance_band: str | None = None
    tags: str | None = None
    is_eventbrite: bool = False
    event_url: str | None = None
    starts_at: datetime | None = None
    avatar_url: str | None = None
    profile_url: str | None = None
    skills: list[str] | None = None

class RecommendationFeedbackCreate(BaseModel):
    item_type: str = Field(pattern="^(community|event|place|user|project|opportunity)$")
    item_id: int
    feedback: str = Field(pattern="^(relevant|not_relevant|already_done|save_for_later)$")
    notes: str | None = None

class RecommendationFeedbackResponse(BaseModel):
    id: int
    user_id: int
    item_type: str
    item_id: int
    feedback: str
    notes: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class GithubSyncRequest(BaseModel):
    github_username: str

class EventRegisterRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    ticket_count: int = 1
    notes: str | None = None
