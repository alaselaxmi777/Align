import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Activity, CalendarDays, MessageSquare, Share2, Users } from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { Community, EventItem, PostItem, api } from "../lib/api";
import PostCard from "../components/cards/PostCard";
import PostDetailModal from "../components/PostDetailModal";
import { SafeImage } from "../components/common/SafeImage";

const DEFAULT_COVER = "https://images.pexels.com/photos/3184292/pexels-photo-3184292.jpeg?auto=compress&cs=tinysrgb&w=1280";
const DEFAULT_AVATAR = "https://images.pexels.com/photos/3184418/pexels-photo-3184418.jpeg?auto=compress&cs=tinysrgb&w=400";

export default function CommunityDetail() {
  const { id } = useParams<{ id: string }>();
  const [community, setCommunity] = useState<Community | null>(null);
  const [posts, setPosts] = useState<PostItem[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [activeTab, setActiveTab] = useState<"about" | "discussions" | "events" | "members">("about");
  const [joined, setJoined] = useState(false);
  const [joining, setJoining] = useState(false);
  const [selectedPost, setSelectedPost] = useState<PostItem | null>(null);
  const [loading, setLoading] = useState(true);

  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    async function loadCommunity() {
      if (!id) return;
      setLoading(true);
      try {
        const commList = await api.communities();
        const found = commList.find((c) => String(c.id) === id);
        if (found) {
          setCommunity(found);
          setJoined(Boolean(found.is_member));
        }

        // Load community posts and events
        const commId = Number(id);
        const [feedRes, eventsRes] = await Promise.allSettled([
          api.feed({ community_id: commId }),
          api.events(),
        ]);

        if (feedRes.status === "fulfilled") {
          setPosts(feedRes.value);
        }
        if (eventsRes.status === "fulfilled") {
          setEvents(eventsRes.value.filter((e) => e.community_id === commId || !e.community_id));
        }
      } catch (err) {
        console.error("Failed to load community details:", err);
      } finally {
        setLoading(false);
      }
    }
    loadCommunity();
  }, [id]);

  async function handleToggleJoin() {
    if (!community) return;
    if (!loggedIn) {
      window.location.href = "/login";
      return;
    }
    setJoining(true);
    try {
      if (joined) {
        await api.leaveCommunity(community.id);
        setJoined(false);
        setCommunity((prev) => (prev ? { ...prev, member_count: Math.max(0, (prev.member_count ?? 1) - 1) } : prev));
      } else {
        await api.joinCommunity(community.id);
        setJoined(true);
        setCommunity((prev) => (prev ? { ...prev, member_count: (prev.member_count ?? 0) + 1 } : prev));
      }
    } catch (err) {
      console.error("Join toggle error:", err);
    } finally {
      setJoining(false);
    }
  }

  if (loading) {
    return (
      <AppShell title="Community">
        <div className="empty">Loading community details...</div>
      </AppShell>
    );
  }

  if (!community) {
    return (
      <AppShell title="Community Not Found">
        <div className="empty">
          <p>This community could not be found.</p>
          <Link to="/communities" className="button primary">
            Back to communities
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title={community.name}>
      {/* Cover Image */}
      <SafeImage
        src={community.image_url}
        fallbackSrc={DEFAULT_COVER}
        alt={community.name}
        className="cover"
        loading="lazy"
      />

      {/* Avatar Header */}
      <div className="profile-head">
        <SafeImage
          src={community.image_url}
          fallbackSrc={DEFAULT_AVATAR}
          alt={community.name}
          loading="lazy"
        />
      </div>

      {/* Info & Stats */}
      <div className="profile-info">
        <div>
          <p className="eyebrow">Community · {community.category || "General"}</p>
          <h1 className="page-title" style={{ marginBottom: "5px" }}>
            {community.name}
          </h1>
          <p className="lead" style={{ margin: "0 0 12px 0", maxWidth: "680px" }}>
            {community.description}
          </p>
          <div className="stats">
            <span>
              <b>{community.member_count ?? 0}</b> {community.member_count === 1 ? "member" : "members"}
            </span>
            <span>
              <b>{posts.length}</b> {posts.length === 1 ? "discussion" : "discussions"}
            </span>
            <span>
              <b>{community.location || "Online"}</b>
            </span>
          </div>
        </div>

        <button
          type="button"
          className={`button ${joined ? "selected" : "primary"}`}
          onClick={handleToggleJoin}
          disabled={joining}
          style={{ minWidth: "140px" }}
        >
          {joining ? "..." : joined ? "Joined Community" : "Join community"}
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="chips">
        <button
          type="button"
          className={`chip ${activeTab === "about" ? "active" : ""}`}
          onClick={() => setActiveTab("about")}
        >
          About
        </button>
        <button
          type="button"
          className={`chip ${activeTab === "discussions" ? "active" : ""}`}
          onClick={() => setActiveTab("discussions")}
        >
          Discussions ({posts.length})
        </button>
        <button
          type="button"
          className={`chip ${activeTab === "events" ? "active" : ""}`}
          onClick={() => setActiveTab("events")}
        >
          Events ({events.length})
        </button>
        <button
          type="button"
          className={`chip ${activeTab === "members" ? "active" : ""}`}
          onClick={() => setActiveTab("members")}
        >
          Members ({community.member_count ?? 0})
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "about" && (
        <div className="panel" style={{ padding: "30px", marginTop: "10px" }}>
          <h2 style={{ fontSize: "22px", fontWeight: "800", color: "var(--text)", marginBottom: "12px" }}>
            Build, share, belong.
          </h2>
          <p className="lead" style={{ marginBottom: "20px" }}>
            {community.description} Join discussions, connect with fellow members, and RSVP to upcoming events.
          </p>

          {community.tags && (
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "16px" }}>
              {community.tags.split(",").map((t) => (
                <span key={t.trim()} className="tag">
                  #{t.trim()}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "discussions" && (
        <div style={{ marginTop: "10px" }}>
          {posts.length === 0 ? (
            <div className="empty">
              <MessageSquare size={36} style={{ color: "var(--accent)", margin: "0 auto 12px auto" }} />
              <p>No community posts shared yet.</p>
              <Link to="/feed" className="button primary">
                Explore Feed
              </Link>
            </div>
          ) : (
            <div className="photo-grid">
              {posts.map((post) => (
                <PostCard key={post.id} post={post} onOpen={setSelectedPost} />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "events" && (
        <div style={{ marginTop: "10px" }}>
          {events.length === 0 ? (
            <div className="empty">
              <CalendarDays size={36} style={{ color: "var(--accent)", margin: "0 auto 12px auto" }} />
              <p>No upcoming events currently scheduled for this group.</p>
              <Link to="/events" className="button">
                Browse all events
              </Link>
            </div>
          ) : (
            <div className="panel" style={{ padding: "10px 20px" }}>
              {events.map((evt) => (
                <div key={evt.id} className="list-row">
                  <CalendarDays size={20} />
                  <div>
                    <strong>{evt.title}</strong>
                    <p>{evt.location} · {evt.description.slice(0, 70)}...</p>
                  </div>
                  <Link to="/events" className="button" style={{ marginLeft: "auto" }}>
                    View event
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "members" && (
        <div className="panel" style={{ padding: "30px", marginTop: "10px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "800", color: "var(--text)", marginBottom: "12px" }}>
            Meet the members ({community.member_count ?? 0})
          </h2>
          <p className="lead" style={{ marginBottom: "20px" }}>
            A growing circle of makers, thinkers, and builders across {community.location || "Mumbai"}.
          </p>
          <Link to="/people" className="button primary">
            Find and connect with members →
          </Link>
        </div>
      )}

      {/* Interactive Post Modal */}
      <PostDetailModal
        post={selectedPost}
        onClose={() => setSelectedPost(null)}
        onLikeChange={(postId: number, liked: boolean, count: number) => {
          setPosts((prev) =>
            prev.map((p) =>
              p.id === postId ? { ...p, is_liked: liked, likes_count: count } : p
            )
          );
        }}
      />
    </AppShell>
  );
}
