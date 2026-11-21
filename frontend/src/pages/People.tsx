import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, CheckCircle2, LoaderCircle, MapPin, MessageSquare, Search, Sparkles, User as UserIcon, UserPlus, Users, X } from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, User, SmartPeerMatch } from "../lib/api";
import { SafeAvatar } from "../components/common/SafeImage";
import { useToast } from "../components/common/ToastContext";
import { formatApiError } from "../lib/errorUtils";

type ConnectionItem = {
  connection_id: number;
  status: string;
  created_at: string;
  is_sender: boolean;
  partner_id: number;
  partner_name: string;
  partner_avatar?: string | null;
  partner_skills: string;
  partner_location: string;
};

export default function People() {
  const toast = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [activeTab, setActiveTab] = useState<"discover" | "smart_match" | "connections">("discover");
  const [smartMatches, setSmartMatches] = useState<SmartPeerMatch[]>([]);
  const [loadingSmartMatches, setLoadingSmartMatches] = useState(false);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusMap, setStatusMap] = useState<Record<number, string>>({});

  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    loadUsers(query.trim(), page);
    if (loggedIn) {
      loadConnections();
      loadSmartMatches();
    }
  }, [page]);

  async function loadSmartMatches() {
    setLoadingSmartMatches(true);
    try {
      const res = await api.smartPeerMatches(20, 16);
      setSmartMatches(res.results);
    } catch (err) {
      console.error("Smart match load error", err);
    } finally {
      setLoadingSmartMatches(false);
    }
  }

  async function loadUsers(searchQ = "", pageNum = 1) {
    setLoading(true);
    setError("");
    try {
      const data = await api.users(searchQ, pageNum, 24);
      setUsers(data);
      // Auto-populate connection map from API response
      const sm: Record<number, string> = {};
      data.forEach((u) => {
        if (u.connection_status && u.connection_status !== "none") {
          sm[u.id] = u.connection_status;
        }
      });
      setStatusMap((prev) => ({ ...sm, ...prev }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load people");
    } finally {
      setLoading(false);
    }
  }

  async function loadConnections() {
    try {
      const conns = await api.myConnections();
      setConnections(conns);
      const sm: Record<number, string> = {};
      conns.forEach((c) => {
        sm[c.partner_id] = c.status;
      });
      setStatusMap((prev) => ({ ...prev, ...sm }));
    } catch (err) {
      console.error(err);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    loadUsers(query.trim(), 1);
  }

  async function handleConnect(userId: number) {
    if (!loggedIn) {
      toast.info("Please sign in to send connection requests.");
      return;
    }
    try {
      const res = await api.connectUser(userId);
      setStatusMap((prev) => ({ ...prev, [userId]: "pending" }));
      toast.success(res.message);
      loadConnections();
    } catch (err) {
      toast.error(formatApiError(err, "Failed to connect."));
    }
  }

  async function handleAccept(connId: number) {
    try {
      await api.acceptConnection(connId);
      toast.success("Connection accepted!");
      loadConnections();
    } catch (err) {
      toast.error(formatApiError(err, "Failed to accept."));
    }
  }

  async function handleReject(connId: number) {
    try {
      await api.rejectConnection(connId);
      toast.info("Connection request declined.");
      loadConnections();
    } catch (err) {
      toast.error(formatApiError(err, "Failed to reject."));
    }
  }

  const pendingIncoming = connections.filter((c) => c.status === "pending" && !c.is_sender);
  const acceptedFriends = connections.filter((c) => c.status === "accepted");

  return (
    <AppShell title="People">
      <div style={{ maxWidth: "1060px", margin: "0 auto" }}>
        {/* Header */}
        <section style={{ textAlign: "center", marginBottom: "28px" }}>
          <p className="eyebrow">Peer Discovery</p>
          <h1 className="page-title">Discover People &amp; Collaborators</h1>
          <p className="lead" style={{ maxWidth: "560px", margin: "0 auto" }}>
            Find peers who share your technical interests, learning goals, and domain passions across the ALIGN network.
          </p>

          {/* Tab Selector */}
          {loggedIn && (
            <div
              style={{
                display: "inline-flex",
                gap: "8px",
                background: "var(--bg-card)",
                padding: "4px",
                borderRadius: "14px",
                border: "1px solid var(--border-subtle)",
                margin: "20px auto 0 auto",
              }}
            >
              <button
                type="button"
                onClick={() => setActiveTab("discover")}
                style={{
                  padding: "8px 18px",
                  borderRadius: "10px",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "600",
                  background: activeTab === "discover" ? "var(--bg-secondary)" : "transparent",
                  color: "var(--primary-text)",
                }}
              >
                Discover Peers
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab("smart_match");
                  if (smartMatches.length === 0) loadSmartMatches();
                }}
                style={{
                  padding: "8px 18px",
                  borderRadius: "10px",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "600",
                  background: activeTab === "smart_match" ? "var(--bg-secondary)" : "transparent",
                  color: activeTab === "smart_match" ? "var(--accent-primary)" : "var(--primary-text)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <Sparkles size={14} color="var(--accent-primary)" />
                Smart AI Match
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("connections")}
                style={{
                  padding: "8px 18px",
                  borderRadius: "10px",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: "600",
                  background: activeTab === "connections" ? "var(--bg-secondary)" : "transparent",
                  color: "var(--primary-text)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                My Connections
                {pendingIncoming.length > 0 && (
                  <span
                    style={{
                      background: "var(--primary-accent)",
                      color: "#FFFFFF",
                      fontSize: "11px",
                      padding: "1px 6px",
                      borderRadius: "100px",
                    }}
                  >
                    {pendingIncoming.length}
                  </span>
                )}
              </button>
            </div>
          )}

          {/* Search Box */}
          {activeTab === "discover" && (
            <form
              onSubmit={handleSearch}
              className="search-box"
              style={{
                maxWidth: "580px",
                margin: "20px auto 0 auto",
                display: "flex",
                gap: "8px",
                background: "var(--bg-card)",
                padding: "8px",
                borderRadius: "16px",
                border: "1.5px solid var(--border-subtle)",
                boxShadow: "var(--card-shadow)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, paddingLeft: "8px" }}>
                <Search size={18} style={{ color: "var(--secondary-text)" }} />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by skill, goal, or interest (e.g. Python, AI, Design)..."
                  style={{
                    border: "none",
                    outline: "none",
                    width: "100%",
                    fontSize: "14px",
                    color: "var(--primary-text)",
                    background: "transparent",
                  }}
                />
              </div>
              <button
                type="submit"
                className="submit-button"
                style={{ width: "auto", margin: 0, padding: "10px 20px", fontWeight: "600" }}
              >
                Search
              </button>
            </form>
          )}
        </section>

        {error && (
          <div className="error-box" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: 20 }}>
            <span>{error}</span>
            <button
              onClick={() => void loadUsers()}
              style={{
                padding: "7px 18px",
                borderRadius: 8,
                background: "#EF4444",
                color: "#FFFFFF",
                border: "none",
                fontWeight: 700,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Tab 1: Discover Grid */}
        {activeTab === "discover" && (
          loading ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
                gap: "20px",
              }}
            >
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <div
                  key={n}
                  style={{
                    height: 240,
                    borderRadius: 18,
                    background: "var(--bg-card)",
                    border: "1px solid var(--border-subtle)",
                    opacity: 0.5,
                  }}
                />
              ))}
            </div>
          ) : users.length === 0 ? (
            <div className="empty-state" style={{ padding: "60px 0" }}>
              <Users size={44} style={{ color: "var(--accent-pink)", margin: "0 auto 12px auto" }} />
              <h3 style={{ color: "var(--primary-text)", margin: "0 0 6px 0" }}>No peers found matching your query</h3>
              <p style={{ color: "var(--secondary-text)", fontSize: "14px", maxWidth: "360px", margin: "0 auto" }}>
                Try searching with broader terms like "AI", "Data", "Design", or clear your filter.
              </p>
            </div>
          ) : (
            <>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
                  gap: "20px",
                }}
              >
              {users.map((u) => {
                const connStatus = statusMap[u.id] || "none";
                const isRequested = connStatus === "pending";
                const isConnected = connStatus === "accepted";

                const skillsList = (u.profile?.skills || "")
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean);
                const interestsList = (u.profile?.interests || "")
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean);

                return (
                  <div
                    key={u.id}
                    className="result-card"
                    style={{
                      padding: "24px",
                      background: "var(--bg-card)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "18px",
                      boxShadow: "0 4px 18px rgba(244, 182, 194, 0.18)",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      {/* Header */}
                      <Link
                        to={`/profile/${u.id}`}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "14px",
                          marginBottom: "14px",
                          textDecoration: "none",
                          color: "inherit",
                        }}
                        title={`View ${u.name}'s profile`}
                      >
                        <div
                          style={{
                            width: "52px",
                            height: "52px",
                            borderRadius: "50%",
                            background: "linear-gradient(135deg, var(--powder-pink) 0%, var(--primary-pink) 100%)",
                            border: "2px solid var(--border-subtle)",
                            display: "grid",
                            placeItems: "center",
                            overflow: "hidden",
                            flexShrink: 0,
                          }}
                        >
                          <SafeAvatar
                            src={u.profile?.avatar_url}
                            name={u.name}
                            size={52}
                          />
                        </div>

                        <div style={{ flex: 1, minWidth: 0 }}>
                          <h3 style={{ margin: "0 0 3px 0", fontSize: "17px", color: "var(--primary-text)", fontWeight: "700" }}>
                            {u.name}
                          </h3>
                          {u.profile?.location ? (
                            <span
                              style={{
                                fontSize: "12px",
                                color: "var(--secondary-text)",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                              }}
                            >
                              <MapPin size={12} style={{ color: "var(--accent-pink)" }} /> {u.profile.location}
                            </span>
                          ) : (
                            <span style={{ fontSize: "12px", color: "var(--secondary-text)" }}>ALIGN Community Member</span>
                          )}
                        </div>
                      </Link>

                      {/* Bio */}
                      {u.recommendation_reason && (
                        <div
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "3px 10px",
                            borderRadius: "100px",
                            background: "var(--powder-pink)",
                            border: "1px solid var(--border-subtle)",
                            fontSize: "11px",
                            fontWeight: "600",
                            color: "var(--primary-text)",
                            marginBottom: "10px",
                          }}
                        >
                          <Sparkles size={12} style={{ color: "var(--accent-pink)" }} />
                          {u.recommendation_reason}
                          {u.match_score ? ` (${Math.round(u.match_score * 100)}%)` : ""}
                        </div>
                      )}

                      {u.profile?.bio && (
                        <p
                          style={{
                            fontSize: "13px",
                            color: "var(--primary-text)",
                            lineHeight: "1.5",
                            margin: "0 0 14px 0",
                            fontStyle: "italic",
                          }}
                        >
                          "{u.profile.bio}"
                        </p>
                      )}

                      {/* Skills Chips */}
                      {skillsList.length > 0 && (
                        <div style={{ marginBottom: "12px" }}>
                          <span style={{ fontSize: "11px", color: "var(--secondary-text)", fontWeight: "600", display: "block", marginBottom: "5px" }}>
                            SKILLS & EXPERTISE
                          </span>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                            {skillsList.slice(0, 5).map((s) => (
                              <span
                                key={s}
                                style={{
                                  fontSize: "11px",
                                  padding: "2px 8px",
                                  borderRadius: "8px",
                                  background: "var(--powder-pink)",
                                  color: "var(--primary-text)",
                                  border: "1px solid var(--border-subtle)",
                                  fontWeight: "500",
                                }}
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Interests Chips */}
                      {interestsList.length > 0 && (
                        <div style={{ marginBottom: "14px" }}>
                          <span style={{ fontSize: "11px", color: "var(--secondary-text)", fontWeight: "600", display: "block", marginBottom: "5px" }}>
                            INTERESTS
                          </span>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                            {interestsList.slice(0, 4).map((item) => (
                              <span
                                key={item}
                                style={{
                                  fontSize: "11px",
                                  padding: "2px 8px",
                                  borderRadius: "8px",
                                  background: "var(--bg-secondary)",
                                  color: "var(--secondary-text)",
                                  border: "1px solid var(--border-subtle)",
                                }}
                              >
                                {item}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div style={{ display: "flex", gap: "10px", marginTop: "14px", paddingTop: "12px", borderTop: "1px solid var(--border-subtle)" }}>
                      {connStatus === "pending" && u.is_connection_sender === false && u.connection_id ? (
                        <button
                          type="button"
                          onClick={() => handleAccept(u.connection_id!)}
                          className="cta-button"
                          style={{
                            flex: 1,
                            padding: "10px",
                            fontSize: "13px",
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "6px",
                            background: "var(--primary-accent)",
                            color: "#FFFFFF",
                            fontWeight: "600",
                          }}
                        >
                          <Check size={14} /> Accept Invite
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleConnect(u.id)}
                          disabled={isRequested || isConnected}
                          className="cta-button"
                          style={{
                            flex: 1,
                            padding: "10px",
                            fontSize: "13px",
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "6px",
                            background: isConnected
                              ? "rgba(16, 185, 129, 0.2)"
                              : isRequested
                              ? "var(--bg-main)"
                              : "var(--primary-accent)",
                            color: isConnected
                              ? "var(--success-color)"
                              : isRequested
                              ? "var(--primary-text)"
                              : "#FFFFFF",
                            borderColor: isConnected
                              ? "var(--success-color)"
                              : "var(--border-subtle)",
                            fontWeight: "600",
                          }}
                        >
                          {isConnected ? (
                            <>
                              <CheckCircle2 size={14} style={{ color: "var(--success-color)" }} /> Connected
                            </>
                          ) : isRequested ? (
                            <>
                              <Check size={14} style={{ color: "var(--primary-accent)" }} /> Requested
                            </>
                          ) : (
                            <>
                              <UserPlus size={14} /> Connect
                            </>
                          )}
                        </button>
                      )}

                      <Link
                        to={`/messages?user_id=${u.id}&name=${encodeURIComponent(u.name)}`}
                        style={{
                          padding: "10px 14px",
                          borderRadius: "12px",
                          background: "var(--bg-card)",
                          border: "1.5px solid var(--border-subtle)",
                          color: "var(--primary-text)",
                          fontSize: "13px",
                          fontWeight: "600",
                          textDecoration: "none",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        <MessageSquare size={14} style={{ color: "var(--primary-accent)" }} /> Message
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Pagination Controls */}
            {users.length > 0 && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  gap: "16px",
                  marginTop: "32px",
                }}
              >
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  style={{
                    padding: "8px 18px",
                    borderRadius: "10px",
                    border: "1px solid var(--border-subtle)",
                    background: page <= 1 ? "var(--bg-secondary)" : "var(--bg-card)",
                    color: page <= 1 ? "var(--secondary-text)" : "var(--primary-text)",
                    fontSize: "13px",
                    fontWeight: "600",
                    cursor: page <= 1 ? "not-allowed" : "pointer",
                  }}
                >
                  Previous
                </button>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--primary-text)" }}>
                  Page {page}
                </span>
                <button
                  type="button"
                  disabled={users.length < 24}
                  onClick={() => setPage((p) => p + 1)}
                  style={{
                    padding: "8px 18px",
                    borderRadius: "10px",
                    border: "1px solid var(--border-subtle)",
                    background: users.length < 24 ? "var(--bg-secondary)" : "var(--bg-card)",
                    color: users.length < 24 ? "var(--secondary-text)" : "var(--primary-text)",
                    fontSize: "13px",
                    fontWeight: "600",
                    cursor: users.length < 24 ? "not-allowed" : "pointer",
                  }}
                >
                  Next
                </button>
              </div>
            )}
          </>
        ))}

        {/* Tab: Smart AI Matching */}
        {activeTab === "smart_match" && (
          loadingSmartMatches ? (
            <div className="empty-state" style={{ padding: "60px 0", textAlign: "center" }}>
              <LoaderCircle className="spin" size={36} style={{ color: "var(--accent-primary)", margin: "0 auto 12px auto" }} />
              <p style={{ color: "var(--secondary-text)" }}>Computing multi-dimensional vector compatibility...</p>
            </div>
          ) : smartMatches.length === 0 ? (
            <div className="empty-state" style={{ padding: "60px 0", textAlign: "center" }}>
              <Sparkles size={44} style={{ color: "var(--accent-primary)", margin: "0 auto 12px auto" }} />
              <h3 style={{ color: "var(--primary-text)", margin: "0 0 6px 0" }}>No High-Compatibility Matches Found</h3>
              <p style={{ color: "var(--secondary-text)", fontSize: "14px", maxWidth: "420px", margin: "0 auto" }}>
                Add more skills, interests, and learning goals to your profile to help the matching algorithm find your ideal peers.
              </p>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: "20px" }}>
              {smartMatches.map((m) => {
                const connStatus = statusMap[m.user_id] || m.connection_status || "none";
                const isRequested = connStatus === "pending";
                const isConnected = connStatus === "accepted";

                return (
                  <div
                    key={m.user_id}
                    style={{
                      padding: "22px",
                      background: "var(--bg-card)",
                      border: "1px solid var(--border-color)",
                      borderRadius: "16px",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      {/* Top info row */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "14px" }}>
                        <Link
                          to={`/profile/${m.user_id}`}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "12px",
                            textDecoration: "none",
                            color: "inherit",
                          }}
                          title={`View ${m.name}'s profile`}
                        >
                          <div
                            style={{
                              width: "48px",
                              height: "48px",
                              borderRadius: "50%",
                              background: "rgba(83,101,245,0.1)",
                              border: "1px solid var(--border-color)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "18px",
                              fontWeight: "700",
                              color: "var(--accent-primary)",
                            }}
                          >
                            {m.name.slice(0, 1).toUpperCase()}
                          </div>
                          <div>
                            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: "700", color: "var(--text-primary)" }}>
                              {m.name}
                            </h3>
                            <div style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "4px" }}>
                              <MapPin size={12} /> {m.location || "Location not set"}
                            </div>
                          </div>
                        </Link>

                        {/* Compatibility Score Badge */}
                        <div
                          style={{
                            padding: "6px 12px",
                            borderRadius: "10px",
                            background: "rgba(83,101,245,0.1)",
                            border: "1px solid rgba(83,101,245,0.2)",
                            textAlign: "center",
                          }}
                        >
                          <div style={{ fontSize: "16px", fontWeight: "800", color: "var(--accent-primary)" }}>
                            {Math.round(m.compatibility.overall_percentage)}%
                          </div>
                          <div style={{ fontSize: "10px", fontWeight: "700", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                            MATCH
                          </div>
                        </div>
                      </div>

                      {/* AI Explanation Banner */}
                      <div
                        style={{
                          background: "var(--bg-secondary)",
                          border: "1px solid var(--border-color)",
                          borderRadius: "10px",
                          padding: "10px 12px",
                          marginBottom: "14px",
                          fontSize: "12px",
                          lineHeight: "1.4",
                          color: "var(--text-secondary)",
                          display: "flex",
                          alignItems: "flex-start",
                          gap: "8px",
                        }}
                      >
                        <Sparkles size={16} color="var(--accent-primary)" style={{ flexShrink: 0, marginTop: "2px" }} />
                        <span>{m.compatibility.explanation}</span>
                      </div>

                      {/* Dimension Progress Breakdown */}
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "16px" }}>
                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "3px" }}>
                            <span>Semantic Intent</span>
                            <span>{Math.round(m.compatibility.semantic_similarity)}%</span>
                          </div>
                          <div style={{ width: "100%", height: "4px", background: "var(--border-color)", borderRadius: "2px", overflow: "hidden" }}>
                            <div style={{ width: `${m.compatibility.semantic_similarity}%`, height: "100%", background: "var(--accent-primary)" }} />
                          </div>
                        </div>

                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "3px" }}>
                            <span>Skill Synergy</span>
                            <span>{Math.round(m.compatibility.skill_synergy)}%</span>
                          </div>
                          <div style={{ width: "100%", height: "4px", background: "var(--border-color)", borderRadius: "2px", overflow: "hidden" }}>
                            <div style={{ width: `${m.compatibility.skill_synergy}%`, height: "100%", background: "#10B981" }} />
                          </div>
                        </div>

                        <div>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "3px" }}>
                            <span>Goal Alignment</span>
                            <span>{Math.round(m.compatibility.shared_goals)}%</span>
                          </div>
                          <div style={{ width: "100%", height: "4px", background: "var(--border-color)", borderRadius: "2px", overflow: "hidden" }}>
                            <div style={{ width: `${m.compatibility.shared_goals}%`, height: "100%", background: "#8B5CF6" }} />
                          </div>
                        </div>
                      </div>

                      {/* Common skills chips */}
                      {m.compatibility.shared_skills && m.compatibility.shared_skills.length > 0 && (
                        <div style={{ marginBottom: "14px" }}>
                          <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "var(--text-secondary)", marginBottom: "6px" }}>
                            Shared Skills:
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
                            {m.compatibility.shared_skills.map((s: string, idx: number) => (
                              <span
                                key={idx}
                                style={{
                                  fontSize: "11px",
                                  padding: "2px 7px",
                                  borderRadius: "4px",
                                  background: "rgba(16,185,129,0.1)",
                                  color: "#10B981",
                                  fontWeight: "600",
                                }}
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: "flex", gap: "8px", paddingTop: "12px", borderTop: "1px solid var(--border-color)" }}>
                      <button
                        onClick={() => handleConnect(m.user_id)}
                        disabled={isRequested || isConnected}
                        style={{
                          flex: 1,
                          padding: "8px 12px",
                          borderRadius: "8px",
                          border: "none",
                          background: isConnected
                            ? "#10B981"
                            : isRequested
                            ? "var(--bg-secondary)"
                            : "var(--accent-primary)",
                          color: isRequested ? "var(--text-secondary)" : "#fff",
                          fontWeight: "600",
                          fontSize: "12px",
                          cursor: isRequested || isConnected ? "default" : "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "6px",
                        }}
                      >
                        {isConnected ? (
                          <>
                            <CheckCircle2 size={13} /> Connected
                          </>
                        ) : isRequested ? (
                          <>
                            <Check size={13} /> Requested
                          </>
                        ) : (
                          <>
                            <UserPlus size={13} /> Connect
                          </>
                        )}
                      </button>

                      <Link
                        to={`/messages?user_id=${m.user_id}&name=${encodeURIComponent(m.name)}`}
                        style={{
                          padding: "8px 12px",
                          borderRadius: "8px",
                          background: "var(--bg-secondary)",
                          border: "1px solid var(--border-color)",
                          color: "var(--text-primary)",
                          fontSize: "12px",
                          fontWeight: "600",
                          textDecoration: "none",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        <MessageSquare size={13} color="var(--accent-primary)" /> Message
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )
        )}

        {/* Tab 2: My Connections */}
        {activeTab === "connections" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            {/* Incoming Requests */}
            {pendingIncoming.length > 0 && (
              <div>
                <h3 style={{ fontSize: "18px", color: "var(--primary-text)", marginBottom: "12px", fontWeight: "700" }}>
                  Pending Requests ({pendingIncoming.length})
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {pendingIncoming.map((c) => (
                    <div
                      key={c.connection_id}
                      style={{
                        padding: "16px 20px",
                        background: "var(--bg-card)",
                        border: "1.5px solid var(--border-subtle)",
                        borderRadius: "16px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        flexWrap: "wrap",
                        gap: "12px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <div
                          style={{
                            width: "44px",
                            height: "44px",
                            borderRadius: "50%",
                            background: "var(--powder-pink)",
                            display: "grid",
                            placeItems: "center",
                          }}
                        >
                          <UserIcon size={20} style={{ color: "var(--primary-text)" }} />
                        </div>
                        <div>
                          <h4 style={{ margin: 0, fontSize: "15px", color: "var(--primary-text)", fontWeight: "700" }}>
                            {c.partner_name}
                          </h4>
                          <span style={{ fontSize: "12px", color: "var(--secondary-text)" }}>
                            {c.partner_location || "ALIGN Member"} {c.partner_skills ? `· ${c.partner_skills}` : ""}
                          </span>
                        </div>
                      </div>

                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                          type="button"
                          onClick={() => handleAccept(c.connection_id)}
                          className="cta-button"
                          style={{ padding: "8px 14px", fontSize: "12px", fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "4px" }}
                        >
                          <Check size={14} /> Accept
                        </button>
                        <button
                          type="button"
                          onClick={() => handleReject(c.connection_id)}
                          style={{
                            padding: "8px 14px",
                            borderRadius: "10px",
                            background: "transparent",
                            border: "1px solid var(--border-subtle)",
                            color: "var(--error)",
                            fontSize: "12px",
                            cursor: "pointer",
                            fontWeight: "600",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <X size={14} /> Decline
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Accepted Connections */}
            <div>
              <h3 style={{ fontSize: "18px", color: "var(--primary-text)", marginBottom: "12px", fontWeight: "700" }}>
                Connected Peers ({acceptedFriends.length})
              </h3>
              {acceptedFriends.length === 0 ? (
                <div className="empty-state" style={{ padding: "40px 0" }}>
                  <Users size={36} style={{ color: "var(--accent-pink)", margin: "0 auto 8px auto" }} />
                  <p style={{ color: "var(--secondary-text)", fontSize: "14px" }}>
                    No accepted connections yet. Explore peers in the Discover tab to connect!
                  </p>
                </div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "16px" }}>
                  {acceptedFriends.map((c) => (
                    <div
                      key={c.connection_id}
                      style={{
                        padding: "16px",
                        background: "var(--bg-card)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "16px",
                        boxShadow: "var(--shadow-card)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div
                          style={{
                            width: "40px",
                            height: "40px",
                            borderRadius: "50%",
                            background: "var(--powder-pink)",
                            display: "grid",
                            placeItems: "center",
                          }}
                        >
                          <UserIcon size={18} style={{ color: "var(--primary-text)" }} />
                        </div>
                        <div>
                          <h4 style={{ margin: 0, fontSize: "14px", color: "var(--primary-text)", fontWeight: "700" }}>
                            {c.partner_name}
                          </h4>
                          <span style={{ fontSize: "11px", color: "var(--secondary-text)" }}>Connected</span>
                        </div>
                      </div>

                      <Link
                        to={`/messages?user_id=${c.partner_id}&name=${encodeURIComponent(c.partner_name)}`}
                        style={{
                          padding: "6px 12px",
                          borderRadius: "8px",
                          background: "var(--powder-pink)",
                          color: "var(--primary-text)",
                          fontSize: "12px",
                          fontWeight: "600",
                          textDecoration: "none",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        <MessageSquare size={13} /> Chat
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
