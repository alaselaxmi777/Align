import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FolderGit2,
  Users,
  CheckCircle2,
  Circle,
  PlusCircle,
  Github,
  Globe,
  UserCheck,
  Send,
  ShieldCheck,
  Calendar,
  Layers,
  Sparkles,
  MessageSquare,
} from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, ProjectItem, ProjectDiscussionItem, sanitizeExternalUrl } from "../lib/api";
import { useToast } from "../components/common/ToastContext";
import { formatApiError } from "../lib/errorUtils";

type Application = {
  id: number;
  applicant_id: number;
  applicant_name: string;
  applicant_avatar?: string | null;
  applicant_skills: string;
  desired_role: string;
  pitch_message: string;
  status: string;
  created_at: string;
};

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const projectId = Number(id);

  const [project, setProject] = useState<ProjectItem | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [discussions, setDiscussions] = useState<ProjectDiscussionItem[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "milestones" | "team" | "discussions" | "applications">("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Apply Modal state
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [desiredRole, setDesiredRole] = useState("");
  const [pitchMessage, setPitchMessage] = useState("");
  const [applying, setApplying] = useState(false);

  // Add Milestone Modal state (for owner)
  const [showAddMilestone, setShowAddMilestone] = useState(false);
  const [msTitle, setMsTitle] = useState("");
  const [msDesc, setMsDesc] = useState("");

  // Discussion state
  const [discTitle, setDiscTitle] = useState("");
  const [discContent, setDiscContent] = useState("");
  const [postingDisc, setPostingDisc] = useState(false);

  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    if (!projectId) return;
    loadProject();
  }, [projectId]);

  async function loadProject() {
    setLoading(true);
    setError("");
    try {
      const data = await api.projectDetails(projectId);
      setProject(data);
      const discs = await api.projectDiscussions(projectId).catch(() => []);
      setDiscussions(discs);
      if (data.is_owner) {
        const apps = await api.projectApplications(projectId);
        setApplications(apps);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleMilestone(milestoneId: number, currentlyCompleted: boolean) {
    try {
      await api.updateProjectMilestone(projectId, milestoneId, {
        is_completed: !currentlyCompleted,
      });
      toast.success(currentlyCompleted ? "Milestone marked incomplete." : "Milestone completed!");
      loadProject();
    } catch (err) {
      toast.error(formatApiError(err, "Failed to update milestone"));
    }
  }

  async function handleUpdateStatus(newStatus: string) {
    try {
      await api.updateProject(projectId, { status: newStatus });
      toast.success(`Project status updated to ${newStatus}.`);
      loadProject();
    } catch (err) {
      toast.error(formatApiError(err, "Failed to update status"));
    }
  }

  async function handlePostDiscussion(e: React.FormEvent) {
    e.preventDefault();
    if (!discContent.trim()) return;
    setPostingDisc(true);
    try {
      await api.createProjectDiscussion(projectId, {
        title: discTitle.trim(),
        content: discContent.trim(),
      });
      toast.success("Update posted to discussion stream!");
      setDiscTitle("");
      setDiscContent("");
      const discs = await api.projectDiscussions(projectId);
      setDiscussions(discs);
    } catch (err) {
      toast.error(formatApiError(err, "Failed to post update"));
    } finally {
      setPostingDisc(false);
    }
  }

  async function handleApply(e: React.FormEvent) {
    e.preventDefault();
    if (!desiredRole.trim() || !pitchMessage.trim()) return;
    setApplying(true);
    try {
      const res = await api.applyToProject(projectId, {
        desired_role: desiredRole.trim(),
        pitch_message: pitchMessage.trim(),
      });
      toast.success(res.message);
      setShowApplyModal(false);
      setDesiredRole("");
      setPitchMessage("");
      loadProject();
    } catch (err) {
      toast.error(formatApiError(err, "Failed to submit application"));
    } finally {
      setApplying(false);
    }
  }

  async function handleReviewApplication(appId: number, action: "accepted" | "rejected") {
    try {
      await api.reviewProjectApplication(projectId, appId, action);
      toast.success(`Application ${action}!`);
      loadProject();
    } catch (err) {
      toast.error(formatApiError(err, "Action failed"));
    }
  }

  async function handleAddMilestone(e: React.FormEvent) {
    e.preventDefault();
    if (!msTitle.trim()) return;
    try {
      await api.addProjectMilestone(projectId, {
        title: msTitle.trim(),
        description: msDesc.trim(),
      });
      toast.success("Milestone added successfully!");
      setShowAddMilestone(false);
      setMsTitle("");
      setMsDesc("");
      loadProject();
    } catch (err) {
      toast.error(formatApiError(err, "Failed to add milestone"));
    }
  }

  if (loading) {
    return (
      <AppShell title="Project Workspace">
        <div style={{ textAlign: "center", padding: "80px 20px", color: "var(--text-secondary)" }}>
          <div className="spinner" style={{ margin: "0 auto 16px" }} />
          <p>Loading project workspace...</p>
        </div>
      </AppShell>
    );
  }

  if (error || !project) {
    return (
      <AppShell title="Project Workspace">
        <div style={{ maxWidth: 600, margin: "60px auto", padding: 24, textAlign: "center" }}>
          <p style={{ color: "#EF4444", marginBottom: 16 }}>{error || "Project not found"}</p>
          <Link to="/projects" className="btn btn-secondary">
            <ArrowLeft size={16} /> Back to Projects
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title={project.title}>
      <div style={{ maxWidth: 1040, margin: "0 auto", padding: "20px 16px 80px" }}>
        {/* Back Link */}
        <Link
          to="/projects"
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
          <ArrowLeft size={16} /> Back to Projects
        </Link>

        {/* Hero Card */}
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
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
            <div style={{ flex: "1 1 540px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
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
                  {project.category}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: "var(--text-secondary)",
                    background: "var(--bg-secondary)",
                    padding: "3px 8px",
                    borderRadius: 6,
                  }}
                >
                  {project.stage}
                </span>
              </div>

              <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
                {project.title}
              </h1>

              <p style={{ fontSize: 15, color: "var(--text-secondary)", margin: "0 0 16px", lineHeight: 1.5 }}>
                {project.tagline || project.description}
              </p>

              <div style={{ fontSize: 13, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 16 }}>
                <div>
                  Initiated by <strong style={{ color: "var(--text-primary)" }}>{project.creator_name}</strong>
                </div>
                <div>
                  Team size: <strong style={{ color: "var(--text-primary)" }}>{project.team_size} members</strong>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 160 }}>
              {!project.is_owner && !project.is_member && (
                <button
                  onClick={() => {
                    if (!loggedIn) {
                      navigate("/login");
                      return;
                    }
                    setShowApplyModal(true);
                  }}
                  className="btn"
                  style={{
                    background: "var(--accent-primary)",
                    color: "#fff",
                    fontWeight: 600,
                    padding: "10px 18px",
                    borderRadius: 10,
                    border: "none",
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 8,
                  }}
                >
                  <Send size={15} /> Apply to Join Team
                </button>
              )}

              {project.is_owner && (
                <div
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    background: "rgba(83,101,245,0.1)",
                    color: "var(--accent-primary)",
                    fontSize: 12,
                    fontWeight: 700,
                    textAlign: "center",
                  }}
                >
                  ★ You are Project Lead
                </div>
              )}

              {project.is_member && !project.is_owner && (
                <div
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    background: "rgba(16,185,129,0.1)",
                    color: "#10B981",
                    fontSize: 12,
                    fontWeight: 700,
                    textAlign: "center",
                  }}
                >
                  ✓ Active Contributor
                </div>
              )}

              {project.github_repo_url && (
                <a
                  href={sanitizeExternalUrl(project.github_repo_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary"
                  style={{
                    padding: "9px 16px",
                    borderRadius: 10,
                    fontSize: 13,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6,
                    textDecoration: "none",
                  }}
                >
                  <Github size={15} /> Source Code
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Apply Modal */}
        {showApplyModal && (
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
              onSubmit={handleApply}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: 16,
                padding: 24,
                width: "100%",
                maxWidth: 480,
                boxShadow: "0 20px 40px rgba(0,0,0,0.3)",
              }}
            >
              <h3 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>
                Apply to Join {project.title}
              </h3>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 16px" }}>
                Introduce yourself and let the project lead know which role you want to own.
              </p>

              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                  Desired Role
                </label>
                <input
                  type="text"
                  placeholder="e.g. Frontend Engineer, ML Researcher, UI Designer"
                  value={desiredRole}
                  onChange={(e) => setDesiredRole(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                  }}
                  required
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                  Your Pitch & Relevant Experience
                </label>
                <textarea
                  rows={4}
                  placeholder="Tell the team why you're excited about this project and link any prior work..."
                  value={pitchMessage}
                  onChange={(e) => setPitchMessage(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                  }}
                  required
                />
              </div>

              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <button
                  type="button"
                  onClick={() => setShowApplyModal(false)}
                  disabled={applying}
                  className="btn btn-secondary"
                  style={{ padding: "7px 14px", fontSize: 13 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={applying}
                  className="btn"
                  style={{
                    background: "var(--accent-primary)",
                    color: "#fff",
                    padding: "7px 16px",
                    fontSize: 13,
                    fontWeight: 600,
                    border: "none",
                    borderRadius: 8,
                    cursor: "pointer",
                  }}
                >
                  {applying ? "Submitting..." : "Send Application"}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Tab Navigation */}
        <div style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--border-color)", marginBottom: 24 }}>
          <button
            onClick={() => setActiveTab("overview")}
            style={{
              padding: "10px 18px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "overview" ? "2px solid var(--accent-primary)" : "2px solid transparent",
              color: activeTab === "overview" ? "var(--accent-primary)" : "var(--text-secondary)",
              fontWeight: 600,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Overview & Vision
          </button>

          <button
            onClick={() => setActiveTab("milestones")}
            style={{
              padding: "10px 18px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "milestones" ? "2px solid var(--accent-primary)" : "2px solid transparent",
              color: activeTab === "milestones" ? "var(--accent-primary)" : "var(--text-secondary)",
              fontWeight: 600,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Milestones ({project.milestones?.length || 0})
          </button>

          <button
            onClick={() => setActiveTab("team")}
            style={{
              padding: "10px 18px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "team" ? "2px solid var(--accent-primary)" : "2px solid transparent",
              color: activeTab === "team" ? "var(--accent-primary)" : "var(--text-secondary)",
              fontWeight: 600,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Team ({project.members?.length || project.team_size})
          </button>

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
              gap: 6,
            }}
          >
            <MessageSquare size={14} /> Updates &amp; Discussions ({discussions.length})
          </button>

          {project.is_owner && (
            <button
              onClick={() => setActiveTab("applications")}
              style={{
                padding: "10px 18px",
                background: "none",
                border: "none",
                borderBottom: activeTab === "applications" ? "2px solid var(--accent-primary)" : "2px solid transparent",
                color: activeTab === "applications" ? "var(--accent-primary)" : "var(--text-secondary)",
                fontWeight: 600,
                fontSize: 14,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              Applicant Review ({applications.length})
            </button>
          )}
        </div>

        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div>
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: 14,
                padding: 24,
                marginBottom: 20,
              }}
            >
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 12px", color: "var(--text-primary)" }}>
                Project Description
              </h2>
              <p style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.6, margin: "0 0 20px", whiteSpace: "pre-wrap" }}>
                {project.description}
              </p>

              {/* Roles Needed */}
              {project.required_roles && project.required_roles.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
                    Roles Needed on the Team
                  </h3>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {project.required_roles.map((r, idx) => (
                      <span
                        key={idx}
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          padding: "4px 10px",
                          borderRadius: 6,
                          background: "rgba(16,185,129,0.1)",
                          color: "#10B981",
                        }}
                      >
                        + {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Skills Needed */}
              {project.skills_needed && project.skills_needed.length > 0 && (
                <div>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
                    Target Tech Stack & Skills
                  </h3>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {project.skills_needed.map((s, idx) => (
                      <span
                        key={idx}
                        style={{
                          fontSize: 12,
                          padding: "3px 9px",
                          borderRadius: 6,
                          background: "var(--bg-secondary)",
                          border: "1px solid var(--border-color)",
                          color: "var(--text-secondary)",
                        }}
                      >
                        #{s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: MILESTONES */}
        {activeTab === "milestones" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                Project Milestones
              </h2>
              {project.is_owner && (
                <button
                  onClick={() => setShowAddMilestone(true)}
                  className="btn"
                  style={{
                    background: "var(--accent-primary)",
                    color: "#fff",
                    padding: "8px 14px",
                    borderRadius: 8,
                    fontSize: 13,
                    fontWeight: 600,
                    border: "none",
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  <PlusCircle size={15} /> Add Milestone
                </button>
              )}
            </div>

            {/* Add Milestone Form */}
            {showAddMilestone && (
              <form
                onSubmit={handleAddMilestone}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 12,
                  padding: 16,
                  marginBottom: 16,
                }}
              >
                <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px", color: "var(--text-primary)" }}>
                  Add Project Milestone
                </h4>
                <input
                  type="text"
                  placeholder="Milestone title (e.g. Design Database Schema)"
                  value={msTitle}
                  onChange={(e) => setMsTitle(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                    marginBottom: 8,
                  }}
                  required
                />
                <textarea
                  rows={2}
                  placeholder="Description or deliverable criteria..."
                  value={msDesc}
                  onChange={(e) => setMsDesc(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                    marginBottom: 10,
                  }}
                />
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button
                    type="button"
                    onClick={() => setShowAddMilestone(false)}
                    className="btn btn-secondary"
                    style={{ padding: "6px 12px", fontSize: 12 }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn"
                    style={{
                      background: "var(--accent-primary)",
                      color: "#fff",
                      padding: "6px 14px",
                      fontSize: 12,
                      fontWeight: 600,
                      border: "none",
                      borderRadius: 8,
                    }}
                  >
                    Save Milestone
                  </button>
                </div>
              </form>
            )}

            {project.milestones && project.milestones.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {project.milestones.map((m, idx) => (
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
                    {(project.is_owner || project.is_member) ? (
                      <button
                        onClick={() => handleToggleMilestone(m.id, m.is_completed)}
                        title={m.is_completed ? "Mark as in-progress" : "Mark as completed"}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          padding: 0,
                          display: "flex",
                          alignItems: "center",
                        }}
                      >
                        {m.is_completed ? (
                          <CheckCircle2 size={22} color="#10B981" />
                        ) : (
                          <Circle size={22} color="var(--text-secondary)" />
                        )}
                      </button>
                    ) : (
                      m.is_completed ? (
                        <CheckCircle2 size={20} color="#10B981" />
                      ) : (
                        <Circle size={20} color="var(--text-secondary)" />
                      )
                    )}
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)" }}>
                          Phase {idx + 1}
                        </span>
                        <h4
                          style={{
                            fontSize: 15,
                            fontWeight: 600,
                            margin: 0,
                            color: "var(--text-primary)",
                            textDecoration: m.is_completed ? "line-through" : "none",
                          }}
                        >
                          {m.title}
                        </h4>
                      </div>
                      {m.description && (
                        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
                          {m.description}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: 30, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>
                No milestones added yet.
              </div>
            )}
          </div>
        )}

        {/* TAB 3: TEAM */}
        {activeTab === "team" && (
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 16px", color: "var(--text-primary)" }}>
              Project Team ({project.members?.length || 0})
            </h2>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
              {project.members &&
                project.members.map((m) => (
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
                      {m.name.slice(0, 1).toUpperCase()}
                    </div>
                    <div>
                      <h4 style={{ fontSize: 14, fontWeight: 600, margin: 0, color: "var(--text-primary)" }}>
                        {m.name}
                      </h4>
                      <p style={{ fontSize: 12, color: "var(--accent-primary)", margin: "2px 0 0", fontWeight: 500 }}>
                        {m.role}
                      </p>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* TAB 4: DISCUSSIONS & UPDATES */}
        {activeTab === "discussions" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                Project Updates &amp; Discussions ({discussions.length})
              </h2>
            </div>

            {/* Post update box */}
            {loggedIn && (
              <form
                onSubmit={handlePostDiscussion}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 14,
                  padding: 18,
                  marginBottom: 20,
                }}
              >
                <input
                  type="text"
                  placeholder="Update headline or topic (optional)..."
                  value={discTitle}
                  onChange={(e) => setDiscTitle(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                    marginBottom: 8,
                  }}
                />
                <textarea
                  rows={3}
                  placeholder="Share a project milestone update, technical question, or decision with the team..."
                  value={discContent}
                  onChange={(e) => setDiscContent(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                    marginBottom: 10,
                  }}
                  required
                />
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button
                    type="submit"
                    disabled={postingDisc}
                    className="btn"
                    style={{
                      background: "var(--accent-primary)",
                      color: "#fff",
                      padding: "7px 16px",
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
                    <Send size={13} /> {postingDisc ? "Posting..." : "Post Update"}
                  </button>
                </div>
              </form>
            )}

            {/* Discussions List */}
            {discussions.length === 0 ? (
              <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>
                No project discussions posted yet. Start the conversation!
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {discussions.map((d) => (
                  <div
                    key={d.id}
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border-color)",
                      borderRadius: 12,
                      padding: 16,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                      <div
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: "50%",
                          background: "var(--bg-secondary)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: 13,
                          fontWeight: 700,
                          color: "var(--accent-primary)",
                        }}
                      >
                        {d.author_name.slice(0, 1).toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                          {d.author_name}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                          {new Date(d.created_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    {d.title && (
                      <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px", color: "var(--text-primary)" }}>
                        {d.title}
                      </h4>
                    )}
                    <p style={{ fontSize: 13, color: "var(--text-primary)", margin: 0, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                      {d.content}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 5: APPLICATIONS (Owner Only) */}
        {activeTab === "applications" && project.is_owner && (
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 16px", color: "var(--text-primary)" }}>
              Applicant Review ({applications.length})
            </h2>

            {applications.length === 0 ? (
              <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>
                No active applications at the moment.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {applications.map((app) => (
                  <div
                    key={app.id}
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border-color)",
                      borderRadius: 12,
                      padding: 18,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                      <div>
                        <h4 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                          {app.applicant_name}
                        </h4>
                        <span style={{ fontSize: 12, color: "var(--accent-primary)", fontWeight: 600 }}>
                          Role: {app.desired_role}
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          textTransform: "uppercase",
                          padding: "3px 8px",
                          borderRadius: 6,
                          background:
                            app.status === "accepted"
                              ? "rgba(16,185,129,0.1)"
                              : app.status === "rejected"
                              ? "rgba(239,68,68,0.1)"
                              : "rgba(245,158,11,0.1)",
                          color:
                            app.status === "accepted"
                              ? "#10B981"
                              : app.status === "rejected"
                              ? "#EF4444"
                              : "#F59E0B",
                        }}
                      >
                        {app.status}
                      </span>
                    </div>

                    <p style={{ fontSize: 13, color: "var(--text-primary)", margin: "0 0 12px", lineHeight: 1.4 }}>
                      "{app.pitch_message}"
                    </p>

                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 12 }}>
                      Skills: {app.applicant_skills || "General Builder"}
                    </div>

                    {app.status === "pending" && (
                      <div style={{ display: "flex", gap: 8 }}>
                        <button
                          onClick={() => handleReviewApplication(app.id, "accepted")}
                          className="btn"
                          style={{
                            background: "#10B981",
                            color: "#fff",
                            border: "none",
                            borderRadius: 6,
                            padding: "6px 14px",
                            fontSize: 12,
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          Accept to Team
                        </button>
                        <button
                          onClick={() => handleReviewApplication(app.id, "rejected")}
                          className="btn btn-secondary"
                          style={{ padding: "6px 14px", fontSize: 12, color: "#EF4444" }}
                        >
                          Decline
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
