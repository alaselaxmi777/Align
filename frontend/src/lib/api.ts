import { formatApiError } from "./errorUtils";

const RAW_API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1").trim();
const API_BASE = RAW_API_BASE.replace(/\/+$/, "");

export function resolveMediaUrl(url?: string | null): string {
  if (!url) return "";
  const trimmed = url.trim();
  if (
    trimmed.startsWith("blob:") ||
    trimmed.startsWith("data:") ||
    /^https?:\/\//i.test(trimmed)
  ) {
    return trimmed;
  }
  // Relative path like /uploads/...: resolve against backend host
  const backendBase = API_BASE
    .replace(/\/api\/v1\/?$/, "")
    .replace(/\/+$/, "");
  const cleanPath = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  return `${backendBase}${cleanPath}`;
}

export function sanitizeExternalUrl(url?: string | null): string {
  if (!url) return "#";
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  return "#";
}

export type Community = {
  id: number;
  name: string;
  description: string;
  category: string;
  tags: string;
  location: string;
  latitude?: number | null;
  longitude?: number | null;
  image_url?: string | null;
  is_private?: boolean;
  created_by_id?: number | null;
  owner_name?: string | null;
  owner_avatar?: string | null;
  created_at?: string | null;
  member_count?: number;
  is_member?: boolean;
  score?: number | null;
  score_breakdown?: {
    semantic: number;
    keyword: number;
    graph: number;
    geo: number;
    category: number;
    feedback: number;
  } | null;
  why_recommended?: string | null;
  matched_terms?: string[] | null;
  graph_path?: string | null;
};

export type EventItem = {
  id: number;
  title: string;
  description: string;
  category: string;
  location: string;
  latitude?: number | null;
  longitude?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
  capacity?: number | null;
  is_cancelled?: boolean;
  source?: string | null;
  event_url?: string | null;
  is_external?: boolean;
  is_expired?: boolean;
  created_by_id?: number | null;
  community_id?: number | null;
  created_at?: string | null;
  registered_count?: number;
  is_registered?: boolean;
  score?: number | null;
  score_breakdown?: {
    semantic: number;
    keyword: number;
    graph: number;
    geo: number;
    category: number;
    feedback: number;
  } | null;
  why_recommended?: string | null;
  matched_terms?: string[] | null;
  graph_path?: string | null;
};

export type PlaceItem = {
  id: number;
  name: string;
  description: string;
  category: string;
  address: string;
  city: string;
  latitude: number;
  longitude: number;
  image_url?: string | null;
  distance_km?: number | null;
  score?: number | null;
  score_breakdown?: {
    semantic: number;
    keyword: number;
    graph: number;
    geo: number;
    category: number;
    feedback: number;
  } | null;
  why_recommended?: string | null;
  matched_terms?: string[] | null;
  graph_path?: string | null;
};

export type DiscoveryResult = {
  result_type: "community" | "event" | "place" | "user" | "project" | "opportunity";
  id: number;
  title: string;
  description: string;
  category: string;
  location: string;
  score: number;
  score_breakdown?: {
    semantic: number;
    keyword: number;
    graph: number;
    geo: number;
    category: number;
    feedback: number;
  };
  matched_terms?: string[];
  graph_path?: string | null;
  reason: string;
  why_recommended?: string | null;
  matching_factors?: string[];
  location_relevance?: string | null;
  is_verified?: boolean;
  distance_km?: number | null;
  distance_band?: string | null;
  tags?: string | null;
  source?: string | null;
  is_eventbrite?: boolean;
  event_url?: string | null;
  starts_at?: string | null;
  avatar_url?: string | null;
  profile_url?: string | null;
  skills?: string[] | null;
};

export type RecommendationFeedbackType = "relevant" | "not_relevant" | "already_done" | "save_for_later";

export interface RecommendationFeedbackItem {
  id: number;
  user_id: number;
  item_type: string;
  item_id: number;
  feedback: RecommendationFeedbackType;
  notes?: string | null;
  created_at: string;
}

export interface RegistrationResult {
  status: string;
  message: string;
  ticket_code?: string;
  event_id?: number;
  event_title?: string;
  starts_at?: string;
  location?: string;
  attendee_name?: string;
  attendee_email?: string;
  ticket_count?: number;
}

export type Profile = {
  id: number;
  user_id: number;
  name?: string;
  bio: string;
  avatar_url?: string | null;
  location: string;
  latitude?: number | null;
  longitude?: number | null;
  privacy_level: string;
  location_privacy?: string;
  interests: string;
  skills: string;
  hobbies?: string;
  skill_proficiency?: string;
  hobby_engagement_level?: string;
  goals: string;
  preferred_activities: string;
  preferred_community_types: string;
  age_cohort?: string | null;
  gender?: string | null;
  preferred_language?: string | null;
  onboarding_step?: number;
  onboarding_completed: boolean;
  followers_count?: number;
  following_count?: number;
  connections_count?: number;
};

export type User = {
  id: number;
  username?: string | null;
  name: string;
  email: string;
  bio?: string;
  interests?: string;
  skills?: string;
  hobbies?: string;
  is_active: boolean;
  is_verified: boolean;
  is_admin: boolean;
  profile?: Profile | null;
  connection_status?: string | null;
  connection_id?: number | null;
  is_connection_sender?: boolean | null;
  recommendation_reason?: string | null;
  followers_count?: number;
  following_count?: number;
  connections_count?: number;
  match_score?: number | null;
  distance_band?: string | null;
};

export type SkillMaster = {
  id: number;
  category: string;
  type: string;
  description: string;
};

export type HobbyMaster = {
  id: number;
  category: string;
  type: string;
  description: string;
};

export type SkillHobbyDatasetItem = {
  id: number;
  record_id: string;
  record_type: "Skill" | "Hobby";
  category: string;
  type: string;
  description: string;
  application_context: string;
  proficiency_engagement_level: string;
  setting: string;
  frequency?: string | null;
  primary_motivation?: string | null;
  popularity_score: number;
  expanded_record_description: string;
};

export type CategorySummary = {
  category: string;
  count: number;
  sample_types: string[];
};

export type DatasetStats = {
  total_records: number;
  skills_count: number;
  hobbies_count: number;
  skill_types_count: number;
  hobby_types_count: number;
  categories: CategorySummary[];
};

export type DatasetFacets = {
  contexts: string[];
  proficiencies: string[];
  settings: string[];
  frequencies: string[];
  motivations: string[];
};

// Goals & Interests types
export type GoalMaster = {
  id: number;
  category: string;
  type: string;
  description: string;
};

export type InterestMaster = {
  id: number;
  category: string;
  type: string;
  description: string;
};

export type GoalInterestDatasetItem = {
  id: number;
  record_id: string;
  record_type: "Goal" | "Interest";
  category: string;
  type: string;
  description: string;
  life_context?: string | null;
  timeline_engagement_level?: string | null;
  priority_setting?: string | null;
  status_frequency?: string | null;
  primary_motivation?: string | null;
  popularity_score: number;
  expanded_record_description: string;
};

export type GoalsInterestsStats = {
  total_records: number;
  goals_count: number;
  interests_count: number;
  goal_types_count: number;
  interest_types_count: number;
  categories: CategorySummary[];
};

export type GoalsInterestsFacets = {
  life_contexts: string[];
  timelines: string[];
  priorities: string[];
  frequencies: string[];
  motivations: string[];
};

export type AdminStats = {
  total_users: number;
  total_communities: number;
  total_events: number;
  total_places: number;
  total_posts: number;
  total_registrations: number;
  total_dataset_records: number;
  total_reports: number;
  database_status: string;
  pgvector_status: string;
  neo4j_status: string;
};

