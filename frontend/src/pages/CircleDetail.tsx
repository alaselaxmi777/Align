import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Users,
  MessageSquare,
  Calendar,
  Sparkles,
  Send,
  PlusCircle,
  MapPin,
  Clock,
  ShieldCheck,
  UserCheck,
  UserPlus,
  Share2,
} from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { SafeAvatar } from "../components/common/SafeImage";
import {
  api,
  InterestCircleItem,
  CircleDiscussionItem,
  CircleReplyItem,
  CircleActivityItem,
} from "../lib/api";

export default function CircleDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const circleId = Number(id);

  const [circle, setCircle] = useState<InterestCircleItem | null>(null);
  const [discussions, setDiscussions] = useState<CircleDiscussionItem[]>([]);
  const [activities, setActivities] = useState<CircleActivityItem[]>([]);
  const [activeTab, setActiveTab] = useState<"discussions" | "activities" | "members">("discussions");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");

  // New discussion modal / state
  const [showNewDiscussion, setShowNewDiscussion] = useState(false);
  const [discTitle, setDiscTitle] = useState("");
  const [discContent, setDiscContent] = useState("");

  // Replies state: map discussionId -> list of replies
  const [repliesMap, setRepliesMap] = useState<Record<number, CircleReplyItem[]>>({});
  const [replyInputMap, setReplyInputMap] = useState<Record<number, string>>({});
  const [loadingReplies, setLoadingReplies] = useState<Record<number, boolean>>({});

  // New activity modal / state
  const [showNewActivity, setShowNewActivity] = useState(false);
  const [actTitle, setActTitle] = useState("");
  const [actDesc, setActDesc] = useState("");
  const [actType, setActType] = useState("hack_session");
  const [actDate, setActDate] = useState("");
  const [actLocation, setActLocation] = useState("");

  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    if (!circleId) return;
    loadData();
  }, [circleId]);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [c, d, a] = await Promise.all([
        api.circleDetails(circleId),
        api.circleDiscussions(circleId),
        api.circleActivities(circleId),
      ]);
      setCircle(c);
      setDiscussions(d);
      setActivities(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load circle details");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleMembership() {
    if (!circle) return;
    if (!loggedIn) {
      navigate("/login");
      return;
    }
    setActionLoading(true);
    try {
      if (circle.is_member) {
        await api.leaveCircle(circle.id);
      } else {
        await api.joinCircle(circle.id);
      }
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleCreateDiscussion(e: React.FormEvent) {
    e.preventDefault();
    if (!discTitle.trim() || !discContent.trim()) return;
    try {
      await api.createCircleDiscussion(circleId, {
        title: discTitle.trim(),
        content: discContent.trim(),
      });
      setDiscTitle("");
      setDiscContent("");
      setShowNewDiscussion(false);
      const d = await api.circleDiscussions(circleId);
      setDiscussions(d);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to post discussion");
    }
  }

  async function toggleReplies(discussionId: number) {
    if (repliesMap[discussionId]) {
      // already loaded, could toggle collapsed if desired
      return;
    }
    setLoadingReplies((prev) => ({ ...prev, [discussionId]: true }));
    try {
      const reps = await api.circleReplies(circleId, discussionId);
      setRepliesMap((prev) => ({ ...prev, [discussionId]: reps }));
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingReplies((prev) => ({ ...prev, [discussionId]: false }));
    }
  }

  async function handlePostReply(discussionId: number) {
    const text = replyInputMap[discussionId]?.trim();
    if (!text) return;
    try {
      const newRep = await api.postCircleReply(circleId, discussionId, text);
      setRepliesMap((prev) => ({
        ...prev,
        [discussionId]: [...(prev[discussionId] || []), newRep],
      }));
      setReplyInputMap((prev) => ({ ...prev, [discussionId]: "" }));
      // bump replies_count in discussion item
      setDiscussions((prev) =>
        prev.map((d) =>
          d.id === discussionId ? { ...d, replies_count: d.replies_count + 1 } : d
        )
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to post reply");
    }
  }

  async function handleCreateActivity(e: React.FormEvent) {
    e.preventDefault();
    if (!actTitle.trim() || !actDate) return;
    try {
      await api.scheduleCircleActivity(circleId, {
        title: actTitle.trim(),
        description: actDesc.trim(),
        activity_type: actType,
        scheduled_at: new Date(actDate).toISOString(),
        location_or_link: actLocation.trim() || "Virtual / Discord Room",
      });
      setActTitle("");
      setActDesc("");
      setActDate("");
      setActLocation("");
      setShowNewActivity(false);
      const acts = await api.circleActivities(circleId);
      setActivities(acts);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to schedule activity");
    }
  }

  if (loading) {
    return (
      <AppShell title="Interest Circle">
        <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--text-secondary)" }}>
          <div className="spinner" style={{ margin: "0 auto 16px" }} />
          <p>Loading circle details...</p>
        </div>
      </AppShell>
    );
  }

  if (error || !circle) {
    return (
      <AppShell title="Interest Circle">
        <div style={{ maxWidth: 600, margin: "60px auto", padding: 24, textAlign: "center" }}>
          <p style={{ color: "#EF4444", marginBottom: 16 }}>{error || "Circle not found"}</p>
          <Link to="/circles" className="btn btn-secondary">
            <ArrowLeft size={16} /> Back to Circles
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title={circle.name}>
      <div style={{ maxWidth: 1040, margin: "0 auto", padding: "20px 16px 80px" }}>
        {/* Back Link */}
        <Link
          to="/circles"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 14,
            fontWeight: 500,
            color: "var(--text-secondary)",
            marginBottom: 20,
            textDecoration: "none",
          }}
        >
          <ArrowLeft size={16} /> Back to Interest Circles
        </Link>

        {/* Header Hero Card */}
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-color)",
            borderRadius: 16,
            padding: 24,
            marginBottom: 24,
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", gap: 20, justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ flex: "1 1 500px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                <span
                  style={{
                    fontSize: 11,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    fontWeight: 700,
                    color: "var(--accent-primary)",
                    background: "rgba(83, 101, 245, 0.1)",
                    padding: "3px 8px",
                    borderRadius: 6,
                  }}
                >
                  {circle.category}
                </span>
                <span
                  style={{
                    fontSize: 12,
                    color: "var(--text-secondary)",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <Users size={14} />
                  {circle.member_count} / {circle.max_members} members
                </span>
              </div>

              <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
                {circle.name}
              </h1>
              <p style={{ fontSize: 15, color: "var(--text-secondary)", margin: "0 0 16px", lineHeight: 1.5 }}>
                {circle.tagline || circle.description}
              </p>

              {/* Tags */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16 }}>
                {circle.tags.map((tag, idx) => (
                  <span
                    key={idx}
                    style={{
                      fontSize: 12,
                      padding: "3px 10px",
                      borderRadius: 999,
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border-color)",
                      color: "var(--text-secondary)",
                    }}
                  >
                    #{tag}
                  </span>
                ))}
              </div>

              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                Organized by <strong style={{ color: "var(--text-primary)" }}>{circle.creator_name}</strong>
              </div>
            </div>

            {/* Action buttons */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 160 }}>
              <button
                onClick={handleToggleMembership}
                disabled={actionLoading}
                className="btn"
                style={{
                  background: circle.is_member ? "var(--bg-secondary)" : "var(--accent-primary)",
                  color: circle.is_member ? "var(--text-primary)" : "#fff",
                  border: circle.is_member ? "1px solid var(--border-color)" : "none",
                  fontWeight: 600,
                  padding: "10px 18px",
                  borderRadius: 10,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                }}
              >
                {circle.is_member ? (
                  <>
                    <UserCheck size={16} /> Joined Circle
                  </>
                ) : (
                  <>
                    <UserPlus size={16} /> Join Circle
                  </>
                )}
              </button>

              <button
                onClick={() => {
                  navigator.clipboard.writeText(window.location.href);
                  alert("Circle link copied to clipboard!");
                }}
                className="btn btn-secondary"
                style={{
                  padding: "9px 16px",
                  borderRadius: 10,
                  fontSize: 13,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                }}
              >
                <Share2 size={15} /> Share Circle
              </button>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: "flex",
            gap: 8,
            borderBottom: "1px solid var(--border-color)",
            marginBottom: 24,
          }}
        >
          <button
            onClick={() => setActiveTab("discussions")}
            style={{
              padding: "10px 18px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "discussions" ? "2px solid var(--accent-primary)" : "2px solid transparent",
              color: activeTab === "discussions" ? "var(--accent-primary)" : "var(--text-secondary)",
              fontWeight: 600,
              fontSize: 14,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <MessageSquare size={16} />
            Discussions ({circle.discussions_count})
          </button>

          <button
            onClick={() => setActiveTab("activities")}
            style={{
              padding: "10px 18px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "activities" ? "2px solid var(--accent-primary)" : "2px solid transparent",
              color: activeTab === "activities" ? "var(--accent-primary)" : "var(--text-secondary)",
              fontWeight: 600,
              fontSize: 14,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <Calendar size={16} />
            Activities ({circle.activities_count})
          </button>

          <button
            onClick={() => setActiveTab("members")}
            style={{
              padding: "10px 18px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "members" ? "2px solid var(--accent-primary)" : "2px solid transparent",
              color: activeTab === "members" ? "var(--accent-primary)" : "var(--text-secondary)",
              fontWeight: 600,
              fontSize: 14,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <Users size={16} />
            Members ({circle.member_count})
          </button>
        </div>

        {/* TAB 1: DISCUSSIONS */}
        {activeTab === "discussions" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                Circle Discussions
              </h2>
              {circle.is_member && (
                <button
                  onClick={() => setShowNewDiscussion(true)}
                  className="btn"
                  style={{
                    background: "var(--accent-primary)",
                    color: "#fff",
                    borderRadius: 8,
                    padding: "8px 14px",
                    fontSize: 13,
                    fontWeight: 600,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    cursor: "pointer",
                    border: "none",
                  }}
                >
                  <PlusCircle size={15} /> Start Discussion
                </button>
              )}
            </div>

            {/* Discussion creation modal */}
            {showNewDiscussion && (
              <form
                onSubmit={handleCreateDiscussion}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 12,
                  padding: 18,
                  marginBottom: 20,
                }}
              >
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 12px", color: "var(--text-primary)" }}>
                  Start a New Discussion Thread
                </h3>
                <input
                  type="text"
                  placeholder="Thread topic or question..."
                  value={discTitle}
                  onChange={(e) => setDiscTitle(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 14,
                    marginBottom: 10,
                  }}
                  required
                />
                <textarea
                  placeholder="Share details, context, code snippets, or thoughts..."
                  rows={4}
                  value={discContent}
                  onChange={(e) => setDiscContent(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 14,
                    marginBottom: 12,
                    resize: "vertical",
                  }}
                  required
                />
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button
                    type="button"
                    onClick={() => setShowNewDiscussion(false)}
                    className="btn btn-secondary"
                    style={{ padding: "7px 14px", fontSize: 13 }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn"
                    style={{
                      background: "var(--accent-primary)",
                      color: "#fff",
                      padding: "7px 16px",
                      fontSize: 13,
                      fontWeight: 600,
                      border: "none",
                      borderRadius: 8,
                    }}
                  >
                    Post Discussion
                  </button>
                </div>
              </form>
            )}

            {discussions.length === 0 ? (
              <div
                style={{
                  background: "var(--bg-card)",
                  border: "1px dashed var(--border-color)",
                  borderRadius: 12,
                  padding: "40px 20px",
                  textAlign: "center",
                  color: "var(--text-secondary)",
                }}
              >
                <MessageSquare size={36} style={{ margin: "0 auto 12px", opacity: 0.5 }} />
                <p style={{ margin: "0 0 8px", fontWeight: 600 }}>No discussions yet</p>
                <p style={{ margin: 0, fontSize: 13 }}>
                  {circle.is_member
                    ? "Start the first conversation with your circle peers!"
                    : "Join this circle to participate in conversations and activities."}
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {discussions.map((d) => {
                  const replies = repliesMap[d.id] || [];
                  const isLoadingReps = loadingReplies[d.id];
                  const hasLoadedReps = Boolean(repliesMap[d.id]);

                  return (
                    <div
                      key={d.id}
                      style={{
                        background: "var(--bg-card)",
                        border: "1px solid var(--border-color)",
                        borderRadius: 12,
                        padding: 18,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                        <h4 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                          {d.title}
                        </h4>
                        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                          {new Date(d.created_at).toLocaleDateString()}
                        </span>
                      </div>

                      <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>
                        Started by <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{d.author_name}</span>
                      </div>

                      <p style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.5, margin: "0 0 14px", whiteSpace: "pre-wrap" }}>
                        {d.content}
                      </p>

                      {/* Reply summary toggle */}
                      <div style={{ display: "flex", alignItems: "center", gap: 12, paddingTop: 10, borderTop: "1px solid var(--border-color)" }}>
                        <button
                          onClick={() => toggleReplies(d.id)}
                          style={{
                            background: "none",
                            border: "none",
                            color: "var(--accent-primary)",
                            fontSize: 13,
                            fontWeight: 600,
                            cursor: "pointer",
                            padding: 0,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 5,
                          }}
                        >
                          <MessageSquare size={14} />
                          {hasLoadedReps ? `Replies (${replies.length})` : `${d.replies_count} Replies`}
                        </button>
                      </div>

                      {/* Loaded Replies List */}
                      {hasLoadedReps && (
                        <div style={{ marginTop: 14, paddingLeft: 12, borderLeft: "2px solid var(--border-color)" }}>
                          {replies.map((r) => (
                            <div key={r.id} style={{ marginBottom: 12 }}>
                              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                                  {r.author_name}
                                </span>
                                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                                  {new Date(r.created_at).toLocaleDateString()}
                                </span>
                              </div>
                              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, whiteSpace: "pre-wrap" }}>
                                {r.content}
                              </p>
                            </div>
                          ))}

                          {/* Post Reply Input */}
                          {circle.is_member && (
                            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                              <input
                                type="text"
                                placeholder="Write a reply..."
                                value={replyInputMap[d.id] || ""}
                                onChange={(e) =>
                                  setReplyInputMap((prev) => ({ ...prev, [d.id]: e.target.value }))
                                }
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") handlePostReply(d.id);
                                }}
                                style={{
                                  flex: 1,
                                  padding: "7px 12px",
                                  borderRadius: 8,
                                  border: "1px solid var(--border-color)",
                                  background: "var(--bg-secondary)",
                                  color: "var(--text-primary)",
                                  fontSize: 13,
                                }}
                              />
                              <button
                                onClick={() => handlePostReply(d.id)}
                                style={{
                                  background: "var(--accent-primary)",
                                  color: "#fff",
                                  border: "none",
                                  borderRadius: 8,
                                  padding: "7px 14px",
                                  cursor: "pointer",
                                }}
                              >
                                <Send size={14} />
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                      {isLoadingReps && (
                        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 8 }}>Loading replies...</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: ACTIVITIES */}
        {activeTab === "activities" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                Scheduled Circle Activities
              </h2>
              {circle.is_member && (
                <button
                  onClick={() => setShowNewActivity(true)}
                  className="btn"
                  style={{
                    background: "var(--accent-primary)",
                    color: "#fff",
                    borderRadius: 8,
                    padding: "8px 14px",
                    fontSize: 13,
                    fontWeight: 600,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    cursor: "pointer",
                    border: "none",
                  }}
                >
                  <PlusCircle size={15} /> Schedule Activity
                </button>
              )}
            </div>

            {/* Schedule Activity Form */}
            {showNewActivity && (
              <form
                onSubmit={handleCreateActivity}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 12,
                  padding: 18,
                  marginBottom: 20,
                }}
              >
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: "0 0 12px", color: "var(--text-primary)" }}>
                  Schedule Group Session / Activity
                </h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                  <input
                    type="text"
                    placeholder="Activity Title (e.g. Weekly Code Review)"
                    value={actTitle}
                    onChange={(e) => setActTitle(e.target.value)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 13,
                    }}
                    required
                  />
                  <select
                    value={actType}
                    onChange={(e) => setActType(e.target.value)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 13,
                    }}
                  >
                    <option value="hack_session">Hack Session</option>
                    <option value="study_group">Study Group</option>
                    <option value="paper_reading">Paper Reading</option>
                    <option value="project_demo">Project Demo</option>
                    <option value="casual_meetup">Casual Meetup</option>
                  </select>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                  <input
                    type="datetime-local"
                    value={actDate}
                    onChange={(e) => setActDate(e.target.value)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 13,
                    }}
                    required
                  />
                  <input
                    type="text"
                    placeholder="Location or Virtual Link (e.g. Google Meet URL)"
                    value={actLocation}
                    onChange={(e) => setActLocation(e.target.value)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 13,
                    }}
                  />
                </div>
                <textarea
                  placeholder="Activity agenda, prerequisites, or preparation notes..."
                  rows={3}
                  value={actDesc}
                  onChange={(e) => setActDesc(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                    marginBottom: 12,
                  }}
                />
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button
                    type="button"
                    onClick={() => setShowNewActivity(false)}
                    className="btn btn-secondary"
                    style={{ padding: "7px 14px", fontSize: 13 }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn"
                    style={{
                      background: "var(--accent-primary)",
                      color: "#fff",
                      padding: "7px 16px",
                      fontSize: 13,
                      fontWeight: 600,
                      border: "none",
                      borderRadius: 8,
                    }}
                  >
                    Save Activity
                  </button>
                </div>
              </form>
            )}

            {activities.length === 0 ? (
              <div
                style={{
                  background: "var(--bg-card)",
                  border: "1px dashed var(--border-color)",
                  borderRadius: 12,
                  padding: "40px 20px",
                  textAlign: "center",
                  color: "var(--text-secondary)",
                }}
              >
                <Calendar size={36} style={{ margin: "0 auto 12px", opacity: 0.5 }} />
                <p style={{ margin: "0 0 8px", fontWeight: 600 }}>No activities scheduled</p>
                <p style={{ margin: 0, fontSize: 13 }}>Plan a hack sprint or study session with circle peers.</p>
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 14 }}>
                {activities.map((a) => (
                  <div
                    key={a.id}
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border-color)",
                      borderRadius: 12,
                      padding: 16,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                      <span
                        style={{
                          fontSize: 11,
                          textTransform: "uppercase",
                          fontWeight: 700,
                          color: "var(--accent-primary)",
                          background: "rgba(83, 101, 245, 0.1)",
                          padding: "3px 8px",
                          borderRadius: 6,
                        }}
                      >
                        {a.activity_type.replace("_", " ")}
                      </span>
                    </div>

                    <h4 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
                      {a.title}
                    </h4>

                    {a.description && (
                      <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px", lineHeight: 1.4 }}>
                        {a.description}
                      </p>
                    )}

                    <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <Clock size={14} color="var(--accent-primary)" />
                        {new Date(a.scheduled_at).toLocaleString()}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <MapPin size={14} color="var(--accent-primary)" />
                        {a.location_or_link}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: MEMBERS */}
        {activeTab === "members" && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 6px", color: "var(--text-primary)" }}>
                Circle Roster ({circle.members?.length || circle.member_count} Members)
              </h2>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                High-density micro-community limited to {circle.max_members} passionate builders.
              </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
              {circle.members && circle.members.length > 0 ? (
                circle.members.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border-color)",
                      borderRadius: 12,
                      padding: 16,
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                    }}
                  >
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: "50%",
                        background: "var(--bg-secondary)",
                        border: "1px solid var(--border-color)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 16,
                        fontWeight: 700,
                        color: "var(--accent-primary)",
                        overflow: "hidden",
                      }}
                    >
                      <SafeAvatar
                        src={m.avatar_url}
                        name={m.name}
                        size={40}
                      />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <h4 style={{ fontSize: 14, fontWeight: 600, margin: 0, color: "var(--text-primary)" }}>
                          {m.name}
                        </h4>
                        {m.role === "admin" && (
                          <ShieldCheck size={14} color="var(--accent-primary)" />
                        )}
                      </div>
                      <p
                        style={{
                          fontSize: 12,
                          color: "var(--text-secondary)",
                          margin: "2px 0 0",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {m.skills || "Builder / Collaborator"}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>
                  No members list available.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
