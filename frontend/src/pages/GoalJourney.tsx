import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Compass,
  Sparkles,
  CheckCircle2,
  Circle,
  Calendar,
  Users,
  Award,
  BookOpen,
  ArrowRight,
  PlusCircle,
  Trash2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  MapPin,
  Flame,
} from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, GoalJourneyItem, GoalMilestoneItem } from "../lib/api";
import { showToast } from "../components/common/ToastContext";

function formatGoalStatus(status: string) {
  switch (status?.toLowerCase()) {
    case "completed":
      return "Completed";
    case "in_progress":
      return "In Progress";
    case "not_started":
      return "Not Started";
    case "paused":
      return "Paused";
    case "archived":
      return "Archived";
    default:
      return status?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "In Progress";
  }
}

export default function GoalJourney() {
  const [journeys, setJourneys] = useState<GoalJourneyItem[]>([]);
  const [selectedJourneyId, setSelectedJourneyId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [goalTitle, setGoalTitle] = useState("");
  const [timeframe, setTimeframe] = useState("12 Weeks");
  const [category, setCategory] = useState("AI/ML");

  // Delete confirmation modal state
  const [deleteConfirmJourney, setDeleteConfirmJourney] = useState<GoalJourneyItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Expanded milestones accordion map
  const [expandedMilestones, setExpandedMilestones] = useState<Record<number, boolean>>({});

  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    if (loggedIn) {
      loadJourneys();
    } else {
      setLoading(false);
    }
  }, [loggedIn]);

  async function loadJourneys() {
    setLoading(true);
    setError("");
    try {
      const data = await api.myGoalJourneys();
      setJourneys(data);
      if (data.length > 0 && !selectedJourneyId) {
        setSelectedJourneyId(data[0].id);
        // Expand first milestone by default
        if (data[0].milestones && data[0].milestones.length > 0) {
          setExpandedMilestones({ [data[0].milestones[0].id]: true });
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load journeys");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!goalTitle.trim()) return;
    setGenerating(true);
    try {
      const newJourney = await api.generateGoalJourney({
        title: goalTitle.trim(),
        timeframe,
        category,
      });
      setGoalTitle("");
      setShowModal(false);
      setJourneys((prev) => [newJourney, ...prev]);
      setSelectedJourneyId(newJourney.id);
      if (newJourney.milestones && newJourney.milestones.length > 0) {
        setExpandedMilestones({ [newJourney.milestones[0].id]: true });
      }
      showToast("success", "AI Goal Journey generated successfully!");
    } catch (err) {
      showToast("error", err instanceof Error ? err.message : "Failed to generate goal journey");
    } finally {
      setGenerating(false);
    }
  }

  async function handleToggleMilestone(milestoneId: number) {
    if (!selectedJourneyId) return;
    try {
      const res = await api.toggleGoalMilestone(selectedJourneyId, milestoneId);
      // Update local state
      setJourneys((prev) =>
        prev.map((j) => {
          if (j.id !== selectedJourneyId) return j;
          const updatedMilestones = j.milestones.map((m) =>
            m.id === milestoneId ? { ...m, is_completed: res.is_completed } : m
          );
          const completedCount = updatedMilestones.filter((m) => m.is_completed).length;
          return {
            ...j,
            progress_percentage: res.journey_progress,
            status: res.journey_status,
            completed_milestones: completedCount,
            milestones: updatedMilestones,
          };
        })
      );
      if (res.is_completed) {
        if (res.journey_progress === 100) {
          showToast("success", "🎉 Goal Journey completed! +150 XP bonus earned!");
        } else {
          showToast("success", "Milestone completed! +50 XP earned");
        }
      }
    } catch (err) {
      showToast("error", err instanceof Error ? err.message : "Failed to update milestone");
    }
  }

  async function confirmDeleteJourney() {
    if (!deleteConfirmJourney) return;
    setDeleting(true);
    try {
      await api.deleteGoalJourney(deleteConfirmJourney.id);
      const remaining = journeys.filter((j) => j.id !== deleteConfirmJourney.id);
      setJourneys(remaining);
      if (selectedJourneyId === deleteConfirmJourney.id) {
        setSelectedJourneyId(remaining.length > 0 ? remaining[0].id : null);
      }
      showToast("success", `Deleted "${deleteConfirmJourney.title}"`);
      setDeleteConfirmJourney(null);
    } catch (err) {
      showToast("error", err instanceof Error ? err.message : "Failed to delete journey");
    } finally {
      setDeleting(false);
    }
  }

  const activeJourney = journeys.find((j) => j.id === selectedJourneyId) || journeys[0] || null;
  const totalStepWeeks = activeJourney?.milestones?.reduce((acc, m) => acc + (m.estimated_weeks || 0), 0) || 0;
  const completedStepWeeks = activeJourney?.milestones?.filter((m) => m.is_completed).reduce((acc, m) => acc + (m.estimated_weeks || 0), 0) || 0;

  return (
    <AppShell title="AI Goal Journey">
      <div style={{ maxWidth: 1040, margin: "0 auto", padding: "20px 16px 80px" }}>
        {/* Header Hero */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(83,101,245,0.08) 0%, rgba(139,92,246,0.04) 100%)",
            border: "1px solid var(--border-color)",
            borderRadius: 16,
            padding: "24px 28px",
            marginBottom: 24,
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 16,
          }}
        >
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "var(--accent-primary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
              <Sparkles size={14} /> AI-Powered Career & Learning Roadmaps
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
              Goal Journeys & Learning Paths
            </h1>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0, maxWidth: 640 }}>
              Turn your aspirational goals into structured milestones. Earn XP for every completed step, and discover real ALIGN peers, communities, and events tailored to each phase.
            </p>
          </div>

          <button
            onClick={() => setShowModal(true)}
            className="btn"
            style={{
              background: "var(--accent-primary)",
              color: "#fff",
              borderRadius: 10,
              padding: "10px 18px",
              fontSize: 14,
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              border: "none",
              cursor: "pointer",
            }}
          >
            <PlusCircle size={16} /> New AI Goal Journey
          </button>
        </div>

        {/* Modal: Generate Journey */}
        {showModal && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(0,0,0,0.65)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 100,
              padding: 16,
            }}
          >
            <form
              onSubmit={handleGenerate}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: 16,
                padding: 24,
                width: "100%",
                maxWidth: 520,
                boxShadow: "0 20px 40px rgba(0,0,0,0.3)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Sparkles size={20} color="var(--accent-primary)" />
                <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                  Create Goal Journey with AI
                </h3>
              </div>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 16px" }}>
                Describe what you want to learn or achieve. Our NLP framework breaks it down into phases and matches relevant community resources.
              </p>

              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                  Goal Title or Career Target
                </label>
                <input
                  type="text"
                  placeholder="e.g. Master Full-Stack Web Development or Learn Generative AI"
                  value={goalTitle}
                  onChange={(e) => setGoalTitle(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 14,
                  }}
                  required
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 18 }}>
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                    Category
                  </label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "9px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 14,
                    }}
                  >
                    <option value="AI/ML">AI & Machine Learning</option>
                    <option value="Web Development">Full-Stack Web Dev</option>
                    <option value="Mobile App">Mobile Engineering</option>
                    <option value="Data Science">Data Science & Analytics</option>
                    <option value="Cloud & DevOps">Cloud & DevOps</option>
                    <option value="Career & Research">Career & Research</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                    Target Timeframe
                  </label>
                  <select
                    value={timeframe}
                    onChange={(e) => setTimeframe(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "9px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 14,
                    }}
                  >
                    <option value="4 Weeks">4 Weeks (Sprint)</option>
                    <option value="8 Weeks">8 Weeks (Standard)</option>
                    <option value="12 Weeks">12 Weeks (Quarterly)</option>
                    <option value="24 Weeks">24 Weeks (In-depth)</option>
                  </select>
                </div>
              </div>

              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  disabled={generating}
                  className="btn btn-secondary"
                  style={{ padding: "8px 16px", fontSize: 13 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={generating}
                  className="btn"
                  style={{
                    background: "var(--accent-primary)",
                    color: "#fff",
                    padding: "8px 18px",
                    fontSize: 13,
                    fontWeight: 600,
                    border: "none",
                    borderRadius: 8,
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  {generating ? (
                    <>
                      <div className="spinner" style={{ width: 14, height: 14 }} /> Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles size={14} /> Generate Roadmap
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirmJourney && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(0,0,0,0.65)",
              backdropFilter: "blur(4px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 110,
              padding: 16,
            }}
          >
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: 16,
                padding: 24,
                width: "100%",
                maxWidth: 440,
                boxShadow: "0 20px 40px rgba(0,0,0,0.3)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <div style={{ width: 36, height: 36, borderRadius: "50%", background: "rgba(239, 68, 68, 0.15)", display: "flex", alignItems: "center", justifyContent: "center", color: "#EF4444" }}>
                  <Trash2 size={20} />
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                  Delete Goal Journey?
                </h3>
              </div>
              <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.5, margin: "0 0 20px" }}>
                Are you sure you want to permanently remove <strong>"{deleteConfirmJourney.title}"</strong> and all its milestones? This action cannot be undone.
              </p>
              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
                <button
                  type="button"
                  onClick={() => setDeleteConfirmJourney(null)}
                  disabled={deleting}
                  style={{
                    padding: "9px 16px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "transparent",
                    color: "var(--text-primary)",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmDeleteJourney}
                  disabled={deleting}
                  style={{
                    padding: "9px 18px",
                    borderRadius: 8,
                    border: "none",
                    background: "#EF4444",
                    color: "#FFFFFF",
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: deleting ? "not-allowed" : "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  {deleting ? "Deleting..." : "Delete Journey"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Content Layout */}
        {!loggedIn ? (
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-color)",
              borderRadius: 16,
              padding: 40,
              textAlign: "center",
            }}
          >
            <Compass size={40} color="var(--accent-primary)" style={{ margin: "0 auto 12px" }} />
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>
              Sign in to track your personalized journeys
            </h2>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px" }}>
              Save learning roadmaps, earn gamification XP, and stay accountable with community peers.
            </p>
            <Link to="/login" className="btn" style={{ background: "var(--accent-primary)", color: "#fff", padding: "10px 22px", borderRadius: 8, textDecoration: "none", fontWeight: 600 }}>
              Sign In to ALIGN
            </Link>
          </div>
        ) : loading ? (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-secondary)" }}>
            <div className="spinner" style={{ margin: "0 auto 16px" }} />
            <p>Loading your goal roadmaps...</p>
          </div>
        ) : journeys.length === 0 ? (
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px dashed var(--border-color)",
              borderRadius: 16,
              padding: "48px 24px",
              textAlign: "center",
            }}
          >
            <Sparkles size={40} color="var(--accent-primary)" style={{ margin: "0 auto 12px", opacity: 0.8 }} />
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 8px", color: "var(--text-primary)" }}>
              No Goal Journeys Yet
            </h2>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", maxWidth: 480, marginInline: "auto" }}>
              Start your first AI goal journey. Tell us your objective and we will generate step-by-step milestones, verified resources, and connect you with peers.
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="btn"
              style={{
                background: "var(--accent-primary)",
                color: "#fff",
                padding: "10px 20px",
                borderRadius: 8,
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <PlusCircle size={16} /> Create My First Journey
            </button>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 24, alignItems: "start" }}>
            {/* Left Sidebar: Journey List */}
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: 14,
                padding: 14,
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-secondary)", marginBottom: 12, letterSpacing: "0.05em" }}>
                My Journeys ({journeys.length})
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {journeys.map((j) => {
                  const isSelected = j.id === (activeJourney?.id || selectedJourneyId);
                  return (
                    <div
                      key={j.id}
                      onClick={() => setSelectedJourneyId(j.id)}
                      style={{
                        padding: "12px 14px",
                        borderRadius: 10,
                        background: isSelected ? "var(--bg-secondary)" : "transparent",
                        border: isSelected ? "1px solid var(--accent-primary)" : "1px solid transparent",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--accent-primary)" }}>
                          {j.target_category}
                        </span>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: "1px 5px",
                              borderRadius: 4,
                              background: j.status === "completed" ? "rgba(16, 185, 129, 0.15)" : "rgba(83, 101, 245, 0.15)",
                              color: j.status === "completed" ? "#10B981" : "var(--accent-primary)",
                            }}
                          >
                            {formatGoalStatus(j.status)}
                          </span>
                          <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                            {j.progress_percentage}%
                          </span>
                        </div>
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6, lineHeight: 1.3 }}>
                        {j.title}
                      </div>
                      {/* Mini progress bar */}
                      <div style={{ width: "100%", height: 4, background: "var(--border-color)", borderRadius: 2, overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${j.progress_percentage}%`,
                            height: "100%",
                            background: "var(--accent-primary)",
                            borderRadius: 2,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right Main: Active Journey Detail */}
            {activeJourney && (
              <div>
                {/* Active Journey Top Info Card */}
                <div
                  style={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 14,
                    padding: 20,
                    marginBottom: 20,
                  }}
                >
                  <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 14 }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            textTransform: "uppercase",
                            padding: "3px 8px",
                            borderRadius: 6,
                            background: "rgba(83,101,245,0.1)",
                            color: "var(--accent-primary)",
                          }}
                        >
                          {activeJourney.target_category}
                        </span>
                        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                          • {activeJourney.timeframe} ({totalStepWeeks} Weeks Total)
                        </span>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: 6,
                            background: activeJourney.status === "completed" ? "rgba(16, 185, 129, 0.15)" : "rgba(83, 101, 245, 0.15)",
                            color: activeJourney.status === "completed" ? "#10B981" : "var(--accent-primary)",
                          }}
                        >
                          • {formatGoalStatus(activeJourney.status)}
                        </span>
                        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                          • {completedStepWeeks} of {totalStepWeeks} weeks completed
                        </span>
                      </div>
                      <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
                        {activeJourney.title}
                      </h2>
                      <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
                        {activeJourney.description}
                      </p>
                    </div>

                    <button
                      onClick={() => setDeleteConfirmJourney(activeJourney)}
                      title="Delete Journey"
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--text-secondary)",
                        cursor: "pointer",
                        padding: 6,
                        borderRadius: 6,
                      }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  {/* Progress bar container */}
                  <div style={{ background: "var(--bg-secondary)", padding: 14, borderRadius: 10, border: "1px solid var(--border-color)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                      <span style={{ color: "var(--text-primary)" }}>Roadmap Progress</span>
                      <span style={{ color: "var(--accent-primary)" }}>
                        {activeJourney.completed_milestones} / {activeJourney.total_milestones} Milestones ({activeJourney.progress_percentage}%) · {completedStepWeeks}/{totalStepWeeks} Weeks Completed
                      </span>
                    </div>
                    <div style={{ width: "100%", height: 8, background: "var(--border-color)", borderRadius: 4, overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${activeJourney.progress_percentage}%`,
                          height: "100%",
                          background: "var(--accent-primary)",
                          borderRadius: 4,
                          transition: "width 0.3s ease",
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Milestones Timeline */}
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {activeJourney.milestones.map((m, idx) => {
                    const isExpanded = Boolean(expandedMilestones[m.id]);
                    return (
                      <div
                        key={m.id}
                        style={{
                          background: "var(--bg-card)",
                          border: `1px solid ${m.is_completed ? "rgba(16, 185, 129, 0.3)" : "var(--border-color)"}`,
                          borderRadius: 14,
                          overflow: "hidden",
                          transition: "border-color 0.2s ease",
                        }}
                      >
                        {/* Milestone Header Row */}
                        <div
                          style={{
                            padding: 16,
                            display: "flex",
                            alignItems: "flex-start",
                            gap: 12,
                            background: m.is_completed ? "rgba(16, 185, 129, 0.03)" : "transparent",
                          }}
                        >
                          <button
                            onClick={() => handleToggleMilestone(m.id)}
                            style={{
                              background: "none",
                              border: "none",
                              cursor: "pointer",
                              padding: 0,
                              color: m.is_completed ? "#10B981" : "var(--text-secondary)",
                              marginTop: 2,
                            }}
                            title={m.is_completed ? "Mark incomplete" : "Mark milestone complete (+50 XP)"}
                          >
                            {m.is_completed ? (
                              <CheckCircle2 size={22} color="#10B981" />
                            ) : (
                              <Circle size={22} />
                            )}
                          </button>

                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8, marginBottom: 4 }}>
                              <span
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  textTransform: "uppercase",
                                  padding: "2px 6px",
                                  borderRadius: 4,
                                  background: "var(--bg-secondary)",
                                  color: "var(--text-secondary)",
                                }}
                              >
                                Step {idx + 1}
                              </span>
                              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                                ~{m.estimated_weeks} weeks
                              </span>
                              {m.is_completed && (
                                <span style={{ fontSize: 11, fontWeight: 700, color: "#10B981" }}>
                                  ✓ Completed (+50 XP)
                                </span>
                              )}
                            </div>

                            <h3
                              style={{
                                fontSize: 16,
                                fontWeight: 700,
                                margin: 0,
                                color: m.is_completed ? "var(--text-secondary)" : "var(--text-primary)",
                                textDecoration: m.is_completed ? "line-through" : "none",
                              }}
                            >
                              {m.title}
                            </h3>
                          </div>

                          <button
                            onClick={() =>
                              setExpandedMilestones((prev) => ({ ...prev, [m.id]: !prev[m.id] }))
                            }
                            style={{
                              background: "none",
                              border: "none",
                              color: "var(--text-secondary)",
                              cursor: "pointer",
                              padding: 4,
                            }}
                          >
                            {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                          </button>
                        </div>

                        {/* Expandable Body */}
                        {isExpanded && (
                          <div style={{ padding: "0 16px 16px", borderTop: "1px solid var(--border-color)" }}>
                            <p style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.5, margin: "14px 0 16px" }}>
                              {m.description}
                            </p>

                            {/* Curated Resources */}
                            {m.resources && m.resources.length > 0 && (
                              <div style={{ marginBottom: 16 }}>
                                <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--text-secondary)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                                  <BookOpen size={14} /> Recommended Learning Resources
                                </div>
                                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                                  {m.resources.map((res, rIdx) => (
                                    <span
                                      key={rIdx}
                                      style={{
                                        fontSize: 12,
                                        padding: "4px 10px",
                                        borderRadius: 6,
                                        background: "var(--bg-secondary)",
                                        border: "1px solid var(--border-color)",
                                        color: "var(--text-primary)",
                                      }}
                                    >
                                      {res}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* ALIGN Community & Peer Integrations */}
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
                              {/* Recommended Communities */}
                              {m.recommended_communities && m.recommended_communities.length > 0 && (
                                <div style={{ background: "var(--bg-secondary)", padding: 12, borderRadius: 10, border: "1px solid var(--border-color)" }}>
                                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-primary)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                                    <Users size={14} /> Connected Communities
                                  </div>
                                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                    {m.recommended_communities.slice(0, 2).map((c) => (
                                      <Link
                                        key={c.id}
                                        to={`/communities/${c.id}`}
                                        style={{
                                          fontSize: 13,
                                          fontWeight: 600,
                                          color: "var(--text-primary)",
                                          textDecoration: "none",
                                          display: "flex",
                                          alignItems: "center",
                                          justifyContent: "space-between",
                                        }}
                                      >
                                        <span>{c.name}</span>
                                        <ArrowRight size={13} color="var(--text-secondary)" />
                                      </Link>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Recommended Peers */}
                              {m.recommended_peers && m.recommended_peers.length > 0 && (
                                <div style={{ background: "var(--bg-secondary)", padding: 12, borderRadius: 10, border: "1px solid var(--border-color)" }}>
                                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-primary)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                                    <Award size={14} /> Peers On This Track
                                  </div>
                                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                    {m.recommended_peers.slice(0, 2).map((p) => (
                                      <Link
                                        key={p.id}
                                        to="/people"
                                        style={{
                                          fontSize: 13,
                                          color: "var(--text-primary)",
                                          textDecoration: "none",
                                          display: "flex",
                                          alignItems: "center",
                                          gap: 8,
                                        }}
                                      >
                                        <span style={{ fontWeight: 600 }}>{p.name}</span>
                                        <span style={{ fontSize: 11, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                          ({p.skills.split(",")[0]})
                                        </span>
                                      </Link>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