export type DataHealthResponse = {
  timestamp: string;
  status: string;
  sources: Array<{
    name: string;
    status: string;
    last_successful_fetch: string | null;
    policy: string;
    cache_entries?: number;
    total_places?: number;
    verified_file?: string;
  }>;
  row_counts: {
    users: { total: number; real: number; test: number };
    communities: { total: number; real: number; test: number };
    projects: { total: number; real: number; test: number };
    events: { total: number; upcoming: number; past: number; cancelled: number };
    opportunities: { total: number; active: number; expired: number; inactive: number };
    places: { total: number };
    posts: { total: number };
    reels: { total: number };
  };
  inactive_and_expired: {
    expired_opportunities: number;
    inactive_opportunities: number;
    cancelled_events: number;
    past_events: number;
    test_entities_total: number;
  };
};

export type DatasetMetadataItem = {
  id: number;
  dataset_name: string;
  version: string;
  source_filename: string;
  total_records: number;
  record_types: string;
  status: string;
  imported_at: string;
  notes?: string | null;
};

export type UserReportItem = {
  id: number;
  reporter_id: number;
  reporter_name: string;
  reported_user_id?: number | null;
  reported_user_name?: string | null;
  target_type?: string;
  post_id?: number | null;
  reel_id?: number | null;
  content_snippet?: string | null;
  reason: string;
  details?: string | null;
  status: string;
  created_at: string;
};

// Next-Gen Features Types
export type AssistantCard = {
  card_type: "user" | "community" | "event" | "place" | "opportunity" | "action_cta";
  id?: number;
  title: string;
  subtitle?: string;
  description?: string;
  location?: string;
  avatar_url?: string | null;
  match_percentage?: number;
  starts_at?: string | null;
  source?: string;
  link: string;
  action_text?: string;
};

export type AssistantResponse = {
  conversation_id: number;
  role: "assistant";
  content: string;
  intent: string;
  action_cards: AssistantCard[];
  suggested_prompts: string[];
  created_at: string;
};

export type AssistantConversationItem = {
  id: number;
  title: string;
  pinned?: boolean;
  archived?: boolean;
  last_message_at?: string;
  created_at: string;
  updated_at?: string | null;
  message_count: number;
};

export type AssistantCitation = {
  title: string;
  url: string;
  snippet: string;
  verified?: boolean;
};

export type AssistantProposedMemory = {
  id: number;
  type: string;
  content: string;
  status: string;
};

export type AssistantMemoryItem = {
  id: number;
  type: string;
  content: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  updated_at?: string | null;
};

export type AssistantSettingsItem = {
  user_id: number;
  memory_enabled: boolean;
  auto_suggest_followups: boolean;
  research_enabled: boolean;
};

export type AssistantSavedRecItem = {
  id: number;
  entity_type: string;
  entity_id: number;
  title: string;
  reason?: string | null;
  feedback?: "useful" | "not_useful" | "dismissed" | null;
  created_at: string;
};

export type AssistantMessageItem = {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  intent?: string | null;
  action_cards: AssistantCard[];
  citations?: AssistantCitation[];
  suggested_followups?: string[];
  created_at: string;
};

export type CompatibilityBreakdown = {
  overall_percentage: number;
  semantic_similarity: number;
  skill_synergy: number;
  shared_goals: number;
  common_interests: number;
  location_proximity: number;
  distance_km?: number | null;
  shared_skills: string[];
  shared_goals_list?: string[];
  explanation: string;
};

export type SmartPeerMatch = {
  user_id: number;
  name: string;
  avatar_url?: string | null;
  bio: string;
  skills: string;
  interests: string;
  goals: string;
  location: string;
  connection_status: string;
  connection_id?: number | null;
  is_connection_sender?: boolean;
  compatibility: CompatibilityBreakdown;
};

export type InterestCircleItem = {
  id: number;
  name: string;
  tagline: string;
  description: string;
  category: string;
  tags: string[];
  max_members: number;
  member_count: number;
  is_private: boolean;
  image_url?: string | null;
  created_by_id?: number | null;
  creator_name: string;
  is_member: boolean;
  is_admin: boolean;
  discussions_count: number;
  activities_count: number;
  created_at: string;
  members?: Array<{
    id: number;
    name: string;
    avatar_url?: string | null;
    skills: string;
    role: string;
    joined_at: string;
  }>;
};

export type CircleDiscussionItem = {
  id: number;
  title: string;
  content: string;
  author_id: number;
  author_name: string;
  author_avatar?: string | null;
  created_at: string;
  replies_count: number;
};

export type InstagramStatus = {
  enabled: boolean;
  connected: boolean;
  user_id?: number;
  instagram_user_id?: string | null;
  username?: string | null;
  account_type?: string | null;
  status: "not_connected" | "connected" | "reconnect_needed";
  media_count: number;
  last_synced_at?: string | null;
  recommendations_enabled: boolean;
  profile_visible: boolean;
  pending_suggested_interests_count: number;
};

export type InstagramMediaItem = {
  id: number;
  instagram_media_id: string;
  media_type: string;
  media_url: string;
  permalink?: string | null;
  caption?: string | null;
  timestamp?: string | null;
  hashtags?: string | null;
};

export type SuggestedInterestItem = {
  id: number;
  interest: string;
  source: string;
  confidence_score: number;
  status: "pending" | "accepted" | "rejected";
  created_at: string;
};

export type CircleReplyItem = {
  id: number;
  content: string;
  author_id: number;
  author_name: string;
  author_avatar?: string | null;
  created_at: string;
};

export type CircleActivityItem = {
  id: number;
  title: string;
  description: string;
  activity_type: string;
  scheduled_at: string;
  location_or_link: string;
  creator_name: string;
  created_at: string;
};

export type GoalMilestoneItem = {
  id: number;
  step_order: number;
  title: string;
  description: string;
  estimated_weeks: number;
  is_completed: boolean;
  completed_at?: string | null;
  resources: string[];
  recommended_communities: Array<{ id: number; name: string; category: string; similarity: number }>;
  recommended_events: Array<{ id: number; title: string; location: string; similarity: number }>;
  recommended_peers: Array<{ id: number; name: string; avatar_url?: string | null; skills: string }>;
};

export type GoalJourneyItem = {
  id: number;
  title: string;
  target_category: string;
  timeframe: string;
  description: string;
  status: string;
  progress_percentage: number;
  total_milestones: number;
  completed_milestones: number;
  created_at: string;
  milestones: GoalMilestoneItem[];
};

export type UserBadgeItem = {
  id: number;
  badge_key: string;
  name: string;
  description: string;
  category: string;
  icon_name: string;
  unlocked_at: string;
};

export type ActivityLogItem = {
  id: number;
  action_type: string;
  xp_awarded: number;
  description: string;
  created_at: string;
};

export type GamificationProfile = {
  user_id: number;
  name: string;
  avatar_url?: string | null;
  xp_points: number;
  current_level: number;
  next_level: number;
  xp_for_next_level: number;
  level_progress_percentage: number;
  current_streak_days: number;
  community_contribution_points: number;
  badges: UserBadgeItem[];
  recent_activities: ActivityLogItem[];
};

export type LeaderboardItem = {
  rank: number;
  user_id: number;
  name: string;
  avatar_url?: string | null;
  level: number;
  xp_points: number;
  streak_days: number;
  badges_count: number;
  is_me: boolean;
};

export type ProjectItem = {
  id: number;
  title: string;
  tagline: string;
  description: string;
  category: string;
  stage: string;
  status: string;
  required_roles: string[];
  skills_needed: string[];
  github_repo_url?: string | null;
  live_demo_url?: string | null;
  creator_id?: number | null;
  creator_name: string;
  creator_avatar?: string | null;
  team_size: number;
  is_owner: boolean;
  is_member: boolean;
  created_at: string;
  discussions_count?: number;
  members: Array<{
    id: number;
    name: string;
    avatar_url?: string | null;
    role: string;
    joined_at: string;
  }>;
  milestones: Array<{
    id: number;
    step_order: number;
    title: string;
    description: string;
    is_completed: boolean;
    completed_at?: string | null;
  }>;
};

