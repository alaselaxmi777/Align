from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class SkillMasterResponse(BaseModel):
    id: int
    category: str
    type: str
    description: str
    model_config = ConfigDict(from_attributes=True)

class HobbyMasterResponse(BaseModel):
    id: int
    category: str
    type: str
    description: str
    model_config = ConfigDict(from_attributes=True)

class SkillHobbyDatasetItem(BaseModel):
    id: int
    record_id: str
    record_type: str
    category: str
    type: str
    description: str
    application_context: str
    proficiency_engagement_level: str
    setting: str
    frequency: Optional[str] = None
    primary_motivation: Optional[str] = None
    popularity_score: int
    expanded_record_description: str
    model_config = ConfigDict(from_attributes=True)

class CategorySummary(BaseModel):
    category: str
    count: int
    sample_types: List[str]

class DatasetStatsResponse(BaseModel):
    total_records: int
    skills_count: int
    hobbies_count: int
    skill_types_count: int
    hobby_types_count: int
    categories: List[CategorySummary]


# ---------------------------------------------------------------------------
# Goals & Interests schemas
# ---------------------------------------------------------------------------

class GoalMasterResponse(BaseModel):
    id: int
    category: str
    type: str
    description: str
    model_config = ConfigDict(from_attributes=True)


class InterestMasterResponse(BaseModel):
    id: int
    category: str
    type: str
    description: str
    model_config = ConfigDict(from_attributes=True)


class GoalInterestDatasetItem(BaseModel):
    id: int
    record_id: str
    record_type: str
    category: str
    type: str
    description: str
    life_context: Optional[str] = None
    timeline_engagement_level: Optional[str] = None
    priority_setting: Optional[str] = None
    status_frequency: Optional[str] = None
    primary_motivation: Optional[str] = None
    popularity_score: int
    expanded_record_description: str
    model_config = ConfigDict(from_attributes=True)


class GoalsInterestsStatsResponse(BaseModel):
    total_records: int
    goals_count: int
    interests_count: int
    goal_types_count: int
    interest_types_count: int
    categories: List[CategorySummary]
