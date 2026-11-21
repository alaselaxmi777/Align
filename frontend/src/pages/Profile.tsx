import { FormEvent, useEffect, useState } from "react";
import {
  Bookmark,
  Calendar,
  Check,
  Clapperboard,
  Code2,
  Compass,
  Edit3,
  ExternalLink,
  Grid3X3,
  Heart,
  Image as ImageIcon,
  Layers,
  LayoutGrid,
  LoaderCircle,
  MapPin,
  MessageCircle,
  MessageSquare,
  Play,
  Plus,
  Send,
  Settings as SettingsIcon,
  Share2,
  Shield,
  Sliders,
  Sparkles,
  Target,
  User as UserIcon,
  UserPlus,
  Users,
  Wrench,
  X,
  Instagram,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import PostDetailModal from "../components/PostDetailModal";
import ReelPlayerModal, { ReelItem } from "../components/ReelPlayerModal";
import { api, InstagramMediaItem, Post, SavedItem, sanitizeExternalUrl, User } from "../lib/api";
import { SafeImage, SafeAvatar } from "../components/common/SafeImage";
import { useToast } from "../components/common/ToastContext";
import { formatApiError } from "../lib/errorUtils";

const COMMUNITY_REELS: ReelItem[] = [];

export default function Profile() {
  const { id: paramId } = useParams<{ id?: string }>();
  const toast = useToast();
  const [user, setUser] = useState<User | null>(null);
  const [me, setMe] = useState<User | null>(null);
  const [isOwnProfile, setIsOwnProfile] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState<string>("none");
  const [connecting, setConnecting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"posts" | "reels" | "saved" | "instagram" | "edit">("posts");

  // Instagram State
  const [igMedia, setIgMedia] = useState<InstagramMediaItem[]>([]);
  const [loadingIgMedia, setLoadingIgMedia] = useState(false);
  const [igConnected, setIgConnected] = useState(false);

  // Posts State
  const [posts, setPosts] = useState<Post[]>([]);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);

  // Reels State
  const [userReels, setUserReels] = useState<ReelItem[]>([]);
  const [selectedReel, setSelectedReel] = useState<ReelItem | null>(null);

  // Saved Items State
  const [savedItems, setSavedItems] = useState<SavedItem[]>([]);
  const [loadingSaved, setLoadingSaved] = useState(false);

  // New Post Modal State
  const [showCreatePost, setShowCreatePost] = useState(false);
  const [newPostContent, setNewPostContent] = useState("");
  const [newPostImage, setNewPostImage] = useState("");
  const [creatingPost, setCreatingPost] = useState(false);

  // Edit fields
  const [name, setName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [bio, setBio] = useState("");
  const [location, setLocation] = useState("");
  const [interests, setInterests] = useState("");
  const [skills, setSkills] = useState("");
  const [goals, setGoals] = useState("");
  const [activities, setActivities] = useState("");
  const [communityTypes, setCommunityTypes] = useState("");
  const [saving, setSaving] = useState(false);
  const [syncingGh, setSyncingGh] = useState(false);
  const [ghUsername, setGhUsername] = useState("alaselaxmi25-png");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    void loadUserData();
  }, [paramId]);

  async function loadUserData() {
    setLoading(true);
    try {
      const myUser = await api.me();
      setMe(myUser);

      let targetUser = myUser;
      const targetIsSelf = !paramId || String(myUser.id) === String(paramId);
      setIsOwnProfile(targetIsSelf);

      if (!targetIsSelf && paramId) {
        try {
          if (/^\d+$/.test(paramId)) {
            targetUser = await api.getUserProfile(Number(paramId));
          } else {
            targetUser = await api.getUserByUsername(paramId);
          }
          const connRes = await api.connectionStatus(targetUser.id);
          setConnectionStatus(connRes.status || "none");
        } catch (fetchErr) {
          console.error("Target user profile fetch failed", fetchErr);
        }
      }

      setUser(targetUser);
      setName(targetUser.name || "");
      const p = targetUser.profile;
      if (p) {
        setAvatarUrl(p.avatar_url || "");
        setBio(p.bio || "");
        setLocation(p.location || "");
        setInterests(p.interests || "");
        setSkills(p.skills || "");
        setGoals(p.goals || "");
        setActivities(p.preferred_activities || "");
        setCommunityTypes(p.preferred_community_types || "");
      }

      // Load user's posts
      loadPosts(targetUser.id);
      // Load user's reels
      loadReels(targetUser.name);
      // Load saved items and instagram only for self
      if (targetIsSelf) {
        loadSavedItems();
        loadInstagramMedia();
      }
    } catch (err) {
      setError("Please sign in to view this profile.");
      navigate("/login?next=/profile");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleConnect() {
    if (!user) return;
    setConnecting(true);
    try {
      if (connectionStatus === "accepted" || connectionStatus === "connected") {
        await api.disconnectUser(user.id);
        setConnectionStatus("none");
      } else {
        const res = await api.connectUser(user.id);
        setConnectionStatus(res.connection_status || "pending");
      }
    } catch (err: any) {
      toast.error(formatApiError(err, "Failed to update connection."));
    } finally {
      setConnecting(false);
    }
  }

  async function loadInstagramMedia() {
    setLoadingIgMedia(true);
    try {
      const status = await api.getInstagramStatus();
      if (status.connected) {
        setIgConnected(true);
        const media = await api.getInstagramMedia();
        setIgMedia(media);
      } else {
        setIgConnected(false);
        setIgMedia([]);
      }
    } catch {
      setIgConnected(false);
      setIgMedia([]);
    } finally {
      setLoadingIgMedia(false);
    }
  }

  async function loadPosts(userId: number) {
    setLoadingPosts(true);
    try {
      const userPosts = await api.feed({ author_id: userId });
      setPosts(userPosts);
    } catch (err) {
      console.error("Failed to load user posts", err);
    } finally {
      setLoadingPosts(false);
    }
  }

  async function loadReels(authorName?: string) {
    try {
      const rData = await api.reels();
      const filtered = authorName ? rData.filter((r) => r.author_name === authorName) : rData;
      setUserReels(
        filtered.map((r) => ({
          id: r.id,
          title: r.title,
          authorName: r.author_name,
          authorAvatar: r.author_avatar || undefined,
          category: r.category,
          videoUrl: r.video_url,
          thumbnailUrl: r.thumbnail_url,
          viewsCount: r.views_count,
          likesCount: r.likes_count,
          commentsCount: r.comments_count,
          audioTrack: r.audio_track || "Original Audio",
          caption: r.caption || "",
          tags: r.tags || [],
        }))
      );
    } catch {
      setUserReels([]);
    }
  }

  async function loadSavedItems() {
    setLoadingSaved(true);
    try {
      const saved = await api.saved();
      setSavedItems(saved);
    } catch (err) {
      console.error("Failed to load saved items", err);
    } finally {
      setLoadingSaved(false);
    }
  }

  async function handleCreatePost(e: FormEvent) {
    e.preventDefault();
    if (!newPostContent.trim()) return;
    setCreatingPost(true);
    try {
      const created = await api.createPost({
        content: newPostContent.trim(),
        image_url: newPostImage.trim() || undefined,
      });
      setPosts([created, ...posts]);
      setNewPostContent("");
      setNewPostImage("");
      setShowCreatePost(false);
      setSuccess("Post created successfully!");
      toast.success("Post created successfully!");
      setTimeout(() => setSuccess(""), 3500);
    } catch (err) {
      toast.error(formatApiError(err, "Failed to create post."));
    } finally {
      setCreatingPost(false);
    }
  }

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await api.updateProfile({
        name,
        avatar_url: avatarUrl || undefined,
        bio,
        location,
        interests,
        skills,
        goals,
        preferred_activities: activities,
        preferred_community_types: communityTypes,
      });
      setSuccess("Profile and intent embeddings updated successfully!");
      if (user) {
        setUser({ ...user, name });
      }
      setTimeout(() => setSuccess(""), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update profile.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSyncGithub(e: FormEvent) {
    e.preventDefault();
    if (!ghUsername.trim()) return;
    setSyncingGh(true);
    setError("");
    setSuccess("");
    try {
      const updated = await api.syncGithubSkills(ghUsername);
      if (updated.skills) setSkills(updated.skills);
      if (updated.bio) setBio(updated.bio);
      if (updated.location && !location) setLocation(updated.location);
      if (updated.avatar_url && !avatarUrl) setAvatarUrl(updated.avatar_url);
      setSuccess(`Imported verified GitHub skills (${updated.skills})!`);
      setTimeout(() => setSuccess(""), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import from GitHub.");
    } finally {
      setSyncingGh(false);
    }
  }

  // Calculate profile completion percentage
  const fields = [name, bio, location, interests, skills, goals, activities, communityTypes, avatarUrl];
  const filledCount = fields.filter((f) => f && f.trim().length > 0).length;
  const completionPercentage = Math.round((filledCount / fields.length) * 100);

  // Extract skills & interests chips
  const skillChips = skills ? skills.split(",").map((s) => s.trim()).filter(Boolean) : [];
  const interestChips = interests ? interests.split(",").map((s) => s.trim()).filter(Boolean) : [];

  if (loading) {
    return (
      <AppShell title="My profile">
        <div className="empty-state" style={{ minHeight: "60vh" }}>
          <LoaderCircle className="spin" size={32} style={{ color: "var(--accent)" }} />
          <p style={{ color: "var(--muted)" }}>Loading your profile...</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title="My profile">
      <div style={{ maxWidth: "935px", margin: "0 auto" }}>
        {/* Instagram-Inspired Profile Header */}
        <header
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "clamp(24px, 5vw, 64px)",
            marginBottom: "36px",
          }}
          className="flex-col sm:flex-row items-center sm:items-start text-center sm:text-left"
        >
          {/* Profile Picture with Story-Ring Gradient */}
          <div style={{ flexShrink: 0 }}>
            <div className="story-ring" style={{ padding: "3.5px" }}>
              <div className="story-ring-inner" style={{ padding: "2.5px" }}>
                <div
                  style={{
                    width: "clamp(90px, 16vw, 150px)",
                    height: "clamp(90px, 16vw, 150px)",
                    borderRadius: "50%",
                    overflow: "hidden",
                    background: "linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-card) 100%)",
                    display: "grid",
                    placeItems: "center",
                    fontSize: "clamp(32px, 5vw, 56px)",
                    fontWeight: 800,
                    color: "var(--primary-accent)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <SafeAvatar
                    src={avatarUrl}
                    name={name || user?.name || "User"}
                    size="100%"
                    fontSize="clamp(32px, 5vw, 56px)"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Profile Information & Actions */}
          <div style={{ flex: 1, minWidth: 0, width: "100%" }}>
            {/* Top Handle & Action Buttons */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "12px",
                marginBottom: "16px",
                justifyContent: "inherit",
              }}
            >
              <h1
                style={{
                  fontSize: "clamp(20px, 3vw, 24px)",
                  fontWeight: 700,
                  color: "var(--primary-text)",
                  margin: 0,
                  letterSpacing: "-0.5px",
                }}
              >
                {user?.username ? `@${user.username}` : (user?.name || "align_user")}
              </h1>

              {/* Verified Badge */}
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "18px",
                  height: "18px",
                  borderRadius: "50%",
                  background: "var(--primary-accent)",
                  color: "#FFFFFF",
                }}
                title="Verified ALIGN Member"
              >
                <Check size={12} strokeWidth={3} />
              </span>

              {/* Action Buttons */}
              <div style={{ display: "inline-flex", gap: "8px", flexWrap: "wrap", marginLeft: "auto" }} className="w-full sm:w-auto justify-center sm:justify-start">
                {isOwnProfile ? (
                  <>
                    <button
                      type="button"
                      onClick={() => setActiveTab("edit")}
                      style={{
                        padding: "7px 16px",
                        borderRadius: "8px",
                        border: "1px solid var(--border-subtle)",
                        background: activeTab === "edit" ? "var(--primary-accent)" : "var(--bg-card)",
                        color: activeTab === "edit" ? "#FFFFFF" : "var(--primary-text)",
                        fontSize: "13px",
                        fontWeight: "600",
                        cursor: "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        transition: "all 0.2s ease",
                      }}
                    >
                      <Edit3 size={14} /> Edit Profile
                    </button>

                    <button
                      type="button"
                      onClick={() => setShowCreatePost(true)}
                      style={{
                        padding: "7px 16px",
                        borderRadius: "8px",
                        border: "none",
                        background: "var(--primary-accent)",
                        color: "#FFFFFF",
                        fontSize: "13px",
                        fontWeight: "600",
                        cursor: "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        boxShadow: "0 2px 8px rgba(83, 101, 245, 0.3)",
                        transition: "all 0.2s ease",
                      }}
                    >
                      <Plus size={15} /> New Post
                    </button>

                    <button
                      type="button"
                      onClick={() => navigate("/settings")}
                      style={{
                        padding: "7px 10px",
                        borderRadius: "8px",
                        border: "1px solid var(--border-subtle)",
                        background: "var(--bg-card)",
                        color: "var(--primary-text)",
                        cursor: "pointer",
                        display: "grid",
                        placeItems: "center",
                      }}
                      title="Settings"
                    >
                      <SettingsIcon size={16} />
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={handleToggleConnect}
                      disabled={connecting}
                      style={{
                        padding: "7px 18px",
                        borderRadius: "8px",
                        border: "1px solid var(--border-subtle)",
                        background:
                          connectionStatus === "accepted" || connectionStatus === "connected"
                            ? "var(--bg-card)"
                            : "var(--primary-accent)",
                        color:
                          connectionStatus === "accepted" || connectionStatus === "connected"
                            ? "var(--primary-text)"
                            : "#FFFFFF",
                        fontSize: "13px",
                        fontWeight: "600",
                        cursor: connecting ? "not-allowed" : "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        transition: "all 0.2s ease",
                      }}
                    >
                      <UserPlus size={15} />
                      {connectionStatus === "accepted" || connectionStatus === "connected"
                        ? "Connected"
                        : connectionStatus === "pending"
                        ? "Request Sent"
                        : "Connect"}
                    </button>

                    <button
                      type="button"
                      onClick={() => navigate(`/messages?user=${user?.id}`)}
                      style={{
                        padding: "7px 18px",
                        borderRadius: "8px",
                        border: "1px solid var(--border-subtle)",
                        background: "var(--bg-card)",
                        color: "var(--primary-text)",
                        fontSize: "13px",
                        fontWeight: "600",
                        cursor: "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <MessageCircle size={15} /> Message
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Stats Row: Posts, Followers, Following */}
            <div
              style={{
                display: "flex",
                gap: "clamp(16px, 4vw, 36px)",
                marginBottom: "16px",
                justifyContent: "inherit",
                fontSize: "14px",
                color: "var(--primary-text)",
              }}
            >
              <div>
                <strong style={{ fontWeight: 700 }}>{posts.length}</strong>{" "}
                <span style={{ color: "var(--secondary-text)" }}>posts</span>
              </div>
              <div>
                <strong style={{ fontWeight: 700 }}>{user?.followers_count ?? 0}</strong>{" "}
                <span style={{ color: "var(--secondary-text)" }}>followers</span>
              </div>
              <div>
                <strong style={{ fontWeight: 700 }}>{user?.following_count ?? 0}</strong>{" "}
                <span style={{ color: "var(--secondary-text)" }}>following</span>
              </div>
              <div>
                <strong style={{ fontWeight: 700 }}>{user?.connections_count ?? 0}</strong>{" "}
                <span style={{ color: "var(--secondary-text)" }}>connections</span>
              </div>
            </div>

            {/* Profile Bio Details */}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <span style={{ fontWeight: 700, fontSize: "15px", color: "var(--primary-text)" }}>
                {name || user?.name}
              </span>

              {bio && (
                <p style={{ margin: 0, fontSize: "14px", color: "var(--primary-text)", lineHeight: "1.5" }}>
                  {bio}
                </p>
              )}

              {/* Location */}
              {location && (
                <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--secondary-text)", fontSize: "13px" }}>
                  <MapPin size={13} style={{ color: "var(--primary-accent)" }} />
                  <span>{location}</span>
                </div>
              )}

              {/* Skills & Interest Hashtag Badges */}
              {(skillChips.length > 0 || interestChips.length > 0) && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "4px" }}>
                  {skillChips.map((s, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: "12px",
                        fontWeight: "600",
                        padding: "2px 8px",
                        borderRadius: "6px",
                        background: "var(--bg-secondary)",
                        color: "var(--primary-accent)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      #{s}
                    </span>
                  ))}
                  {interestChips.map((i, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: "12px",
                        fontWeight: "500",
                        padding: "2px 8px",
                        borderRadius: "6px",
                        background: "var(--bg-card)",
                        color: "var(--secondary-text)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      #{i}
                    </span>
                  ))}
                </div>
              )}

              {/* Learning Goals */}
              {goals && (
                <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--secondary-text)", fontSize: "12px", marginTop: "2px" }}>
                  <Target size={13} style={{ color: "var(--primary-accent)" }} />
                  <span>Goal: {goals}</span>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Success / Error Banners */}
        {error && <div className="error-box" style={{ marginBottom: "18px" }}>{error}</div>}
        {success && (
          <div
            className="error-box"
            style={{
              borderColor: "var(--success-color)",
              background: "rgba(16, 185, 129, 0.15)",
              color: "var(--primary-text)",
              marginBottom: "18px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontWeight: 600,
            }}
          >
            <Check size={16} style={{ color: "var(--success-color)" }} /> {success}
          </div>
        )}

        {/* Instagram-Style Centered Tabs Bar */}
        <nav
          style={{
            display: "flex",
            justifyContent: "center",
            borderTop: "1px solid var(--border-subtle)",
            marginBottom: "24px",
          }}
        >
          {[
            { id: "posts", label: "POSTS", icon: Grid3X3 },
            { id: "reels", label: "REELS", icon: Clapperboard },
            ...(isOwnProfile
              ? [
                  { id: "instagram", label: "INSTAGRAM", icon: Instagram },
                  { id: "saved", label: "SAVED", icon: Bookmark },
                  { id: "edit", label: "SETTINGS", icon: Sliders },
                ]
              : []),
          ].map((tab) => {
            const Icon = tab.icon;
            const isSelected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "14px 20px",
                  border: "none",
                  background: "transparent",
                  color: isSelected ? "var(--primary-text)" : "var(--secondary-text)",
                  borderTop: isSelected ? "2px solid var(--primary-accent)" : "2px solid transparent",
                  marginTop: "-1px",
                  fontSize: "12px",
                  fontWeight: isSelected ? 700 : 600,
                  letterSpacing: "1px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <Icon size={15} strokeWidth={isSelected ? 2.5 : 1.8} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* ========================================================
            TAB 1: POSTS (Three-Column Instagram Grid)
        ======================================================== */}
        {activeTab === "posts" && (
          <section>
            {loadingPosts ? (
              <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
                <LoaderCircle className="spin" size={32} style={{ color: "var(--primary-accent)" }} />
              </div>
            ) : posts.length === 0 ? (
              <div className="empty-state" style={{ padding: "60px 20px" }}>
                <Grid3X3 size={44} style={{ color: "var(--secondary-text)", margin: "0 auto 12px" }} />
                <h3 style={{ color: "var(--primary-text)", margin: "0 0 6px 0" }}>No Posts Yet</h3>
                <p style={{ color: "var(--secondary-text)", margin: "0 0 16px 0" }}>
                  Share photos, project updates, or learning moments with your community.
                </p>
                <button
                  type="button"
                  onClick={() => setShowCreatePost(true)}
                  className="cta-button"
                >
                  <Plus size={15} /> Create First Post
                </button>
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                  gap: "clamp(4px, 1.5vw, 18px)",
                }}
              >
                {posts.map((post) => (
                  <article
                    key={post.id}
                    onClick={() => setSelectedPost(post)}
                    style={{
                      position: "relative",
                      borderRadius: "10px",
                      overflow: "hidden",
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border-subtle)",
                      cursor: "pointer",
                      aspectRatio: "1 / 1",
                    }}
                    className="group"
                  >
                    {/* Post Image or Styled Visual Fallback */}
                    {post.image_url ? (
                      <SafeImage
                        src={post.image_url}
                        alt="Post thumbnail"
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          display: "block",
                          transition: "transform 0.3s ease",
                        }}
                        className="group-hover:scale-105"
                      />
                    ) : (
                      <div
                        style={{
                          width: "100%",
                          height: "100%",
                          padding: "16px",
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                          background: "linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%)",
                        }}
                      >
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: "6px",
                            background: "rgba(83, 101, 245, 0.15)",
                            color: "var(--primary-accent)",
                            alignSelf: "flex-start",
                          }}
                        >
                          {post.community_name || "ALIGN Post"}
                        </span>
                        <p
                          style={{
                            fontSize: "13px",
                            fontWeight: 600,
                            lineHeight: "1.4",
                            color: "var(--primary-text)",
                            margin: 0,
                            display: "-webkit-box",
                            WebkitLineClamp: 3,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                          }}
                        >
                          {post.content}
                        </p>
                        <span style={{ fontSize: "10px", color: "var(--secondary-text)" }}>
                          {new Date(post.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    )}

                    {/* Instagram-Style Hover Overlay with Likes & Comments */}
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        background: "rgba(0, 0, 0, 0.55)",
                        backdropFilter: "blur(2px)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "24px",
                        color: "#FFFFFF",
                        opacity: 0,
                        transition: "opacity 0.2s ease",
                      }}
                      className="group-hover:opacity-100"
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700 }}>
                        <Heart size={18} fill="#FFFFFF" />
                        <span>{post.likes_count || 0}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700 }}>
                        <MessageSquare size={18} fill="#FFFFFF" />
                        <span>{post.comments_count || 0}</span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ========================================================
            TAB 2: REELS (Vertical 9:16 Cards with Views Count)
        ======================================================== */}
        {activeTab === "reels" && (
          <section>
            {userReels.length === 0 ? (
              <div className="empty-state" style={{ padding: "60px 20px" }}>
                <Clapperboard size={44} style={{ color: "var(--secondary-text)", margin: "0 auto 12px" }} />
                <h3 style={{ color: "var(--primary-text)", margin: "0 0 6px 0" }}>No Reels Yet</h3>
                <p style={{ color: "var(--secondary-text)", margin: "0 0 16px 0" }}>
                  Record or upload short community experience clips to share on your profile.
                </p>
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                  gap: "16px",
                }}
              >
                {userReels.map((reel) => (
                  <article
                    key={reel.id}
                    onClick={() => setSelectedReel(reel)}
                    style={{
                      position: "relative",
                      borderRadius: "14px",
                      overflow: "hidden",
                      background: "#000000",
                      border: "1px solid var(--border-subtle)",
                      cursor: "pointer",
                      aspectRatio: "9 / 16",
                      boxShadow: "var(--card-shadow)",
                    }}
                    className="group"
                  >
                    {/* Thumbnail / Video */}
                    <SafeImage
                      src={reel.thumbnailUrl}
                      alt={reel.title}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        display: "block",
                        transition: "transform 0.3s ease",
                      }}
                      className="group-hover:scale-105"
                    />

                    {/* Top Reel Badge */}
                    <div
                      style={{
                        position: "absolute",
                        top: "10px",
                        right: "10px",
                        zIndex: 5,
                        color: "#FFFFFF",
                        background: "rgba(0, 0, 0, 0.4)",
                        backdropFilter: "blur(4px)",
                        borderRadius: "6px",
                        padding: "4px",
                        display: "grid",
                        placeItems: "center",
                      }}
                    >
                      <Clapperboard size={15} />
                    </div>

                    {/* Gradient Overlay & Bottom Info */}
                    <div
                      style={{
                        position: "absolute",
                        bottom: 0,
                        left: 0,
                        right: 0,
                        padding: "14px 12px",
                        background: "linear-gradient(0deg, rgba(0, 0, 0, 0.85) 0%, rgba(0, 0, 0, 0.4) 60%, transparent 100%)",
                        color: "#FFFFFF",
                        display: "flex",
                        flexDirection: "column",
                        gap: "4px",
                        zIndex: 5,
                      }}
                    >
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: 700,
                          lineHeight: "1.3",
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                          textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                        }}
                      >
                        {reel.caption}
                      </span>

                      {/* View Count Display (Instagram Reels Requirement) */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          fontSize: "11px",
                          fontWeight: 700,
                          color: "rgba(255, 255, 255, 0.9)",
                          marginTop: "4px",
                        }}
                      >
                        <Play size={12} fill="#FFFFFF" />
                        <span>{reel.viewsCount}</span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ========================================================
            TAB: INSTAGRAM (Synced Media Grid from Instagram API)
        ======================================================== */}
        {activeTab === "instagram" && (
          <section>
            {loadingIgMedia ? (
              <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
                <LoaderCircle className="spin" size={32} style={{ color: "var(--primary-accent)" }} />
              </div>
            ) : !igConnected || igMedia.length === 0 ? (
              <div className="empty-state" style={{ padding: "60px 20px" }}>
                <div
                  style={{
                    width: "56px",
                    height: "56px",
                    borderRadius: "16px",
                    background: "linear-gradient(45deg, #F58529, #DD2A7B, #8134AF, #515BD4)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#fff",
                    margin: "0 auto 16px",
                  }}
                >
                  <Instagram size={28} />
                </div>
                <h3 style={{ color: "var(--primary-text)", margin: "0 0 6px 0" }}>
                  {!igConnected ? "Connect Your Instagram" : "No Instagram Media Synced Yet"}
                </h3>
                <p style={{ color: "var(--secondary-text)", margin: "0 0 18px 0", maxWidth: "420px", marginLeft: "auto", marginRight: "auto", fontSize: "14px" }}>
                  {!igConnected
                    ? "Link your Instagram Business or Creator account in Settings to showcase your photos, reels, and visual passions directly on your ALIGN profile."
                    : "Your account is connected, but no posts were returned from the Instagram API. Head to Settings to trigger a sync."}
                </p>
                <Link
                  to="/settings"
                  className="cta-button"
                  style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
                >
                  <SettingsIcon size={15} /> Configure Instagram in Settings
                </Link>
              </div>
            ) : (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div
                      style={{
                        width: "24px",
                        height: "24px",
                        borderRadius: "6px",
                        background: "linear-gradient(45deg, #F58529, #DD2A7B, #8134AF)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                      }}
                    >
                      <Instagram size={14} />
                    </div>
                    <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--primary-text)" }}>
                      Synced Instagram Media ({igMedia.length})
                    </span>
                  </div>
                  <Link
                    to="/settings"
                    style={{ fontSize: "12px", color: "var(--primary-accent)", textDecoration: "none", fontWeight: 600 }}
                  >
                    Sync Settings →
                  </Link>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                    gap: "clamp(4px, 1.5vw, 18px)",
                  }}
                >
                  {igMedia.map((media) => (
                    <article
                      key={media.id}
                      style={{
                        position: "relative",
                        borderRadius: "10px",
                        overflow: "hidden",
                        background: "var(--bg-secondary)",
                        border: "1px solid var(--border-subtle)",
                        cursor: "pointer",
                        aspectRatio: "1 / 1",
                      }}
                      className="group"
                    >
                      <SafeImage
                        src={media.media_url}
                        alt={media.caption ? media.caption.slice(0, 60) : "Instagram post"}
                        loading="lazy"
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          display: "block",
                          transition: "transform 0.3s ease",
                        }}
                        className="group-hover:scale-105"
                      />

                      {/* Top-Right Media Type Badge */}
                      <div
                        style={{
                          position: "absolute",
                          top: "8px",
                          right: "8px",
                          background: "rgba(0, 0, 0, 0.6)",
                          backdropFilter: "blur(4px)",
                          borderRadius: "6px",
                          padding: "4px 6px",
                          display: "flex",
                          alignItems: "center",
                          color: "#fff",
                          zIndex: 2,
                        }}
                      >
                        {media.media_type === "VIDEO" ? (
                          <Play size={12} fill="#fff" />
                        ) : media.media_type === "CAROUSEL_ALBUM" ? (
                          <Layers size={12} />
                        ) : (
                          <ImageIcon size={12} />
                        )}
                      </div>

                      {/* Hover Overlay */}
                      <div
                        style={{
                          position: "absolute",
                          inset: 0,
                          background: "rgba(0, 0, 0, 0.7)",
                          backdropFilter: "blur(2px)",
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                          padding: "16px",
                          opacity: 0,
                          transition: "opacity 0.2s ease",
                          zIndex: 3,
                        }}
                        className="group-hover:!opacity-100"
                      >
                        <div>
                          {media.caption && (
                            <p
                              style={{
                                color: "#fff",
                                fontSize: "12px",
                                lineHeight: "1.4",
                                margin: "0 0 8px 0",
                                display: "-webkit-box",
                                WebkitLineClamp: 4,
                                WebkitBoxOrient: "vertical",
                                overflow: "hidden",
                              }}
                            >
                              {media.caption}
                            </p>
                          )}
                          {media.hashtags && (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                              {media.hashtags.split(",").slice(0, 3).map((tag, i) => (
                                <span
                                  key={i}
                                  style={{
                                    fontSize: "10px",
                                    color: "var(--primary-accent)",
                                    background: "rgba(83, 101, 245, 0.25)",
                                    padding: "2px 6px",
                                    borderRadius: "4px",
                                  }}
                                >
                                  #{tag.trim()}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: "11px", color: "rgba(255, 255, 255, 0.7)" }}>
                            {media.timestamp ? new Date(media.timestamp).toLocaleDateString() : ""}
                          </span>
                          {media.permalink && (
                            <a
                              href={sanitizeExternalUrl(media.permalink)}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                background: "linear-gradient(45deg, #DD2A7B, #8134AF)",
                                color: "#fff",
                                padding: "4px 8px",
                                borderRadius: "6px",
                                fontSize: "11px",
                                fontWeight: 600,
                                textDecoration: "none",
                              }}
                            >
                              <span>View</span>
                              <ExternalLink size={11} />
                            </a>
                          )}
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* ========================================================
            TAB 3: SAVED (Bookmarked Communities & Events)
        ======================================================== */}
        {activeTab === "saved" && (
          <section>
            {loadingSaved ? (
              <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
                <LoaderCircle className="spin" size={32} style={{ color: "var(--primary-accent)" }} />
              </div>
            ) : savedItems.length === 0 ? (
              <div className="empty-state" style={{ padding: "60px 20px" }}>
                <Bookmark size={44} style={{ color: "var(--secondary-text)", margin: "0 auto 12px" }} />
                <h3 style={{ color: "var(--primary-text)", margin: "0 0 6px 0" }}>No Saved Items</h3>
                <p style={{ color: "var(--secondary-text)", margin: "0 0 16px 0" }}>
                  Save communities, events, and venues to easily revisit them later.
                </p>
                <button
                  type="button"
                  onClick={() => navigate("/discover")}
                  className="cta-button"
                >
                  <Compass size={15} /> Discover Experiences
                </button>
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                  gap: "18px",
                }}
              >
                {savedItems.map((item) => (
                  <div
                    key={item.id}
                    className="result-card"
                    style={{
                      padding: "20px",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <span className="result-type">{item.item_type}</span>
                      <h3 style={{ margin: "6px 0", fontSize: "16px", color: "var(--primary-text)" }}>
                        {item.title || `Saved ${item.item_type}`}
                      </h3>
                      {item.description && (
                        <p style={{ fontSize: "13px", color: "var(--secondary-text)", margin: "0 0 10px 0" }}>
                          {item.description}
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate(`/${item.item_type === "community" ? "communities" : "events"}`)}
                      style={{
                        padding: "8px 14px",
                        borderRadius: "8px",
                        border: "1px solid var(--border-subtle)",
                        background: "var(--bg-secondary)",
                        color: "var(--primary-text)",
                        fontSize: "12px",
                        fontWeight: 600,
                        cursor: "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        alignSelf: "flex-start",
                      }}
                    >
                      <ExternalLink size={13} /> View {item.item_type}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ========================================================
            TAB 4: EDIT PROFILE & GITHUB SYNC
        ======================================================== */}
        {activeTab === "edit" && (
          <section style={{ maxWidth: "720px", margin: "0 auto" }}>
            {/* Profile Completion Indicator */}
            <div
              className="auth-card"
              style={{
                marginBottom: "20px",
                padding: "20px 24px",
                borderRadius: "18px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--primary-text)", display: "flex", alignItems: "center", gap: "6px" }}>
                  <Sparkles size={14} style={{ color: "var(--primary-accent)" }} /> Profile Optimization
                </span>
                <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--primary-accent)" }}>
                  {completionPercentage}% Complete
                </span>
              </div>

              {/* Progress Bar Track */}
              <div
                style={{
                  width: "100%",
                  height: "10px",
                  background: "var(--bg-secondary)",
                  borderRadius: "100px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${completionPercentage}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, #5365F5 0%, #6677FF 100%)",
                    borderRadius: "100px",
                    transition: "width 0.4s ease",
                  }}
                />
              </div>

              <p style={{ margin: "8px 0 0 0", fontSize: "12px", color: "var(--secondary-text)" }}>
                {completionPercentage >= 85
                  ? "🌟 Excellent! Your profile embeddings are fully optimized for personalized recommendation."
                  : "Tip: Add your programming skills, passions, and learning goals to unlock tailored matches."}
              </p>
            </div>

            {/* GitHub Skills Auto-Import Card */}
            <div
              className="auth-card"
              style={{
                marginBottom: "20px",
                padding: "22px 24px",
                borderRadius: "18px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--primary-accent)", fontSize: "12px", fontWeight: "700" }}>
                <Code2 size={15} /> VERIFIED GITHUB SKILLS IMPORT
              </div>
              <h3 style={{ margin: "6px 0", fontSize: "16px", color: "var(--primary-text)" }}>Sync Technical Stack from GitHub</h3>
              <p style={{ margin: "0 0 14px 0", fontSize: "13px", color: "var(--secondary-text)" }}>
                Automatically extract your programming languages, repository topics, and bio from GitHub.
              </p>

              <form onSubmit={handleSyncGithub} style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                <input
                  value={ghUsername}
                  onChange={(e) => setGhUsername(e.target.value)}
                  placeholder="e.g. your-github-username"
                  style={{
                    flex: 1,
                    minWidth: "220px",
                    padding: "10px 14px",
                    borderRadius: "10px",
                    background: "var(--bg-card)",
                    border: "1.5px solid var(--border-subtle)",
                    color: "var(--primary-text)",
                    fontSize: "13px",
                  }}
                  required
                />
                <button
                  type="submit"
                  disabled={syncingGh}
                  className="cta-button"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "12px",
                    fontWeight: "700",
                  }}
                >
                  {syncingGh ? (
                    <>
                      <LoaderCircle className="spin" size={14} /> Syncing...
                    </>
                  ) : (
                    <>
                      <Code2 size={14} /> Import GitHub Skills
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Instagram Creator & Visual Passions Card */}
            <div
              className="auth-card"
              style={{
                marginBottom: "20px",
                padding: "22px 24px",
                borderRadius: "18px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--primary-accent)", fontSize: "12px", fontWeight: "700" }}>
                <Instagram size={15} /> INSTAGRAM BUSINESS / CREATOR INTEGRATION
              </div>
              <h3 style={{ margin: "6px 0", fontSize: "16px", color: "var(--primary-text)" }}>Connect Instagram &amp; Visual Discovery</h3>
              <p style={{ margin: "0 0 14px 0", fontSize: "13px", color: "var(--secondary-text)" }}>
                Sync your creator or business posts to display a visual media portfolio on your profile and opt-in to discover peers with matching creative passions.
              </p>
              <Link
                to="/settings"
                className="button"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  fontWeight: "700",
                }}
              >
                <SettingsIcon size={14} /> Manage Instagram in Settings
              </Link>
            </div>

            {/* Profile Edit Form */}
            <form onSubmit={saveProfile} className="auth-card" style={{ padding: "26px", borderRadius: "18px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--primary-text)", margin: "0 0 18px 0" }}>
                Personal Information & Embeddings
              </h3>

              <div className="auth-form">
                <label>
                  Full Name
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Alex Morgan"
                    required
                  />
                </label>

                <label>
                  Avatar / Profile Picture URL
                  <input
                    value={avatarUrl}
                    onChange={(e) => setAvatarUrl(e.target.value)}
                    placeholder="https://images.unsplash.com/..."
                  />
                </label>

                <label>
                  Bio & Elevator Pitch
                  <input
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    placeholder="e.g. Computer science student building AI side projects and exploring hiking trails."
                  />
                </label>

                <label>
                  Location / City
                  <input
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. Pune, MH or Online"
                  />
                </label>

                <label>
                  Interests & Passions (comma-separated)
                  <input
                    value={interests}
                    onChange={(e) => setInterests(e.target.value)}
                    placeholder="e.g. Machine Learning, Hiking, UI/UX Design, Open Source"
                  />
                </label>

                <label>
                  Technical Skills & Tools (comma-separated)
                  <input
                    value={skills}
                    onChange={(e) => setSkills(e.target.value)}
                    placeholder="e.g. Python, FastAPI, React, PyTorch, Figma, TypeScript"
                  />
                </label>

                <label>
                  Learning & Exploration Goals
                  <input
                    value={goals}
                    onChange={(e) => setGoals(e.target.value)}
                    placeholder="e.g. Build production machine learning systems, collaborate with AI study circles"
                  />
                </label>

                <label>
                  Preferred Activities
                  <input
                    value={activities}
                    onChange={(e) => setActivities(e.target.value)}
                    placeholder="e.g. Hackathons, weekend meetups, collaborative code reviews"
                  />
                </label>

                <label>
                  Preferred Community Types
                  <input
                    value={communityTypes}
                    onChange={(e) => setCommunityTypes(e.target.value)}
                    placeholder="e.g. Technology, Outdoors, Design, Student Clubs"
                  />
                </label>

                <button type="submit" className="submit-button" disabled={saving} style={{ marginTop: "12px" }}>
                  {saving ? "Saving Intent & Embeddings..." : "Save Profile & Refresh Embeddings"}
                </button>
              </div>
            </form>
          </section>
        )}

      {/* Post Detail Modal */}
      {selectedPost && (
        <PostDetailModal
          post={selectedPost}
          onClose={() => setSelectedPost(null)}
          onPostUpdated={(updated) => {
            setPosts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
          }}
        />
      )}

      {/* Reel Player Modal */}
      {selectedReel && (
        <ReelPlayerModal
          reel={selectedReel}
          onClose={() => setSelectedReel(null)}
        />
      )}

      {/* Create Post Modal */}
      {showCreatePost && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 65,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "16px",
            background: "rgba(0, 0, 0, 0.7)",
            backdropFilter: "blur(6px)",
          }}
          onClick={() => setShowCreatePost(false)}
        >
          <div
            style={{
              position: "relative",
              width: "100%",
              maxWidth: "520px",
              background: "var(--bg-card)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "18px",
              padding: "24px",
              boxShadow: "0 20px 50px rgba(0, 0, 0, 0.4)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ margin: 0, fontSize: "18px", fontWeight: 700, color: "var(--primary-text)" }}>
                Create New Post
              </h3>
              <button
                type="button"
                onClick={() => setShowCreatePost(false)}
                style={{ background: "transparent", border: "none", color: "var(--secondary-text)", cursor: "pointer" }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreatePost}>
              <textarea
                value={newPostContent}
                onChange={(e) => setNewPostContent(e.target.value)}
                placeholder="What project or idea are you working on?"
                rows={4}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: "12px",
                  border: "1.5px solid var(--border-subtle)",
                  background: "var(--bg-secondary)",
                  color: "var(--primary-text)",
                  fontSize: "14px",
                  resize: "vertical",
                  boxSizing: "border-box",
                  fontFamily: "inherit",
                  marginBottom: "12px",
                }}
                required
              />

              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "18px" }}>
                <ImageIcon size={18} style={{ color: "var(--secondary-text)" }} />
                <input
                  type="url"
                  value={newPostImage}
                  onChange={(e) => setNewPostImage(e.target.value)}
                  placeholder="Image URL (e.g. https://...)"
                  style={{
                    flex: 1,
                    padding: "10px 14px",
                    borderRadius: "10px",
                    border: "1px solid var(--border-subtle)",
                    background: "var(--bg-card)",
                    color: "var(--primary-text)",
                    fontSize: "13px",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowCreatePost(false)}
                  style={{
                    padding: "10px 18px",
                    borderRadius: "10px",
                    border: "1px solid var(--border-subtle)",
                    background: "transparent",
                    color: "var(--primary-text)",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingPost || !newPostContent.trim()}
                  className="cta-button"
                  style={{ padding: "10px 20px" }}
                >
                  {creatingPost ? <LoaderCircle className="spin" size={15} /> : <Send size={15} />}
                  <span>Share Post</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      </div>
    </AppShell>
  );
}