export type ProjectDiscussionItem = {
  id: number;
  project_id: number;
  user_id: number;
  author_name: string;
  author_avatar?: string | null;
  title: string;
  content: string;
  created_at: string;
};

export type OpportunityItem = {
  id: number;
  title: string;
  organization: string;
  opportunity_type: string;
  description: string;
  location: string;
  is_remote: boolean;
  deadline?: string | null;
  days_left?: number | null;
  stipend_or_prize?: string | null;
  apply_url: string;
  tags: string[];
  source: string;
  is_bookmarked: boolean;
  bookmarks_count: number;
  created_at: string;
};

export type MapMarkerItem = {
  id: string;
  type: "place" | "event" | "community";
  name: string;
  category: string;
  description: string;
  address: string;
  city: string;
  latitude: number;
  longitude: number;
  distance_km?: number | null;
  link: string;
};

export type SavedItem = {
  id: number;
  item_type: "community" | "event" | "place" | "user" | "post" | "reel";
  item_id: number;
  created_at: string;
  title?: string;
  description?: string;
  category?: string;
  location?: string;
};

export type PostMediaItem = {
  id?: number;
  position: number;
  media_type: string;
  original_url: string;
  feed_url: string;
  thumbnail_url: string;
  width?: number | null;
  height?: number | null;
  alt_text?: string | null;
};

export type Post = {
  id: number;
  author_id: number;
  community_id?: number | null;
  content: string;
  image_url?: string | null;
  visibility?: "public" | "connections_only";
  location_area?: string | null;
  is_pinned?: boolean;
  media?: PostMediaItem[];
  created_at: string;
  author?: {
    id: number;
    name: string;
    email: string;
    avatar_url?: string | null;
  } | null;
  community_name?: string | null;
  likes_count: number;
  is_liked: boolean;
  comments_count?: number;
  score?: number | null;
  score_breakdown?: Record<string, number> | null;
  why_recommended?: string | null;
};

export type PostItem = Post;

export type Message = {
  id: number;
  sender_id: number;
  receiver_id: number;
  content: string;
  is_read: boolean;
  created_at: string;
  sender_name?: string | null;
  receiver_name?: string | null;
};

export type Notification = {
  id: number;
  user_id: number;
  title: string;
  message: string;
  link?: string | null;
  is_read: boolean;
  created_at: string;
};

export type Connection = {
  id: number;
  user_id: number;
  connected_user_id: number;
  status: "pending" | "accepted" | "rejected";
  created_at: string;
  user?: User;
  connected_user?: User;
};

export type AuthResponse = {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user_id: number;
  name: string;
  email: string;
  onboarding_completed?: boolean;
};

function token(): string | null {
  return localStorage.getItem("align_token");
}

let isRefreshing = false;
let refreshSubscribers: ((newToken: string) => void)[] = [];

