import { FormEvent, useEffect, useState } from "react";
import { Activity, ArrowLeft, ArrowRight, Check, CheckCircle2, HelpCircle, LoaderCircle, MapPin, Plus, Sparkles, Tag, Users, X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import CommunityCard from "../components/cards/CommunityCard";
import SearchBar from "../components/common/SearchBar";
import CategoryChips from "../components/common/CategoryChips";
import { api, Community } from "../lib/api";

const CATEGORIES = ["All", "Technology", "Outdoors", "Design", "Career", "Arts", "Wellness"];

export default function Communities() {
  const [communities, setCommunities] = useState<Community[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [showModal, setShowModal] = useState(false);

  // Assessment Wizard Steps (1 = Basics, 2 = Assessment, 3 = AI Alignment & Review)
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Step 1: Basics
  const [name, setName] = useState("");
  const [cat, setCat] = useState("Technology");
  const [loc, setLoc] = useState("Online");

  // Step 2: Alignment Assessment
  const [targetLevel, setTargetLevel] = useState("All Levels");
  const [purpose, setPurpose] = useState("Project Collaboration");
  const [cadence, setCadence] = useState("Bi-Weekly Meetups");
  const [focusTopics, setFocusTopics] = useState("");
  const [rules, setRules] = useState("Be respectful, collaborative, and constructive.");

  // Step 3: Synthesis
  const [submitting, setSubmitting] = useState(false);

  const navigate = useNavigate();
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    void fetchCommunities();
  }, [selectedCategory]);

  async function fetchCommunities(searchTerm = query) {
    setLoading(true);
    setError("");
    try {
      const categoryParam = selectedCategory === "All" ? "" : selectedCategory;
      const data = await api.communities(searchTerm, categoryParam);
      setCommunities(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load communities.");
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(val: string) {
    setQuery(val);
    void fetchCommunities(val);
  }

  // Synthesized description created from assessment
  const synthesizedDescription = `${name} is an active ${cat.toLowerCase()} community centered on ${purpose.toLowerCase()}. 
Designed for ${targetLevel.toLowerCase()}, we gather through ${cadence.toLowerCase()} to share knowledge, build together, and foster authentic peer connections.
Key values: ${rules}`;

  // Synthesized tags
  const synthesizedTags = [
    cat.toLowerCase(),
    targetLevel.toLowerCase().replace(" ", "-"),
    purpose.toLowerCase().replace(" ", "-"),
    ...focusTopics.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean),
  ].join(", ");

  async function handleCompleteAssessment(e: FormEvent) {
    e.preventDefault();
    if (!loggedIn) {
      navigate("/login?next=/communities");
      return;
    }
    setSubmitting(true);
    try {
      const created = await api.createCommunity({
        name,
        description: synthesizedDescription,
        category: cat,
        tags: synthesizedTags,
        location: loc,
      });
      setCommunities([created, ...communities]);
      setShowModal(false);
      // Reset wizard
      setStep(1);
      setName("");
      setFocusTopics("");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create community.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell title="Communities">
      <p className="eyebrow">Find your circle</p>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 className="page-title">Better together.</h1>
          <p className="lead" style={{ margin: 0 }}>
            Small conversations, big ideas, and people who get it.
          </p>
        </div>

        <button
          className="button primary"
          type="button"
          onClick={() => {
            if (!loggedIn) {
              navigate("/login?next=/communities");
            } else {
              setStep(1);
              setShowModal(true);
            }
          }}
        >
          <Plus size={16} /> Create community
        </button>
      </div>

      {/* Toolbar */}
      <div className="toolbar" style={{ marginTop: "24px" }}>
        <SearchBar
          value={query}
          onChange={handleSearch}
          placeholder="Search communities by name, topic, or keyword..."
        />
      </div>

      {/* Category Chips */}
      <CategoryChips
        categories={CATEGORIES}
        activeCategory={selectedCategory}
        onSelect={setSelectedCategory}
      />

      {error && (
        <div className="empty" style={{ color: "var(--error)", display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: 24 }}>
          <span>{error}</span>
          <button
            className="button"
            onClick={() => void fetchCommunities()}
            style={{ fontSize: 13, padding: "7px 18px", borderRadius: 8, cursor: "pointer" }}
          >
            Retry Loading Communities
          </button>
        </div>
      )}

      {/* Section Heading */}
      <div className="section-heading">
        <h2>Recommended &amp; trending communities</h2>
        <small className="meta">
          Showing {communities.length} {communities.length === 1 ? "community" : "communities"}
        </small>
      </div>

      {loading ? (
        <div className="grid-3">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div
              key={n}
              style={{
                height: 280,
                borderRadius: 16,
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                opacity: 0.5,
              }}
            />
          ))}
        </div>
      ) : communities.length === 0 ? (
        <div className="empty">
          <Users size={32} style={{ margin: "0 auto 10px auto", color: "var(--muted)" }} />
          <h3>No communities match your search.</h3>
          <p>Try another search or launch your own group using the create button above!</p>
        </div>
      ) : (
        <div className="grid-3">
          {communities.map((c) => (
            <CommunityCard key={c.id} community={c} />
          ))}
        </div>
      )}

      {/* Recently Active Panel */}
      <div className="section-heading" style={{ marginTop: "50px" }}>
        <h2>Recently active</h2>
      </div>

      {communities.length > 0 ? (
        <div className="panel list-row" style={{ padding: "20px" }}>
          <Activity size={24} style={{ color: "var(--accent)" }} />
          <div>
            <strong style={{ fontSize: "15px", color: "var(--text)" }}>{communities[0].name}</strong>
            <p style={{ margin: "3px 0 0 0", color: "var(--muted)", fontSize: "13px" }}>
              {communities[0].category} · {communities[0].member_count ?? 0} {communities[0].member_count === 1 ? "member" : "members"}
            </p>
          </div>
          <Link to={`/communities/${communities[0].id}`} className="button" style={{ marginLeft: "auto" }}>
            Visit
          </Link>
        </div>
      ) : (
        <div className="panel list-row" style={{ padding: "20px" }}>
          <Activity size={24} style={{ color: "var(--muted)" }} />
          <div>
            <strong style={{ fontSize: "15px", color: "var(--text)" }}>No recent community activity</strong>
            <p style={{ margin: "3px 0 0 0", color: "var(--muted)", fontSize: "13px" }}>
              Join or start a community to get discussions and events flowing.
            </p>
          </div>
        </div>
      )}

      {/* Modal: Assessment & Community Creation Wizard */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.65)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
            zIndex: 1000,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowModal(false);
          }}
        >
          <div
            style={{
              background: "var(--card)",
              borderRadius: "24px",
              padding: "32px",
              maxWidth: "580px",
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              boxShadow: "0 20px 60px rgba(0, 0, 0, 0.3)",
              border: "1.5px solid var(--border-subtle)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span className="mark" style={{ width: "24px", height: "24px", fontSize: "14px", borderRadius: "6px" }}>
                  <span>◈</span>
                </span>
                <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--accent)", textTransform: "uppercase", letterSpacing: "1px" }}>
                  Community Alignment Wizard · Step {step} of 3
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                style={{ background: "transparent", border: "none", color: "var(--secondary-text)", cursor: "pointer" }}
              >
                <X size={20} />
              </button>
            </div>

            {/* STEP 1: Basic Info */}
            {step === 1 && (
              <div>
                <h2 style={{ fontSize: "20px", fontWeight: "800", color: "var(--text)", margin: "0 0 6px 0" }}>
                  Launch a New Community
                </h2>
                <p style={{ color: "var(--muted)", fontSize: "13px", margin: "0 0 20px 0" }}>
                  Start with the essentials. Next, we will synthesize your alignment profile.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "13px", fontWeight: "700", marginBottom: "6px", color: "var(--text)" }}>
                      Community Name *
                    </label>
                    <input
                      type="text"
                      className="search"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Mumbai Generative AI Builders"
                      style={{ width: "100%" }}
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "13px", fontWeight: "700", marginBottom: "6px", color: "var(--text)" }}>
                      Category *
                    </label>
                    <select
                      className="search"
                      value={cat}
                      onChange={(e) => setCat(e.target.value)}
                      style={{ width: "100%" }}
                    >
                      {CATEGORIES.filter((c) => c !== "All").map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "13px", fontWeight: "700", marginBottom: "6px", color: "var(--text)" }}>
                      Location *
                    </label>
                    <input
                      type="text"
                      className="search"
                      required
                      value={loc}
                      onChange={(e) => setLoc(e.target.value)}
                      placeholder="e.g. Bandra, Mumbai or Global Online"
                      style={{ width: "100%" }}
                    />
                  </div>

                  <button
                    type="button"
                    className="button primary"
                    onClick={() => {
                      if (!name.trim()) {
                        alert("Please provide a community name.");
                        return;
                      }
                      setStep(2);
                    }}
                    style={{ marginTop: "10px", width: "100%" }}
                  >
                    Continue to Alignment Assessment →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: Alignment Assessment */}
            {step === 2 && (
              <div>
                <h2 style={{ fontSize: "20px", fontWeight: "800", color: "var(--text)", margin: "0 0 6px 0" }}>
                  Intent &amp; Alignment Framework
                </h2>
                <p style={{ color: "var(--muted)", fontSize: "13px", margin: "0 0 20px 0" }}>
                  Define the intent criteria our hybrid matching engine uses to connect high-synergy members.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "13px", fontWeight: "700", marginBottom: "6px", color: "var(--text)" }}>
                      Primary Focus &amp; Purpose
                    </label>
                    <select
                      className="search"
                      value={purpose}
                      onChange={(e) => setPurpose(e.target.value)}
                      style={{ width: "100%" }}
                    >
                      <option value="Project Collaboration">Project Collaboration &amp; Building</option>
                      <option value="Skill Mastery">Skill Mastery &amp; Peer Learning</option>
                      <option value="Casual Discussion">Casual Discussion &amp; Camaraderie</option>
                      <option value="Industry Networking">Industry Networking &amp; Mentorship</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "13px", fontWeight: "700", marginBottom: "6px", color: "var(--text)" }}>
                      Target Experience Level
                    </label>
                    <select
                      className="search"
                      value={targetLevel}
                      onChange={(e) => setTargetLevel(e.target.value)}
                      style={{ width: "100%" }}
                    >
                      <option value="All Levels">All Levels Welcome</option>
                      <option value="Beginner Friendly">Beginner Friendly</option>
                      <option value="Intermediate">Intermediate Practitioners</option>
                      <option value="Advanced / Expert">Advanced / Senior Specialists</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "13px", fontWeight: "700", marginBottom: "6px", color: "var(--text)" }}>
                      Key Focus Topics (comma separated)
                    </label>
                    <input
                      type="text"
                      className="search"
                      value={focusTopics}
                      onChange={(e) => setFocusTopics(e.target.value)}
                      placeholder="e.g. LLMs, Fine-tuning, RAG, PyTorch"
                      style={{ width: "100%" }}
                    />
                  </div>

                  <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                    <button type="button" className="button" onClick={() => setStep(1)} style={{ flex: 1 }}>
                      ← Back
                    </button>
                    <button type="button" className="button primary" onClick={() => setStep(3)} style={{ flex: 1 }}>
                      Synthesize Profile →
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 3: Review & Launch */}
            {step === 3 && (
              <form onSubmit={handleCompleteAssessment}>
                <h2 style={{ fontSize: "20px", fontWeight: "800", color: "var(--text)", margin: "0 0 6px 0" }}>
                  AI Synthesized Alignment Card
                </h2>
                <p style={{ color: "var(--muted)", fontSize: "13px", margin: "0 0 16px 0" }}>
                  Review your synthesized community charter before publishing to the ALIGN network.
                </p>

                <div
                  style={{
                    background: "var(--sub)",
                    padding: "18px",
                    borderRadius: "16px",
                    border: "1px solid var(--border-subtle)",
                    marginBottom: "20px",
                  }}
                >
                  <h3 style={{ fontSize: "16px", fontWeight: "800", color: "var(--text)", margin: "0 0 6px 0" }}>
                    {name}
                  </h3>
                  <span className="tag" style={{ marginBottom: "10px" }}>
                    {cat} · {loc}
                  </span>
                  <p style={{ fontSize: "13px", color: "var(--muted)", lineHeight: "1.6", margin: "8px 0" }}>
                    {synthesizedDescription}
                  </p>
                  <div style={{ marginTop: "10px", fontSize: "12px", color: "var(--secondary-text)" }}>
                    <strong>Generated Tags:</strong> {synthesizedTags}
                  </div>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button type="button" className="button" onClick={() => setStep(2)} style={{ flex: 1 }}>
                    ← Edit
                  </button>
                  <button type="submit" className="button primary" disabled={submitting} style={{ flex: 1 }}>
                    {submitting ? "Launching..." : "Launch Community"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}
