from app.models.user import (
    User,
    Profile,
    UserPreference,
    OAuthAccount,
    PasswordResetToken,
    EmailVerificationToken,
    UserReport,
    UserBlock,
    RefreshTokenSession,
)
from app.models.community import Community, CommunityMembership
from app.models.event import Event, EventRegistration
from app.models.place import Place
from app.models.saved import SavedItem
from app.models.notification import Notification
from app.models.post import Post, PostLike, PostComment, PostMedia
from app.models.message import Message
from app.models.connection import UserConnection
from app.models.dataset import (
    SkillsHobbiesDataset,
    SkillMaster,
    HobbyMaster,
    GoalsInterestsDataset,
    GoalMaster,
    InterestMaster,
    DatasetMetadata,
)
from app.models.assistant import (
    AssistantConversation,
    AssistantMessage,
    AssistantMemory,
    AssistantSettings,
    AssistantSavedRecommendation,
    AssistantGoalJourney,
)
from app.models.circle import (
    InterestCircle,
    CircleMembership,
    CircleDiscussion,
    CircleDiscussionReply,
    CircleActivity,
)
from app.models.goal_journey import GoalJourney, GoalMilestone
from app.models.gamification import UserGamification, UserBadge, UserActivityLog
from app.models.project import Project, ProjectMember, ProjectMilestone, ProjectApplication, ProjectDiscussion
from app.models.opportunity import Opportunity, OpportunityBookmark
from app.models.reel import Reel, ReelLike, ReelComment
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.instagram import InstagramAccount, InstagramMedia, SuggestedInterest

__all__ = [
    "User",
    "Profile",
    "UserPreference",
    "OAuthAccount",
    "PasswordResetToken",
    "EmailVerificationToken",
    "UserReport",
    "UserBlock",
    "Community",
    "CommunityMembership",
    "Event",
    "EventRegistration",
    "Place",
    "SavedItem",
    "Notification",
    "Post",
    "PostLike",
    "PostComment",
    "Message",
    "UserConnection",
    "SkillsHobbiesDataset",
    "SkillMaster",
    "HobbyMaster",
    "GoalsInterestsDataset",
    "GoalMaster",
    "InterestMaster",
    "DatasetMetadata",
    "AssistantConversation",
    "AssistantMessage",
    "AssistantMemory",
    "AssistantSettings",
    "AssistantSavedRecommendation",
    "AssistantGoalJourney",
    "InterestCircle",
    "CircleMembership",
    "CircleDiscussion",
    "CircleDiscussionReply",
    "CircleActivity",
    "GoalJourney",
    "GoalMilestone",
    "UserGamification",
    "UserBadge",
    "UserActivityLog",
    "Project",
    "ProjectMember",
    "ProjectMilestone",
    "ProjectApplication",
    "ProjectDiscussion",
    "Opportunity",
    "OpportunityBookmark",
    "Reel",
    "ReelLike",
    "ReelComment",
    "InstagramAccount",
    "InstagramMedia",
    "SuggestedInterest",
]