function onRefreshed(newToken: string) {
  refreshSubscribers.forEach((cb) => cb(newToken));
  refreshSubscribers = [];
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const t = token();
  if (t) {
    headers.set("Authorization", `Bearer ${t}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    if (
      response.status === 401 &&
      !path.startsWith("/auth/login") &&
      !path.startsWith("/auth/refresh") &&
      !path.startsWith("/auth/register")
    ) {
      const refreshToken = localStorage.getItem("align_refresh_token");
      if (refreshToken) {
        if (!isRefreshing) {
          isRefreshing = true;
          try {
            const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ refresh_token: refreshToken }),
            });
            if (refreshRes.ok) {
              const data: AuthResponse = await refreshRes.json();
              localStorage.setItem("align_token", data.access_token);
              if (data.refresh_token) {
                localStorage.setItem("align_refresh_token", data.refresh_token);
              }
              if (data.name) localStorage.setItem("align_user_name", data.name);
              if (data.email) localStorage.setItem("align_user_email", data.email);
              if (data.onboarding_completed !== undefined) {
                localStorage.setItem("align_onboarded", String(data.onboarding_completed));
              }
              isRefreshing = false;
              onRefreshed(data.access_token);

              // Retry original request
              headers.set("Authorization", `Bearer ${data.access_token}`);
              const retryRes = await fetch(`${API_BASE}${path}`, { ...options, headers });
              if (retryRes.ok) {
                if (retryRes.status === 204) return undefined as T;
                return retryRes.json() as Promise<T>;
              }
            }
          } catch {
            isRefreshing = false;
          }
        } else {
          // Wait for the active refresh to finish
          return new Promise<T>((resolve, reject) => {
            refreshSubscribers.push(async (newToken) => {
              try {
                headers.set("Authorization", `Bearer ${newToken}`);
                const retryRes = await fetch(`${API_BASE}${path}`, { ...options, headers });
                if (retryRes.ok) {
                  if (retryRes.status === 204) resolve(undefined as T);
                  else resolve((await retryRes.json()) as T);
                } else {
                  reject(new Error(`Retry failed with status ${retryRes.status}`));
                }
              } catch (err) {
                reject(err);
              }
            });
          });
        }
      }

      // Refresh failed or no refresh token
      localStorage.removeItem("align_token");
      localStorage.removeItem("align_refresh_token");
      localStorage.removeItem("align_user_name");
      localStorage.removeItem("align_user_email");
      localStorage.removeItem("align_onboarded");
      window.dispatchEvent(new Event("align-auth-expired"));
    }
    const data = await response.json().catch(() => ({}));
    const errorMessage = formatApiError(data) || `Request failed with status ${response.status}`;
    throw new Error(errorMessage);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  // Auth
  register: (payload: { name: string; email: string; password: string }) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),

  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>(
      "/auth/login",
      { method: "POST", body: JSON.stringify(payload) }
    ),

  googleAuth: (credential: string) =>
    request<AuthResponse>(
      "/auth/google",
      { method: "POST", body: JSON.stringify({ credential }) }
    ),

  logout: async () => {
    const refreshToken = localStorage.getItem("align_refresh_token");
    try {
      if (refreshToken) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      }
    } catch {
      // Best-effort logout
    } finally {
      localStorage.removeItem("align_token");
      localStorage.removeItem("align_refresh_token");
      localStorage.removeItem("align_user_name");
      localStorage.removeItem("align_user_email");
      localStorage.removeItem("align_onboarded");
      window.dispatchEvent(new Event("align-auth-expired"));
    }
  },

  forgotPassword: (email: string) =>
    request<{ status: string; message: string; dev_token?: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  resetPassword: (payload: { token: string; new_password: string }) =>
    request<{ status: string; message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  sendVerification: () =>
    request<{ status: string; message: string; dev_token?: string }>("/auth/send-verification", {
      method: "POST",
    }),

  verifyEmail: (token: string) =>
    request<{ status: string; message: string }>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  me: () => request<User>("/auth/me"),

  updateProfile: (payload: Partial<Profile>) =>
    request<Profile>("/auth/profile", { method: "PUT", body: JSON.stringify(payload) }),

  syncGithubSkills: (github_username: string) =>
    request<Profile>("/users/me/sync-github", {
      method: "POST",
      body: JSON.stringify({ github_username }),
    }),

  checkUsername: (username: string) =>
    request<{ available: boolean; username: string; message: string }>(
      `/users/check-username?username=${encodeURIComponent(username)}`
    ),

  completeOnboarding: (payload: {
    username?: string;
    name?: string;
    avatar_url?: string;
    age_cohort?: string;
    gender?: string;
    preferred_language?: string;
    step?: number;
    bio?: string;
    interests?: string | string[];
    skills?: string | string[];
    hobbies?: string | string[];
    skill_proficiency?: string;
    hobby_engagement_level?: string;
    goals?: string | string[];
    preferred_activities?: string | string[];
    preferred_community_types?: string | string[];
    location?: string;
    privacy_level?: string;
  }) => request<Profile>("/auth/onboarding", { method: "POST", body: JSON.stringify(payload) }),

  // Communities
  communities: (params?: string | { q?: string; category?: string; limit?: number }, cat = "") => {
    let q = "";
    let category = cat;
    let limit = 24;
    if (typeof params === "string") {
      q = params;
    } else if (params && typeof params === "object") {
      q = params.q || "";
      category = params.category || "";
      limit = params.limit || 24;
    }
    return request<Community[]>(
      `/communities?limit=${limit}&q=${encodeURIComponent(q)}${category ? `&category=${encodeURIComponent(category)}` : ""}`
    );
  },

  createCommunity: (payload: {
    name: string;
    description: string;
    category: string;
    tags: string;
    location: string;
  }) => request<Community>("/communities", { method: "POST", body: JSON.stringify(payload) }),

  getCommunity: (id: number) => request<Community>(`/communities/${id}`),

  joinCommunity: (id: number) => request<{ status: string; message: string }>(`/communities/${id}/join`, { method: "POST" }),

  leaveCommunity: (id: number) => request<{ status: string; message: string }>(`/communities/${id}/leave`, { method: "POST" }),

  communityPosts: (id: number) => request<Post[]>(`/communities/${id}/posts`),

  // Events
  events: (
    params?: string | { q?: string; upcoming_only?: boolean; category?: string; limit?: number },
    upcoming = true,
    cat = ""
  ) => {
    let q = "";
    let upcoming_only = upcoming;
    let category = cat;
    let limit = 24;
    if (typeof params === "string") {
      q = params;
    } else if (params && typeof params === "object") {
      q = params.q || "";
      upcoming_only = params.upcoming_only !== undefined ? params.upcoming_only : true;
      category = params.category || "";
      limit = params.limit || 24;
    }
    return request<EventItem[]>(
      `/events?limit=${limit}&upcoming_only=${upcoming_only}&q=${encodeURIComponent(q)}${category ? `&category=${encodeURIComponent(category)}` : ""}`
    );
  },

  createEvent: (payload: {
    title: string;
    description: string;
    category: string;
    location: string;
    starts_at?: string;
    capacity?: number;
  }) => request<EventItem>("/events", { method: "POST", body: JSON.stringify(payload) }),

  getEvent: (id: number) => request<EventItem>(`/events/${id}`),

  registerEvent: (
    id: number,
    payload?: { name?: string; email?: string; phone?: string; ticket_count?: number; notes?: string }
  ) =>
    request<RegistrationResult>(`/events/${id}/register`, {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }),

  cancelEvent: (id: number, email?: string) =>
    request<{ status: string; message: string }>(
      `/events/${id}/cancel${email ? `?email=${encodeURIComponent(email)}` : ""}`,
      { method: "POST" }
    ),

  cancelEventRegistration: (id: number, email?: string) =>
    request<{ status: string; message: string }>(
      `/events/${id}/cancel${email ? `?email=${encodeURIComponent(email)}` : ""}`,
      { method: "POST" }
    ),

  purgeDummyEvents: () =>
    request<{ status: string; purged: number; message: string }>("/events/purge-dummy", { method: "POST" }),

  syncEventbrite: (q = "tech", location = "") =>
    request<{ status: string; synced: number; message: string }>(
      `/events/sync/eventbrite?q=${encodeURIComponent(q)}&location=${encodeURIComponent(location)}`,
      { method: "POST" }
    ),

  // Places
  places: (city = "") => request<PlaceItem[]>(`/places?limit=24${city ? `&city=${encodeURIComponent(city)}` : ""}`),

  // Discovery & Recommendations
  search: (query: string, user_lat?: number, user_lon?: number, category?: string) =>
    request<DiscoveryResult[]>("/discovery/search", {
      method: "POST",
      body: JSON.stringify({ query, limit: 16, user_lat, user_lon, category }),
    }),

  recommendations: (limit = 12) => request<DiscoveryResult[]>(`/discovery/recommendations?limit=${limit}`),

  submitRecommendationFeedback: (
    item_type: "community" | "event" | "place" | "user" | "project" | "opportunity",
    item_id: number,
    feedback: RecommendationFeedbackType,
    notes?: string
  ) =>
    request<RecommendationFeedbackItem>("/discovery/feedback", {
      method: "POST",
      body: JSON.stringify({ item_type, item_id, feedback, notes }),
    }),

  getRecommendationFeedbacks: (item_type?: string) =>
    request<RecommendationFeedbackItem[]>(
      `/discovery/feedback${item_type ? `?item_type=${encodeURIComponent(item_type)}` : ""}`
    ),

  // Saved Items
  saved: () => request<SavedItem[]>("/saved"),

  saveItem: (
    item_type: "community" | "event" | "place" | "user" | "post" | "reel",
    item_id: number
  ) => request<SavedItem>("/saved", { method: "POST", body: JSON.stringify({ item_type, item_id }) }),

  unsaveItem: (item_type: string, item_id: number) =>
    request<{ status: string; message: string }>(`/saved/${item_type}/${item_id}`, { method: "DELETE" }),

  // Social Feed
  feed: (params?: number | { community_id?: number; author_id?: number; limit?: number }) => {
    if (typeof params === "number") {
      return request<Post[]>(`/feed?community_id=${params}`);
    }
    const q = new URLSearchParams();
    if (params?.community_id) q.set("community_id", String(params.community_id));
    if (params?.author_id) q.set("author_id", String(params.author_id));
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<Post[]>(`/feed${qs ? `?${qs}` : ""}`);
  },

  createPost: (payload: {
    content: string;
    community_id?: number;
    image_url?: string;
    visibility?: "public" | "connections_only";
    location_area?: string;
    media_items?: Array<{
      position: number;
      media_type: string;
      original_url: string;
      feed_url: string;
      thumbnail_url: string;
      width?: number;
      height?: number;
      alt_text?: string;
    }>;
  }) =>
    request<Post>("/feed", { method: "POST", body: JSON.stringify(payload) }),

  uploadImageVariant: async (file: File, altText?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (altText) {
      formData.append("alt_text", altText);
    }
    const token = localStorage.getItem("align_token");
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetch(`${API_BASE}/uploads/image`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Image upload failed");
    }
    return res.json() as Promise<{
      status: string;
      original_url: string;
      feed_url: string;
      thumbnail_url: string;
      width: number;
      height: number;
      alt_text?: string;
      media_type: string;
    }>;
  },

  uploadVideoVariant: async (
    file: File,
    isReel: boolean = true,
    onProgress?: (percent: number) => void,
    signal?: AbortSignal
  ) => {
    return new Promise<{
      status: string;
      video_url: string;
      thumbnail_url: string;
      duration_seconds: number;
      width: number;
      height: number;
      is_vertical: boolean;
    }>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/uploads/video`);

      const token = localStorage.getItem("align_token");
      if (token) {
        xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      }

      if (signal) {
        if (signal.aborted) {
          reject(new DOMException("Upload aborted by user", "AbortError"));
          return;
        }
        signal.addEventListener("abort", () => {
          xhr.abort();
          reject(new DOMException("Upload aborted by user", "AbortError"));
        });
      }

      if (onProgress && xhr.upload) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const pct = Math.round((event.loaded / event.total) * 100);
            onProgress(pct);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            reject(new Error("Invalid response from upload server"));
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || "Video upload failed"));
          } catch {
            reject(new Error(`Video upload failed with status ${xhr.status}`));
          }
        }
      };

      xhr.onerror = () => reject(new Error("Network error during video upload"));
      xhr.onabort = () => reject(new DOMException("Upload aborted by user", "AbortError"));

      const formData = new FormData();
      formData.append("file", file);
      formData.append("is_reel", String(isReel));
      xhr.send(formData);
    });
  },

  uploadMedia: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const token = localStorage.getItem("align_token");
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetch(`${API_BASE}/uploads`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    return (await res.json()) as {
      status: string;
      url: string;
      filename: string;
      media_type: "image" | "video";
      size_bytes: number;
    };
  },

  toggleLike: (postId: number) =>
    request<{ status: string; is_liked: boolean; likes_count: number }>(`/feed/${postId}/like`, {
      method: "POST",
    }),

  likePost: (postId: number) =>
    request<{ status: string; is_liked: boolean; likes_count: number }>(`/feed/${postId}/like`, {
      method: "POST",
    }),

  togglePinPost: (postId: number) =>
    request<{ status: string; post_id: number; is_pinned: boolean; message: string }>(
      `/feed/${postId}/pin`,
      { method: "POST" }
    ),

  sharePostToDM: (postId: number, recipientId: number, note?: string) =>
    request<{ status: string; post_id: number; message_id: number; recipient_id: number }>(
      `/feed/${postId}/share`,
      {
        method: "POST",
        body: JSON.stringify({ recipient_id: recipientId, note }),
      }
    ),

  getComments: (postId: number) =>
    request<
      Array<{
        id: number;
        post_id: number;
        author_id: number;
        content: string;
        parent_id?: number | null;
        created_at: string;
        author_name: string;
        author_avatar?: string | null;
        replies: Array<{
          id: number;
          post_id: number;
          author_id: number;
          content: string;
          parent_id?: number | null;
          created_at: string;
          author_name: string;
          author_avatar?: string | null;
        }>;
      }>
    >(`/feed/${postId}/comments`),

  addComment: (postId: number, content: string, parentId?: number) =>
    request<{
      id: number;
      post_id: number;
      author_id: number;
      content: string;
      parent_id?: number | null;
      created_at: string;
      author_name: string;
      author_avatar?: string | null;
      replies: any[];
    }>(`/feed/${postId}/comments`, { method: "POST", body: JSON.stringify({ content, parent_id: parentId }) }),

  editPost: (postId: number, payload: { content: string; visibility?: string }) =>
    request<Post>(`/feed/${postId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deletePost: (postId: number) =>
    request<{ status: string; message: string }>(`/feed/${postId}`, {
      method: "DELETE",
    }),

  // Reels
  reels: (category = "") =>
    request<
      Array<{
        id: number;
        title: string;
        author_id?: number;
        author_name: string;
        author_avatar?: string | null;
        category: string;
        video_url: string;
        thumbnail_url: string;
        views_count: string;
        likes_count: number;
        comments_count: number;
        duration_seconds?: number | null;
        visibility?: "public" | "connections_only";
        audio_track?: string | null;
        caption?: string | null;
        tags: string[];
        is_liked: boolean;
        created_at?: string | null;
      }>
    >(`/reels${category && category !== "All" ? `?category=${encodeURIComponent(category)}` : ""}`),

  toggleReelLike: (reelId: number) =>
    request<{ status: string; reel_id: number; is_liked: boolean; likes_count: number }>(`/reels/${reelId}/like`, {
      method: "POST",
    }),

  recordReelView: (reelId: number) =>
    request<{ status: string; reel_id: number; views_count: number; formatted_views: string }>(
      `/reels/${reelId}/view`,
      { method: "POST" }
    ),

  shareReelToDM: (reelId: number, recipientId: number, note?: string) =>
    request<{ status: string; reel_id: number; message_id: number; recipient_id: number }>(
      `/reels/${reelId}/share`,
      {
        method: "POST",
        body: JSON.stringify({ recipient_id: recipientId, note }),
      }
    ),

  getReelComments: (reelId: number) =>
    request<
      Array<{
        id: number;
        reel_id: number;
        user_id: number;
        user_name: string;
        user_avatar?: string | null;
        content: string;
        parent_id?: number | null;
        created_at: string;
        replies: Array<{
          id: number;
          reel_id: number;
          user_id: number;
          user_name: string;
          user_avatar?: string | null;
          content: string;
          parent_id?: number | null;
          created_at: string;
        }>;
      }>
    >(`/reels/${reelId}/comments`),

  addReelComment: (reelId: number, content: string, parentId?: number) =>
    request<{
      id: number;
      reel_id: number;
      user_id: number;
      user_name: string;
      user_avatar?: string | null;
      content: string;
      parent_id?: number | null;
      created_at: string;
      replies: any[];
    }>(`/reels/${reelId}/comments`, {
      method: "POST",
      body: JSON.stringify({ content, parent_id: parentId }),
    }),

  createReel: (payload: {
    title: string;
    category: string;
    video_url: string;
    thumbnail_url: string;
    duration_seconds?: number;
    visibility?: "public" | "connections_only";
    audio_track?: string;
    caption?: string;
    tags?: string[];
  }) => request<any>("/reels", { method: "POST", body: JSON.stringify(payload) }),

  editReel: (reelId: number, caption: string) =>
    request<any>(`/reels/${reelId}`, {
      method: "PUT",
      body: JSON.stringify({ caption }),
    }),

  deleteReel: (reelId: number) =>
    request<{ status: string; message: string }>(`/reels/${reelId}`, {
      method: "DELETE",
    }),

  // Messages
  conversations: () =>
    request<
      Array<{
        partner_id: number;
        partner_name: string;
        partner_avatar?: string | null;
        last_message: string;
        last_message_at: string;
        unread_count: number;
      }>
    >("/messages/conversations"),

  messages: (other_user_id?: number) =>
    request<Message[]>(`/messages${other_user_id ? `?other_user_id=${other_user_id}` : ""}`),

  sendMessage: (payload: { receiver_id: number; content: string }) =>
    request<Message>("/messages", { method: "POST", body: JSON.stringify(payload) }),

  // Notifications
  notifications: () => request<Notification[]>("/notifications"),

  markNotificationRead: (id: number) =>
    request<{ status: string; message: string }>(`/notifications/${id}/read`, { method: "PUT" }),

  // People & Users
  users: (q = "", page = 1, limit = 24, meaningful_only = false) =>
    request<User[]>(
      `/users?page=${page}&limit=${limit}&meaningful_only=${meaningful_only}${q ? `&q=${encodeURIComponent(q)}` : ""}`
    ),

  getUserProfile: (userId: number) => request<User>(`/users/${userId}`),

  getUserByUsername: (username: string) =>
    request<User>(`/users/handle/${encodeURIComponent(username)}`),

  // Connections
  connectUser: (target_user_id: number) =>
    request<{ status: string; message: string; connection_id: number; connection_status: string }>(
      `/users/${target_user_id}/connect`,
      { method: "POST" }
    ),

  acceptConnection: (connection_id: number) =>
    request<{ status: string; message: string }>(`/users/connections/${connection_id}/accept`, {
      method: "POST",
    }),

  rejectConnection: (connection_id: number) =>
    request<{ status: string; message: string }>(`/users/connections/${connection_id}/reject`, {
      method: "POST",
    }),

  disconnectUser: (target_user_id: number) =>
    request<{ status: string; message: string }>(`/users/${target_user_id}/disconnect`, {
      method: "POST",
    }),

  logoutAll: () =>
    request<{ status: string; message: string }>("/auth/logout-all", {
      method: "POST",
    }),

  changePassword: (payload: { old_password: string; new_password: string }) =>
    request<{ status: string; message: string }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteAccount: () =>
    request<{ status: string; message: string }>("/users/me", {
      method: "DELETE",
    }),

  exportUserData: () =>
    request<Record<string, any>>("/users/me/export"),

  myConnections: (status_filter?: string) =>
    request<
      Array<{
        connection_id: number;
        status: string;
        created_at: string;
        is_sender: boolean;
        partner_id: number;
        partner_name: string;
        partner_avatar?: string | null;
        partner_skills: string;
        partner_location: string;
      }>
    >(`/users/me/connections${status_filter ? `?status_filter=${status_filter}` : ""}`),

  connectionStatus: (target_user_id: number) =>
    request<{ status: string; is_sender: boolean; connection_id?: number | null }>(
      `/users/${target_user_id}/connection-status`
    ),

  // Skills & Hobbies Dataset
  skills: (params?: { category?: string; q?: string; page?: number; limit?: number }) => {
    const p = new URLSearchParams();
    if (params?.category) p.append("category", params.category);
    if (params?.q) p.append("q", params.q);
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const qs = p.toString();
    return request<SkillMaster[]>(`/skills${qs ? `?${qs}` : ""}`);
  },

  skillCategories: () => request<CategorySummary[]>("/skills/categories"),

  searchSkills: (params?: {
    q?: string;
    category?: string;
    context?: string;
    proficiency?: string;
    setting?: string;
    min_popularity?: number;
    page?: number;
    limit?: number;
  }) => {
    const p = new URLSearchParams();
    if (params?.q) p.append("q", params.q);
    if (params?.category) p.append("category", params.category);
    if (params?.context) p.append("context", params.context);
    if (params?.proficiency) p.append("proficiency", params.proficiency);
    if (params?.setting) p.append("setting", params.setting);
    if (params?.min_popularity) p.append("min_popularity", String(params.min_popularity));
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const qs = p.toString();
    return request<SkillHobbyDatasetItem[]>(`/skills/search${qs ? `?${qs}` : ""}`);
  },

  hobbies: (params?: { category?: string; q?: string; page?: number; limit?: number }) => {
    const p = new URLSearchParams();
    if (params?.category) p.append("category", params.category);
    if (params?.q) p.append("q", params.q);
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const qs = p.toString();
    return request<HobbyMaster[]>(`/hobbies${qs ? `?${qs}` : ""}`);
  },

  hobbyCategories: () => request<CategorySummary[]>("/hobbies/categories"),

  searchHobbies: (params?: {
    q?: string;
    category?: string;
    context?: string;
    engagement?: string;
    setting?: string;
    frequency?: string;
    motivation?: string;
    min_popularity?: number;
    page?: number;
    limit?: number;
  }) => {
    const p = new URLSearchParams();
    if (params?.q) p.append("q", params.q);
    if (params?.category) p.append("category", params.category);
    if (params?.context) p.append("context", params.context);
    if (params?.engagement) p.append("engagement", params.engagement);
    if (params?.setting) p.append("setting", params.setting);
    if (params?.frequency) p.append("frequency", params.frequency);
    if (params?.motivation) p.append("motivation", params.motivation);
    if (params?.min_popularity) p.append("min_popularity", String(params.min_popularity));
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const qs = p.toString();
    return request<SkillHobbyDatasetItem[]>(`/hobbies/search${qs ? `?${qs}` : ""}`);
  },

  datasetStats: () => request<DatasetStats>("/dataset/stats"),
  datasetFacets: () => request<DatasetFacets>("/dataset/facets"),

  // Goals & Interests API methods
  goals: (params?: { category?: string; q?: string; page?: number; limit?: number }) => {
    const p = new URLSearchParams();
    if (params?.category) p.append("category", params.category);
    if (params?.q) p.append("q", params.q);
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const qs = p.toString();
    return request<GoalMaster[]>(`/goals${qs ? `?${qs}` : ""}`);
  },

  goalCategories: () => request<CategorySummary[]>("/goals/categories"),

  searchGoals: (params?: {
    q?: string;
    category?: string;
    life_context?: string;
    timeline?: string;
    priority?: string;
    motivation?: string;
    min_popularity?: number;
    page?: number;
    limit?: number;
  }) => {
    const p = new URLSearchParams();
    if (params?.q) p.append("q", params.q);
    if (params?.category) p.append("category", params.category);
    if (params?.life_context) p.append("life_context", params.life_context);
    if (params?.timeline) p.append("timeline", params.timeline);
    if (params?.priority) p.append("priority", params.priority);
    if (params?.motivation) p.append("motivation", params.motivation);
    if (params?.min_popularity) p.append("min_popularity", String(params.min_popularity));
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const qs = p.toString();
    return request<GoalInterestDatasetItem[]>(`/goals/search${qs ? `?${qs}` : ""}`);
  },

  interests: (params?: { category?: string; q?: string; page?: number; limit?: number }) => {
    const p = new URLSearchParams();
    if (params?.category) p.append("category", params.category);
    if (params?.q) p.append("q", params.q);
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const qs = p.toString();
    return request<InterestMaster[]>(`/interests${qs ? `?${qs}` : ""}`);
  },

  interestCategories: () => request<CategorySummary[]>("/interests/categories"),

  searchInterests: (params?: {
    q?: string;
    category?: string;
    life_context?: string;
    timeline?: string;
    setting?: string;
    frequency?: string;
    motivation?: string;
    min_popularity?: number;
    page?: number;
    limit?: number;
  }) => {
    const p = new URLSearchParams();
    if (params?.q) p.append("q", params.q);
    if (params?.category) p.append("category", params.category);
    if (params?.life_context) p.append("life_context", params.life_context);
    if (params?.timeline) p.append("timeline", params.timeline);
    if (params?.setting) p.append("setting", params.setting);
    if (params?.frequency) p.append("frequency", params.frequency);
    if (params?.motivation) p.append("motivation", params.motivation);
    if (params?.min_popularity) p.append("min_popularity", String(params.min_popularity));
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const qs = p.toString();
    return request<GoalInterestDatasetItem[]>(`/interests/search${qs ? `?${qs}` : ""}`);
  },

  goalsInterestsStats: () => request<GoalsInterestsStats>("/goals-interests/stats"),
  goalsInterestsFacets: () => request<GoalsInterestsFacets>("/goals-interests/facets"),

  // Admin & Data Synchronization
  adminStats: () => request<AdminStats>("/admin/stats"),
  adminDataHealth: () => request<DataHealthResponse>("/admin/data-health"),
  adminDatasets: () => request<DatasetMetadataItem[]>("/admin/datasets"),
  adminSyncEvents: (query = "tech", location = "") =>
    request<{ status: string; synced: number; message: string }>(
      `/admin/sync/events?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`,
      { method: "POST" }
    ),
  adminSyncPlaces: (city = "Pune") =>
    request<{ status: string; synced: number; message: string }>(
      `/admin/sync/places?city=${encodeURIComponent(city)}`,
      { method: "POST" }
    ),
  adminReports: (status = "pending") =>
    request<UserReportItem[]>(`/admin/reports?status_filter=${encodeURIComponent(status)}`),
  adminResolveReport: (reportId: number, action = "resolved") =>
    request<{ status: string; message: string }>(
      `/admin/reports/${reportId}/resolve?action=${encodeURIComponent(action)}`,
      { method: "POST" }
    ),
  adminModerationAction: (
    reportId: number,
    action: "remove_content" | "warn_user" | "suspend_user" | "dismiss_report",
    note?: string
  ) =>
    request<{ status: string; message: string; action: string }>(
      `/admin/reports/${reportId}/action`,
      {
        method: "POST",
        body: JSON.stringify({ action, note }),
      }
    ),
  createReport: (data: {
    target_type: "post" | "reel" | "user" | "comment";
    target_id: number;
    reason: string;
    details?: string;
  }) =>
    request<{ status: string; message: string; report_id: number }>(
      "/reports",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),

  // Feature 1: AI Personal Assistant
  assistantChat: (message: string, conversation_id?: number) =>
    request<AssistantResponse>("/assistant/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id }),
    }),
  assistantConversations: (filter_type = "active", search = "", limit = 30) => {
    const p = new URLSearchParams();
    if (filter_type) p.append("filter_type", filter_type);
    if (search) p.append("search", search);
    p.append("limit", String(limit));
    return request<AssistantConversationItem[]>(`/assistant/conversations?${p.toString()}`);
  },
  createAssistantConversation: (title = "New Discovery Session") =>
    request<AssistantConversationItem>("/assistant/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  updateAssistantConversation: (
    convId: number,
    payload: { title?: string; pinned?: boolean; archived?: boolean }
  ) =>
    request<AssistantConversationItem>(`/assistant/conversations/${convId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteAssistantConversation: (convId: number) =>
    request<{ status: string; message: string }>(`/assistant/conversations/${convId}`, {
      method: "DELETE",
    }),
  assistantHistory: (convId: number) =>
    request<AssistantMessageItem[]>(`/assistant/conversations/${convId}/messages`),
  regenerateAssistantTurn: async (
    convId: number,
    onEvent: (event: string, data: any) => void,
    signal?: AbortSignal
  ) => {
    const token = localStorage.getItem("align_token");
    const res = await fetch(`${API_BASE}/assistant/chat/regenerate?conv_id=${convId}`, {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      signal,
    });
    if (!res.ok) throw new Error(`Regenerate failed with status ${res.status}`);
    const reader = res.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";
      for (const block of blocks) {
        if (!block.trim()) continue;
        let eventName = "message";
        let dataStr = "";
        for (const line of block.split("\n")) {
          if (line.startsWith("event: ")) eventName = line.replace("event: ", "").trim();
          else if (line.startsWith("data: ")) dataStr = line.replace("data: ", "").trim();
        }
        if (dataStr) {
          try {
            onEvent(eventName, JSON.parse(dataStr));
          } catch {
            onEvent(eventName, dataStr);
          }
        }
      }
    }
  },
  assistantChatStream: async (
    message: string,
    conversationId: number | undefined,
    onEvent: (event: string, data: any) => void,
    signal?: AbortSignal
  ) => {
    const token = localStorage.getItem("align_token");
    const res = await fetch(`${API_BASE}/assistant/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, conversation_id: conversationId }),
      signal,
    });
    if (!res.ok) {
      throw new Error(`Chat stream failed with status ${res.status}`);
    }
    const reader = res.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";
      for (const block of blocks) {
        if (!block.trim()) continue;
        let eventName = "message";
        let dataStr = "";
        for (const line of block.split("\n")) {
          if (line.startsWith("event: ")) eventName = line.replace("event: ", "").trim();
          else if (line.startsWith("data: ")) dataStr = line.replace("data: ", "").trim();
        }
        if (dataStr) {
          try {
            onEvent(eventName, JSON.parse(dataStr));
          } catch {
            onEvent(eventName, dataStr);
          }
        }
      }
    }
  },
  assistantMemories: (status = "all") => {
    const p = new URLSearchParams();
    if (status) p.append("status_filter", status);
    return request<AssistantMemoryItem[]>(`/assistant/memories?${p.toString()}`);
  },
  updateAssistantMemory: (id: number, payload: { content?: string; status?: "approved" | "rejected" | "pending" }) =>
    request<AssistantMemoryItem>(`/assistant/memories/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteAssistantMemory: (id: number) =>
    request<{ status: string; message: string }>(`/assistant/memories/${id}`, { method: "DELETE" }),
  clearAllAssistantMemories: () =>
    request<{ status: string; message: string }>("/assistant/memories", { method: "DELETE" }),
  assistantSettings: () => request<AssistantSettingsItem>("/assistant/settings"),
  updateAssistantSettings: (payload: Partial<AssistantSettingsItem>) =>
    request<AssistantSettingsItem>("/assistant/settings", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  assistantSavedRecommendations: () =>
    request<AssistantSavedRecItem[]>("/assistant/recommendations"),
  saveAssistantRecommendation: (payload: {
    entity_type: string;
    entity_id: number;
    title: string;
    reason?: string;
  }) =>
    request<{ status: string; id: number; title: string }>("/assistant/recommendations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  feedbackAssistantRecommendation: (id: number, feedback: "useful" | "not_useful" | "dismissed") =>
    request<{ status: string; id: number; feedback: string }>(
      `/assistant/recommendations/${id}/feedback`,
      { method: "POST", body: JSON.stringify({ feedback }) }
    ),

  // Feature 2: Smart People Matching
  smartPeerMatches: (minScore = 30, limit = 15) =>
    request<{ user_id: number; total_matched: number; results: SmartPeerMatch[] }>(
      `/matching/peers?min_score=${minScore}&limit=${limit}`
    ),

  // Feature 3: Interest Circles
  circles: (q = "", category = "") =>
    request<InterestCircleItem[]>(
      `/circles?limit=30${q ? `&q=${encodeURIComponent(q)}` : ""}${category ? `&category=${encodeURIComponent(category)}` : ""}`
    ),
  createCircle: (payload: {
    name: string;
    tagline?: string;
    description: string;
    category?: string;
    tags?: string;
    max_members?: number;
    is_private?: boolean;
    image_url?: string;
  }) => request<InterestCircleItem>("/circles", { method: "POST", body: JSON.stringify(payload) }),
  circleDetails: (id: number) => request<InterestCircleItem>(`/circles/${id}`),
  joinCircle: (id: number) =>
    request<{ status: string; message: string }>(`/circles/${id}/join`, { method: "POST" }),
  leaveCircle: (id: number) =>
    request<{ status: string; message: string }>(`/circles/${id}/leave`, { method: "POST" }),
  circleDiscussions: (id: number) => request<CircleDiscussionItem[]>(`/circles/${id}/discussions`),
  createCircleDiscussion: (id: number, payload: { title: string; content: string }) =>
    request<CircleDiscussionItem>(`/circles/${id}/discussions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  circleReplies: (circleId: number, discId: number) =>
    request<CircleReplyItem[]>(`/circles/${circleId}/discussions/${discId}/replies`),
  postCircleReply: (circleId: number, discId: number, content: string) =>
    request<CircleReplyItem>(`/circles/${circleId}/discussions/${discId}/replies`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  circleActivities: (circleId: number) =>
    request<CircleActivityItem[]>(`/circles/${circleId}/activities`),
  scheduleCircleActivity: (
    circleId: number,
    payload: { title: string; description?: string; activity_type?: string; scheduled_at: string; location_or_link?: string }
  ) =>
    request<{ id: number; title: string; scheduled_at: string }>(`/circles/${circleId}/activities`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Feature 4: AI Goal Journey
  generateGoalJourney: (payload: { title: string; timeframe?: string; category?: string }) =>
    request<GoalJourneyItem>("/goals/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  myGoalJourneys: () => request<GoalJourneyItem[]>("/goals/my"),
  goalJourneyDetails: (id: number) => request<GoalJourneyItem>(`/goals/${id}`),
  toggleGoalMilestone: (journeyId: number, milestoneId: number) =>
    request<{
      milestone_id: number;
      is_completed: boolean;
      journey_progress: number;
      journey_status: string;
      gamification?: any;
    }>(`/goals/${journeyId}/milestones/${milestoneId}`, { method: "PATCH" }),
  deleteGoalJourney: (id: number) =>
    request<{ status: string; message: string }>(`/goals/${id}`, { method: "DELETE" }),

  // Feature 5: Discovery Map Markers
  mapMarkers: (user_lat?: number, user_lon?: number, radius_km = 35, query?: string) => {
    const p = new URLSearchParams();
    if (user_lat !== undefined) p.append("user_lat", String(user_lat));
    if (user_lon !== undefined) p.append("user_lon", String(user_lon));
    p.append("radius_km", String(radius_km));
    if (query) p.append("query", query);
    return request<MapMarkerItem[]>(`/places/map/markers?${p.toString()}`);
  },

  // Feature 6: Gamification
  myGamification: () => request<GamificationProfile>("/gamification/me"),
  gamificationLeaderboard: (limit = 10) =>
    request<LeaderboardItem[]>(`/gamification/leaderboard?limit=${limit}`),

  // Feature 7: Project Collaboration
  projects: (q = "", category = "", stage = "") =>
    request<ProjectItem[]>(
      `/projects?limit=30${q ? `&q=${encodeURIComponent(q)}` : ""}${category ? `&category=${encodeURIComponent(category)}` : ""}${stage ? `&stage=${encodeURIComponent(stage)}` : ""}`
    ),
  githubGoodFirstIssues: (query = "python", limit = 8) =>
    request<
      Array<{
        id: number;
        title: string;
        html_url: string;
        repository: string;
        comments_count: number;
        labels: string[];
        created_at: string;
        state: string;
      }>
    >(`/projects/github/good-first-issues?query=${encodeURIComponent(query)}&limit=${limit}`),
  createProject: (payload: {
    title: string;
    tagline?: string;
    description: string;
    category?: string;
    stage?: string;
    required_roles?: string;
    skills_needed?: string;
    github_repo_url?: string;
    live_demo_url?: string;
  }) => request<ProjectItem>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  projectDetails: (id: number) => request<ProjectItem>(`/projects/${id}`),
  applyToProject: (id: number, payload: { desired_role: string; pitch_message: string }) =>
    request<{ status: string; message: string }>(`/projects/${id}/apply`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  projectApplications: (id: number) =>
    request<
      Array<{
        id: number;
        applicant_id: number;
        applicant_name: string;
        applicant_avatar?: string | null;
        applicant_skills: string;
        desired_role: string;
        pitch_message: string;
        status: string;
        created_at: string;
      }>
    >(`/projects/${id}/applications`),
  reviewProjectApplication: (projectId: number, appId: number, action = "accepted") =>
    request<{ status: string; message: string }>(
      `/projects/${projectId}/applications/${appId}/review?action=${encodeURIComponent(action)}`,
      { method: "POST" }
    ),
  addProjectMilestone: (projectId: number, payload: { title: string; description?: string; step_order?: number }) =>
    request<{ id: number; title: string; is_completed: boolean }>(`/projects/${projectId}/milestones`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateProjectMilestone: (projectId: number, milestoneId: number, payload: { is_completed?: boolean; title?: string; description?: string; step_order?: number }) =>
    request<{ id: number; title: string; is_completed: boolean; completed_at?: string | null }>(
      `/projects/${projectId}/milestones/${milestoneId}`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      }
    ),
  updateProject: (projectId: number, payload: Partial<ProjectItem>) =>
    request<ProjectItem>(`/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  projectDiscussions: (projectId: number) =>
    request<ProjectDiscussionItem[]>(`/projects/${projectId}/discussions`),
  createProjectDiscussion: (projectId: number, payload: { title?: string; content: string }) =>
    request<ProjectDiscussionItem>(`/projects/${projectId}/discussions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  removeProjectMember: (projectId: number, memberUserId: number) =>
    request<{ status: string; message: string }>(`/projects/${projectId}/members/${memberUserId}`, {
      method: "DELETE",
    }),

  // Messaging & Notifications
  unreadMessagesCount: () => request<{ unread_count: number }>("/messages/unread/count"),
  markMessageRead: (messageId: number) =>
    request<{ status: string; message: string }>(`/messages/${messageId}/read`, { method: "PATCH" }),
  markConversationRead: (otherUserId: number) =>
    request<{ status: string; marked_read_count: number }>(`/messages/${otherUserId}/read`, { method: "POST" }),
  unreadNotificationsCount: () => request<{ unread_count: number }>("/notifications/unread/count"),
  markAllNotificationsRead: () => request<{ status: string; marked_read_count: number }>("/notifications/read-all", { method: "POST" }),
  deleteNotification: (id: number) => request<{ status: string; message: string }>(`/notifications/${id}`, { method: "DELETE" }),

  // Gamification History
  gamificationHistory: (limit = 30, offset = 0) =>
    request<{
      user_id: number;
      total_xp: number;
      current_level: number;
      total_transactions: number;
      items: ActivityLogItem[];
    }>(`/gamification/history?limit=${limit}&offset=${offset}`),

  // Feature 8: Opportunity Discovery
  opportunities: (q = "", type = "", is_remote?: boolean) => {
    const p = new URLSearchParams();
    if (q) p.append("q", q);
    if (type) p.append("type", type);
    if (is_remote !== undefined) p.append("is_remote", String(is_remote));
    p.append("limit", "30");
    return request<OpportunityItem[]>(`/opportunities?${p.toString()}`);
  },
  createOpportunity: (payload: {
    title: string;
    organization: string;
    opportunity_type: string;
    description: string;
    location?: string;
    is_remote?: boolean;
    deadline?: string;
    stipend_or_prize?: string;
    apply_url: string;
    tags?: string;
  }) => request<OpportunityItem>("/opportunities", { method: "POST", body: JSON.stringify(payload) }),
  toggleBookmarkOpportunity: (id: number) =>
    request<{ status: string; is_bookmarked: boolean; message: string }>(`/opportunities/${id}/bookmark`, {
      method: "POST",
    }),
  myBookmarkedOpportunities: () => request<OpportunityItem[]>("/opportunities/my/bookmarks"),
  deactivateExpiredOpportunities: () =>
    request<{ status: string; deactivated_count: number }>("/opportunities/deactivate-expired", { method: "POST" }),
  seedVerifiedOpportunities: () =>
    request<{ status: string; inserted_count: number }>("/opportunities/seed-verified", { method: "POST" }),
  syncKaggleOpportunities: () =>
    request<{ status: string; ingested_count: number; message: string }>("/opportunities/sync/kaggle", { method: "POST" }),
  syncGithubOpportunities: () =>
    request<{ status: string; ingested_count: number; message: string }>("/opportunities/sync/github", { method: "POST" }),

  // Instagram Integration
  getInstagramStatus: () => request<InstagramStatus>("/instagram/status"),
  getInstagramConnectUrl: () => request<{ status: string; authorize_url: string; note: string }>("/instagram/connect"),
  syncInstagram: () =>
    request<{ status: string; username?: string; synced_media_count: number; suggested_interests_count: number; message: string }>(
      "/instagram/sync",
      { method: "POST" }
    ),
  disconnectInstagram: () => request<{ status: string; message: string }>("/instagram/disconnect", { method: "DELETE" }),
  getInstagramMedia: (userId?: number, limit = 24) => {
    const q = new URLSearchParams();
    if (userId) q.append("user_id", String(userId));
    q.append("limit", String(limit));
    return request<InstagramMediaItem[]>(`/instagram/media?${q.toString()}`);
  },
  updateInstagramPreferences: (prefs: { recommendations_enabled?: boolean; profile_visible?: boolean }) =>
    request<{ status: string; recommendations_enabled: boolean; profile_visible: boolean }>("/instagram/preferences", {
      method: "POST",
      body: JSON.stringify(prefs),
    }),
  getSuggestedInterests: (status = "pending") =>
    request<SuggestedInterestItem[]>(`/instagram/suggested-interests?status=${status}`),
  acceptSuggestedInterest: (id: number) =>
    request<{ status: string; interest: string }>(`/instagram/suggested-interests/${id}/accept`, { method: "POST" }),
  rejectSuggestedInterest: (id: number) =>
    request<{ status: string; interest: string }>(`/instagram/suggested-interests/${id}/reject`, { method: "POST" }),
};
