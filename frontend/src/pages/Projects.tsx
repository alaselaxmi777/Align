import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FolderGit2,
  Users,
  Sparkles,
  PlusCircle,
  Search,
  Filter,
  ArrowRight,
  ExternalLink,
  Code2,
  CheckCircle2,
  Layers,
  Tag,
  Github,
} from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, ProjectItem } from "../lib/api";
import { useToast } from "../components/common/ToastContext";
import { formatApiError } from "../lib/errorUtils";

const CATEGORIES = [
  "All",
  "AI / Machine Learning",
  "Web3 & Blockchain",
  "Mobile Apps",
  "Open Source Tools",
  "Robotics & IoT",
  "Social Impact",
];

export default function Projects() {
  const navigate = useNavigate();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<"projects" | "github_issues">("projects");
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [selectedStage, setSelectedStage] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // GitHub Good First Issues State
  const [githubIssues, setGithubIssues] = useState<
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
  >([]);
  const [loadingIssues, setLoadingIssues] = useState(false);

  // Publish Modal State
  const [showModal, setShowModal] = useState(false);
  const [pTitle, setPTitle] = useState("");
  const [pTagline, setPTagline] = useState("");
  const [pDesc, setPDesc] = useState("");
  const [pCategory, setPCategory] = useState("AI / Machine Learning");
  const [pStage, setPStage] = useState("Idea / Brainstorming");
  const [pRoles, setPRoles] = useState("");
  const [pSkills, setPSkills] = useState("");
  const [pGithub, setPGithub] = useState("");
  const [creating, setCreating] = useState(false);

  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    loadProjects();
  }, [selectedCategory, selectedStage]);

  async function loadGithubIssues(query = searchQuery || "python") {
    setLoadingIssues(true);
    try {
      const data = await api.githubGoodFirstIssues(query, 12);
      setGithubIssues(data);
    } catch (err) {
      console.error("Failed to load GitHub issues:", err);
    } finally {
      setLoadingIssues(false);
    }
  }

  async function loadProjects(search = searchQuery) {
    setLoading(true);
    setError("");
    try {
      const cat = selectedCategory === "All" ? "" : selectedCategory;
      const stg = selectedStage === "All" ? "" : selectedStage;
      const data = await api.projects(search, cat, stg);
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (activeTab === "github_issues") {
      loadGithubIssues(searchQuery.trim() || "python");
    } else {
      loadProjects(searchQuery.trim());
    }
  }

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!pTitle.trim()) {
      toast.error("Please enter a project title (minimum 2 characters).");
      return;
    }
    if (pTitle.trim().length < 2) {
      toast.error("Project title must be at least 2 characters.");
      return;
    }
    if (!pDesc.trim()) {
      toast.error("Please enter a project description (minimum 10 characters).");
      return;
    }
    if (pDesc.trim().length < 10) {
      toast.error("Project description must be at least 10 characters.");
      return;
    }
    if (pGithub.trim() && !/^https?:\/\//i.test(pGithub.trim())) {
      toast.error("GitHub URL must start with http:// or https://");
      return;
    }

    const parsedRoles = pRoles
      .split(",")
      .map((r) => r.trim())
      .filter(Boolean)
      .join(", ");

    const parsedSkills = pSkills
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .join(", ");

    setCreating(true);
    try {
      const newProj = await api.createProject({
        title: pTitle.trim(),
        tagline: pTagline.trim(),
        description: pDesc.trim(),
        category: pCategory,
        stage: pStage,
        required_roles: parsedRoles,
        skills_needed: parsedSkills,
        github_repo_url: pGithub.trim() || undefined,
      });
      toast.success("Project published successfully!");
      setShowModal(false);
      setPTitle("");
      setPTagline("");
      setPDesc("");
      setPRoles("");
      setPSkills("");
      setPGithub("");
      navigate(`/projects/${newProj.id}`);
    } catch (err) {
      toast.error(formatApiError(err, "Failed to publish project"));
    } finally {
      setCreating(false);
    }
  }

  return (
    <AppShell title="Collaboration Hub">
      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "20px 16px 80px" }}>
        {/* Header Hero */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(83,101,245,0.08) 0%, rgba(59,130,246,0.04) 100%)",
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
              <FolderGit2 size={14} /> Team Matchmaking & Project Ideas
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
              Collaborate & Build Real Projects
            </h1>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0, maxWidth: 640 }}>
              Discover genuine student and builder projects, apply for open contributor roles, track milestones, and ship together.
            </p>
          </div>

          <button
            onClick={() => {
              if (!loggedIn) {
                navigate("/login");
                return;
              }
              setShowModal(true);
            }}
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
            <PlusCircle size={16} /> Publish Project Idea
          </button>
        </div>

        {/* Modal: Publish Project */}
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
              onSubmit={handleCreateProject}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                borderRadius: 16,
                padding: 24,
                width: "100%",
                maxWidth: 580,
                maxHeight: "90vh",
                overflowY: "auto",
                boxShadow: "0 20px 40px rgba(0,0,0,0.3)",
              }}
            >
              <h3 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 14px", color: "var(--text-primary)" }}>
                Publish a Builder Project Idea
              </h3>

              <div style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                    Project Title *
                  </label>
                  <span style={{ fontSize: 11, color: pTitle.trim().length < 2 ? "#EF4444" : "var(--text-secondary)" }}>
                    {pTitle.trim().length}/180 (min 2)
                  </span>
                </div>
                <input
                  type="text"
                  placeholder="e.g. MedAssist AI - Clinical Note Summarizer"
                  value={pTitle}
                  maxLength={180}
                  onChange={(e) => setPTitle(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: `1px solid ${pTitle && pTitle.trim().length < 2 ? "#EF4444" : "var(--border-color)"}`,
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                  }}
                  required
                />
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                  One-Line Hook / Tagline (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Building an open-source clinical NLP assistant for healthcare workers"
                  value={pTagline}
                  maxLength={255}
                  onChange={(e) => setPTagline(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                  }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                    Category
                  </label>
                  <select
                    value={pCategory}
                    onChange={(e) => setPCategory(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 13,
                    }}
                  >
                    <option value="AI / Machine Learning">AI / Machine Learning</option>
                    <option value="Web3 & Blockchain">Web3 & Blockchain</option>
                    <option value="Mobile Apps">Mobile Apps</option>
                    <option value="Open Source Tools">Open Source Tools</option>
                    <option value="Robotics & IoT">Robotics & IoT</option>
                    <option value="Social Impact">Social Impact</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                    Development Stage
                  </label>
                  <select
                    value={pStage}
                    onChange={(e) => setPStage(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 13,
                    }}
                  >
                    <option value="Idea / Brainstorming">Idea / Brainstorming</option>
                    <option value="Prototype in Progress">Prototype in Progress</option>
                    <option value="MVP Launched">MVP Launched</option>
                    <option value="Active Production">Active Production</option>
                  </select>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                    Roles Needed (comma-separated)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Frontend Dev, ML Engineer, Designer"
                    value={pRoles}
                    onChange={(e) => setPRoles(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 13,
                    }}
                  />
                  {pRoles.trim() && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
                      {pRoles.split(",").map((r) => r.trim()).filter(Boolean).map((role, idx) => (
                        <span key={idx} style={{ fontSize: 10, background: "rgba(16,185,129,0.15)", color: "#10B981", padding: "1px 6px", borderRadius: 4 }}>
                          +{role}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                    Skills Needed (comma-separated)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. React, PyTorch, FastAPI"
                    value={pSkills}
                    onChange={(e) => setPSkills(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 13,
                    }}
                  />
                  {pSkills.trim() && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
                      {pSkills.split(",").map((s) => s.trim()).filter(Boolean).map((skill, idx) => (
                        <span key={idx} style={{ fontSize: 10, background: "var(--bg-secondary)", color: "var(--text-secondary)", padding: "1px 6px", borderRadius: 4 }}>
                          #{skill}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                  GitHub Repository URL (Optional, must start with https://)
                </label>
                <input
                  type="url"
                  placeholder="https://github.com/organization/repo"
                  value={pGithub}
                  onChange={(e) => setPGithub(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: `1px solid ${pGithub && !/^https?:\/\//i.test(pGithub.trim()) ? "#EF4444" : "var(--border-color)"}`,
                    background: "var(--bg-secondary)",
                    color: "var(--text-primary)",
                    fontSize: 13,
                  }}
                />
              </div>

              <div style={{ marginBottom: 18 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                    Detailed Description & Vision *
                  </label>
                  <span style={{ fontSize: 11, fontWeight: 600, color: pDesc.trim().length < 10 ? "#EF4444" : "#10B981" }}>
                    {pDesc.trim().length < 10 ? `${pDesc.trim().length}/10 min characters` : `${pDesc.trim().length} characters (valid)`}
                  </span>
                </div>
                <textarea
                  rows={4}
                  placeholder="Explain the problem you're solving, tech architecture, and what you're looking for in collaborators (minimum 10 characters)..."
                  value={pDesc}
                  onChange={(e) => setPDesc(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: `1px solid ${pDesc && pDesc.trim().length < 10 ? "#EF4444" : "var(--border-color)"}`,
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
                  onClick={() => setShowModal(false)}
                  disabled={creating}
                  className="btn btn-secondary"
                  style={{ padding: "8px 16px", fontSize: 13 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || pTitle.trim().length < 2 || pDesc.trim().length < 10}
                  className="btn"
                  style={{
                    background: "var(--accent-primary)",
                    color: "#fff",
                    padding: "8px 18px",
                    fontSize: 13,
                    fontWeight: 600,
                    border: "none",
                    borderRadius: 8,
                    cursor: creating || pTitle.trim().length < 2 || pDesc.trim().length < 10 ? "not-allowed" : "pointer",
                    opacity: creating || pTitle.trim().length < 2 || pDesc.trim().length < 10 ? 0.6 : 1,
                  }}
                >
                  {creating ? "Publishing..." : "Publish Project"}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* View Switcher: Community Projects vs GitHub Good First Issues */}
        <div style={{ display: "flex", gap: 10, marginBottom: 18 }}>
          <button
            type="button"
            onClick={() => setActiveTab("projects")}
            style={{
              padding: "8px 18px",
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              border: activeTab === "projects" ? "1px solid var(--lime)" : "1px solid var(--border)",
              background: activeTab === "projects" ? "var(--lime)" : "var(--bg-card)",
              color: activeTab === "projects" ? "var(--on-lime)" : "var(--text)",
              transition: "all 0.15s ease",
            }}
          >
            Community Projects ({projects.length})
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab("github_issues");
              if (githubIssues.length === 0) loadGithubIssues();
            }}
            style={{
              padding: "8px 18px",
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              border: activeTab === "github_issues" ? "1px solid var(--lilac)" : "1px solid var(--border)",
              background: activeTab === "github_issues" ? "var(--lilac)" : "var(--bg-card)",
              color: activeTab === "github_issues" ? "#ffffff" : "var(--text)",
              display: "inline-flex",
              alignItems: "center",
              gap: 7,
              transition: "all 0.15s ease",
            }}
          >
            <Github size={15} /> GitHub Good First Issues ({githubIssues.length})
          </button>
        </div>

        {/* Filter & Search Bar */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", marginBottom: 20 }}>
          <form onSubmit={handleSearch} style={{ flex: "1 1 280px", position: "relative" }}>
            <Search size={16} color="var(--text-secondary)" style={{ position: "absolute", left: 12, top: 11 }} />
            <input
              type="text"
              placeholder="Search by title, role or tech stack..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "9px 12px 9px 36px",
                borderRadius: 8,
                border: "1px solid var(--border-color)",
                background: "var(--bg-card)",
                color: "var(--text-primary)",
                fontSize: 13,
              }}
            />
          </form>

          {/* Category Dropdown */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            style={{
              padding: "9px 14px",
              borderRadius: 8,
              border: "1px solid var(--border-color)",
              background: "var(--bg-card)",
              color: "var(--text-primary)",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        {/* Projects / GitHub Issues Grid */}
        {activeTab === "github_issues" ? (
          loadingIssues ? (
            <div style={{ textAlign: "center", padding: "80px 20px", color: "var(--text-secondary)" }}>
              <div className="spinner" style={{ margin: "0 auto 16px" }} />
              <p>Fetching real good-first-issues from GitHub...</p>
            </div>
          ) : githubIssues.length === 0 ? (
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px dashed var(--border-color)",
                borderRadius: 16,
                padding: 48,
                textAlign: "center",
                color: "var(--text-secondary)",
              }}
            >
              <Github size={40} style={{ margin: "0 auto 12px", opacity: 0.6 }} />
              <h3 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 6px", color: "var(--text-primary)" }}>
                No GitHub issues found
              </h3>
              <p style={{ fontSize: 13, margin: 0 }}>Try searching for a different language or topic (e.g., react, python, rust).</p>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 20 }}>
              {githubIssues.map((issue) => (
                <div
                  key={issue.id}
                  style={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border-color)",
                    borderRadius: 14,
                    padding: 20,
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          textTransform: "uppercase",
                          padding: "3px 8px",
                          borderRadius: 6,
                          background: "rgba(166,124,245,0.15)",
                          color: "var(--lilac)",
                        }}
                      >
                        {issue.repository}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 600,
                          color: "var(--lime)",
                          background: "rgba(216,245,106,0.1)",
                          padding: "3px 8px",
                          borderRadius: 6,
                        }}
                      >
                        good first issue
                      </span>
                    </div>

                    <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px", lineHeight: 1.35 }}>
                      {issue.title}
                    </h3>

                    {issue.labels && issue.labels.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 16 }}>
                        {issue.labels.slice(0, 4).map((label, idx) => (
                          <span
                            key={idx}
                            style={{
                              fontSize: 11,
                              padding: "2px 7px",
                              borderRadius: 4,
                              background: "var(--bg-secondary)",
                              color: "var(--text-secondary)",
                            }}
                          >
                            #{label}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div style={{ paddingTop: 14, borderTop: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      {issue.comments_count} comments
                    </span>
                    <a
                      href={issue.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        fontSize: 13,
                        fontWeight: 600,
                        color: "var(--accent-primary)",
                        textDecoration: "none",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      Contribute on GitHub <ExternalLink size={14} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : loading ? (
          <div style={{ textAlign: "center", padding: "80px 20px", color: "var(--text-secondary)" }}>
            <div className="spinner" style={{ margin: "0 auto 16px" }} />
            <p>Loading collaboration projects...</p>
          </div>
        ) : error ? (
          <div style={{ textAlign: "center", color: "#EF4444", padding: 30 }}>{error}</div>
        ) : projects.length === 0 ? (
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px dashed var(--border-color)",
              borderRadius: 16,
              padding: 48,
              textAlign: "center",
              color: "var(--text-secondary)",
            }}
          >
            <FolderGit2 size={40} style={{ margin: "0 auto 12px", opacity: 0.6 }} />
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 6px", color: "var(--text-primary)" }}>
              No projects found
            </h3>
            <p style={{ fontSize: 13, margin: 0 }}>Be the first builder to publish a project idea!</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 20 }}>
            {projects.map((p) => (
              <div
                key={p.id}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 14,
                  padding: 20,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                  transition: "transform 0.15s ease, box-shadow 0.15s ease",
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
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
                      {p.category}
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
                      {p.stage}
                    </span>
                  </div>

                  <h3 style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
                    {p.title}
                  </h3>

                  <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 14px", lineHeight: 1.4 }}>
                    {p.tagline || p.description.slice(0, 110) + "..."}
                  </p>

                  {/* Required Roles Needed Tags */}
                  {p.required_roles && p.required_roles.length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-secondary)", marginBottom: 6 }}>
                        Roles Needed:
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {p.required_roles.map((r, rIdx) => (
                          <span
                            key={rIdx}
                            style={{
                              fontSize: 11,
                              fontWeight: 600,
                              padding: "2px 8px",
                              borderRadius: 4,
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
                  {p.skills_needed && p.skills_needed.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 16 }}>
                      {p.skills_needed.slice(0, 4).map((s, sIdx) => (
                        <span
                          key={sIdx}
                          style={{
                            fontSize: 11,
                            padding: "2px 7px",
                            borderRadius: 4,
                            background: "var(--bg-secondary)",
                            color: "var(--text-secondary)",
                          }}
                        >
                          #{s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Card Footer */}
                <div style={{ paddingTop: 14, borderTop: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4 }}>
                    <Users size={14} />
                    <span>{p.team_size} members</span>
                  </div>

                  <Link
                    to={`/projects/${p.id}`}
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: "var(--accent-primary)",
                      textDecoration: "none",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    View Project <ArrowRight size={14} />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
