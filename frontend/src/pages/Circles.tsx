import { FormEvent, useEffect, useState } from "react";
import {
  Calendar,
  CheckCircle,
  Hash,
  Layers,
  LoaderCircle,
  Lock,
  MessageSquare,
  Plus,
  Search,
  Sparkles,
  Users,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import { api, InterestCircleItem } from "../lib/api";

const CATEGORIES = ["All", "Technology", "AI & Robotics", "Design & UX", "Startups", "Outdoors & Fitness", "Creative Writing"];

export default function Circles() {
  const [circles, setCircles] = useState<InterestCircleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form
  const [name, setName] = useState("");
  const [tagline, setTagline] = useState("");
  const [desc, setDesc] = useState("");
  const [category, setCategory] = useState("Technology");
  const [tags, setTags] = useState("");
  const [maxMembers, setMaxMembers] = useState(25);
  const [isPrivate, setIsPrivate] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    void loadCircles();
  }, [search, activeCategory]);

  async function loadCircles() {
    setLoading(true);
    try {
      const cat = activeCategory === "All" ? "" : activeCategory;
      const data = await api.circles(search, cat);
      setCircles(data);
    } catch {
      setCircles([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateCircle(e: FormEvent) {
    e.preventDefault();
    if (!name || !desc) return;
    setSubmitting(true);
    try {
      const newCircle = await api.createCircle({
        name,
        tagline,
        description: desc,
        category,
        tags,
        max_members: maxMembers,
        is_private: isPrivate,
      });
      setShowCreateModal(false);
      setName("");
      setTagline("");
      setDesc("");
      setTags("");
      setCircles([newCircle, ...circles]);
      navigate(`/circles/${newCircle.id}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create Circle.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleJoin(circle: InterestCircleItem) {
    try {
      if (circle.is_member) {
        await api.leaveCircle(circle.id);
      } else {
        await api.joinCircle(circle.id);
      }
      void loadCircles();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update membership.");
    }
  }

  return (
    <AppShell>
      <div style={{ maxWidth: "1140px", margin: "0 auto", padding: "16px 8px 60px" }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "16px",
            marginBottom: "24px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
              <Layers size={26} style={{ color: "var(--primary-accent)" }} />
              <h1 style={{ fontSize: "24px", fontWeight: "800", color: "var(--primary-text)", margin: 0 }}>
                Interest Circles
              </h1>
            </div>
            <p style={{ color: "var(--secondary-text)", fontSize: "14px", margin: 0 }}>
              Small, focused micro-groups (max 25 members) for deep discussions, pair projects, and weekly activities.
            </p>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="button primary"
            style={{ borderRadius: "999px", padding: "10px 20px" }}
          >
            <Plus size={16} />
            <span>Create Interest Circle</span>
          </button>
        </div>

        {/* Search & Categories */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "24px" }}>
          <div style={{ position: "relative" }}>
            <Search
              size={18}
              style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--muted)" }}
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search circles by topic, tags, or focus..."
              className="search"
              style={{ width: "100%", paddingLeft: "42px", height: "44px", borderRadius: "14px" }}
            />
          </div>

          <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "4px" }}>
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                style={{
                  padding: "6px 14px",
                  borderRadius: "999px",
                  fontSize: "13px",
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                  cursor: "pointer",
                  background: activeCategory === cat ? "var(--primary-accent)" : "var(--card-bg)",
                  color: activeCategory === cat ? "#FFFFFF" : "var(--secondary-text)",
                  border: "1px solid",
                  borderColor: activeCategory === cat ? "var(--primary-accent)" : "var(--border-subtle)",
                }}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Circles Grid */}
        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "80px 0" }}>
            <LoaderCircle className="spin" size={36} style={{ color: "var(--primary-accent)" }} />
          </div>
        ) : circles.length === 0 ? (
          <div className="empty-state card" style={{ padding: "60px 20px", textAlign: "center", borderRadius: "18px" }}>
            <Layers size={44} style={{ color: "var(--secondary-text)", margin: "0 auto 12px" }} />
            <h3 style={{ color: "var(--primary-text)", margin: "0 0 6px 0" }}>No Interest Circles Found</h3>
            <p style={{ color: "var(--secondary-text)", maxWidth: "420px", margin: "0 auto 16px" }}>
              Be the first to create an Interest Circle around your favorite topic, framework, or hobby!
            </p>
            <button className="button primary" onClick={() => setShowCreateModal(true)}>
              Start a Circle
            </button>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
              gap: "18px",
            }}
          >
            {circles.map((c) => (
              <article
                key={c.id}
                className="card"
                style={{
                  borderRadius: "18px",
                  padding: "20px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  transition: "transform 0.2s ease, box-shadow 0.2s ease",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px", marginBottom: "8px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--primary-accent)", textTransform: "uppercase" }}>
                      {c.category}
                    </div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: "999px",
                        background: c.member_count >= c.max_members ? "rgba(239, 68, 68, 0.12)" : "rgba(16, 185, 129, 0.12)",
                        color: c.member_count >= c.max_members ? "#EF4444" : "#10B981",
                      }}
                    >
                      <Users size={12} />
                      <span>{c.member_count} / {c.max_members} members</span>
                    </div>
                  </div>

                  <h3
                    onClick={() => navigate(`/circles/${c.id}`)}
                    style={{ fontSize: "17px", fontWeight: "800", color: "var(--primary-text)", margin: "0 0 4px 0", cursor: "pointer" }}
                  >
                    {c.name}
                  </h3>
                  {c.tagline && (
                    <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--primary-accent)", margin: "0 0 8px 0" }}>
                      {c.tagline}
                    </p>
                  )}
                  <p
                    style={{
                      fontSize: "13px",
                      color: "var(--secondary-text)",
                      lineHeight: "1.4",
                      margin: "0 0 14px 0",
                      display: "-webkit-box",
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {c.description}
                  </p>

                  {/* Tags */}
                  {c.tags && c.tags.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "16px" }}>
                      {c.tags.map((t, idx) => (
                        <span
                          key={idx}
                          style={{
                            fontSize: "11px",
                            fontWeight: 600,
                            padding: "2px 8px",
                            borderRadius: "6px",
                            background: "var(--secondary-bg)",
                            color: "var(--secondary-text)",
                          }}
                        >
                          #{t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    paddingTop: "14px",
                    borderTop: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ display: "flex", gap: "12px", fontSize: "12px", color: "var(--secondary-text)" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <MessageSquare size={14} /> {c.discussions_count}
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <Calendar size={14} /> {c.activities_count}
                    </span>
                  </div>

                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      onClick={() => navigate(`/circles/${c.id}`)}
                      className="button"
                      style={{ fontSize: "12px", padding: "6px 12px" }}
                    >
                      View
                    </button>
                    <button
                      onClick={() => handleToggleJoin(c)}
                      className={`button ${c.is_member ? "" : "primary"}`}
                      style={{ fontSize: "12px", padding: "6px 14px" }}
                    >
                      {c.is_member ? "Joined ✓" : "Join"}
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

        {/* Create Circle Modal */}
        {showCreateModal && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0, 0, 0, 0.65)",
              backdropFilter: "blur(4px)",
              display: "grid",
              placeItems: "center",
              zIndex: 9999,
              padding: "16px",
            }}
          >
            <div
              className="card"
              style={{
                width: "100%",
                maxWidth: "520px",
                borderRadius: "20px",
                padding: "26px",
                background: "var(--card-bg)",
              }}
            >
              <h2 style={{ fontSize: "18px", fontWeight: "800", color: "var(--primary-text)", margin: "0 0 6px 0" }}>
                Create an Interest Circle
              </h2>
              <p style={{ fontSize: "13px", color: "var(--secondary-text)", margin: "0 0 18px 0" }}>
                Small groups allow deeper discussions, accountability, and project collaboration.
              </p>

              <form onSubmit={handleCreateCircle} className="auth-form">
                <label>
                  Circle Name
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. ROS2 Robotics Builders"
                    required
                  />
                </label>

                <label>
                  One-Line Tagline
                  <input
                    type="text"
                    value={tagline}
                    onChange={(e) => setTagline(e.target.value)}
                    placeholder="e.g. Weekly paper study & hardware testing"
                  />
                </label>

                <label>
                  Focus Description
                  <textarea
                    value={desc}
                    onChange={(e) => setDesc(e.target.value)}
                    placeholder="Describe what your circle explores, meeting cadences, or goals..."
                    rows={4}
                    required
                  />
                </label>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <label>
                    Category
                    <select value={category} onChange={(e) => setCategory(e.target.value)}>
                      <option value="Technology">Technology</option>
                      <option value="AI & Robotics">AI & Robotics</option>
                      <option value="Design & UX">Design & UX</option>
                      <option value="Startups">Startups</option>
                      <option value="Outdoors & Fitness">Outdoors & Fitness</option>
                    </select>
                  </label>

                  <label>
                    Max Capacity (2-50)
                    <input
                      type="number"
                      min={2}
                      max={50}
                      value={maxMembers}
                      onChange={(e) => setMaxMembers(Number(e.target.value))}
                    />
                  </label>
                </div>

                <label>
                  Tags (comma-separated)
                  <input
                    type="text"
                    value={tags}
                    onChange={(e) => setTags(e.target.value)}
                    placeholder="e.g. ROS2, Python, Robotics, Autonomous"
                  />
                </label>

                <div className="actions" style={{ marginTop: "18px", justifyContent: "flex-end" }}>
                  <button type="button" className="button" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="button primary" disabled={submitting}>
                    {submitting ? "Creating..." : "Launch Circle (+75 XP)"}
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
