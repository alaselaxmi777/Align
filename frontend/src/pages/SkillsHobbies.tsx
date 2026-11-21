import { useState, useEffect } from "react";
import { BookOpen, Compass, Filter, LoaderCircle, Palette, Search, Sparkles, Star, Users, Wrench } from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, SkillMaster, HobbyMaster, SkillHobbyDatasetItem, CategorySummary, DatasetStats, DatasetFacets } from "../lib/api";

export default function SkillsHobbies() {
  const [activeTab, setActiveTab] = useState<"skills" | "hobbies" | "dataset">("skills");

  // Master lists
  const [masterSkills, setMasterSkills] = useState<SkillMaster[]>([]);
  const [skillCategories, setSkillCategories] = useState<CategorySummary[]>([]);
  const [masterHobbies, setMasterHobbies] = useState<HobbyMaster[]>([]);
  const [hobbyCategories, setHobbyCategories] = useState<CategorySummary[]>([]);

  // Granular dataset search
  const [searchResults, setSearchResults] = useState<SkillHobbyDatasetItem[]>([]);
  const [stats, setStats] = useState<DatasetStats | null>(null);
  const [facets, setFacets] = useState<DatasetFacets | null>(null);

  // Filters
  const [q, setQ] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [selectedContext, setSelectedContext] = useState("");
  const [selectedProficiency, setSelectedProficiency] = useState("");
  const [selectedSetting, setSelectedSetting] = useState("");
  const [selectedFrequency, setSelectedFrequency] = useState("");
  const [selectedMotivation, setSelectedMotivation] = useState("");

  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalFound, setTotalFound] = useState(0);

  // Initial load
  useEffect(() => {
    async function init() {
      try {
        const [sList, sCats, hList, hCats, st, fc] = await Promise.all([
          api.skills({ limit: 100 }),
          api.skillCategories(),
          api.hobbies({ limit: 100 }),
          api.hobbyCategories(),
          api.datasetStats(),
          api.datasetFacets(),
        ]);
        setMasterSkills(sList);
        setSkillCategories(sCats);
        setMasterHobbies(hList);
        setHobbyCategories(hCats);
        setStats(st);
        setFacets(fc);
      } catch (err) {
        console.error("Failed to load initial dataset masters:", err);
      }
    }
    init();
  }, []);

  // Search execution
  useEffect(() => {
    async function runSearch() {
      setLoading(true);
      try {
        if (activeTab === "skills") {
          const res = await api.searchSkills({
            q: q.trim() || undefined,
            category: selectedCategory !== "All" ? selectedCategory : undefined,
            context: selectedContext || undefined,
            proficiency: selectedProficiency || undefined,
            setting: selectedSetting || undefined,
            page,
            limit: 24,
          });
          setSearchResults(res);
          setTotalFound(res.length);
        } else if (activeTab === "hobbies") {
          const res = await api.searchHobbies({
            q: q.trim() || undefined,
            category: selectedCategory !== "All" ? selectedCategory : undefined,
            context: selectedContext || undefined,
            engagement: selectedProficiency || undefined,
            setting: selectedSetting || undefined,
            frequency: selectedFrequency || undefined,
            motivation: selectedMotivation || undefined,
            page,
            limit: 24,
          });
          setSearchResults(res);
          setTotalFound(res.length);
        }
      } catch (err) {
        console.error("Search error:", err);
      } finally {
        setLoading(false);
      }
    }

    if (activeTab !== "dataset") {
      runSearch();
    }
  }, [
    activeTab,
    q,
    selectedCategory,
    selectedContext,
    selectedProficiency,
    selectedSetting,
    selectedFrequency,
    selectedMotivation,
    page,
  ]);

  function resetFilters() {
    setQ("");
    setSelectedCategory("All");
    setSelectedContext("");
    setSelectedProficiency("");
    setSelectedSetting("");
    setSelectedFrequency("");
    setSelectedMotivation("");
    setPage(1);
  }

  function handleTabChange(tab: "skills" | "hobbies" | "dataset") {
    if (tab === activeTab) return;
    setSearchResults([]);
    resetFilters();
    setActiveTab(tab);
  }

  const currentCategories = activeTab === "skills" ? skillCategories : hobbyCategories;

  return (
    <AppShell title="Skills Catalog">
      <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
        {/* Banner */}
        <section
          style={{
            padding: "36px 32px",
            background: "var(--bg-card)",
            border: "1.5px solid var(--border-subtle)",
            borderRadius: "24px",
            boxShadow: "var(--shadow-card)",
            marginBottom: "32px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "20px",
          }}
        >
          <div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "4px 12px", background: "var(--powder-pink)", borderRadius: "100px", fontSize: "12px", fontWeight: "600", color: "var(--primary-text)", marginBottom: "8px" }}>
              <Sparkles size={14} style={{ color: "var(--accent-pink)" }} />
              Structured 5,000-Record Skills & Hobbies Catalog
            </div>
            <h1 style={{ fontSize: "28px", fontWeight: "800", color: "var(--primary-text)", margin: "0 0 8px 0" }}>
              Explore Skills, Hobbies & Applications
            </h1>
            <p style={{ color: "var(--secondary-text)", fontSize: "14px", margin: 0, maxWidth: "620px" }}>
              Discover skills across technical, behavioral, cognitive, and sector domains, plus {stats?.hobby_types_count ?? masterHobbies.length ?? 40} creative, athletic, and intellectual hobbies mapped across real-world application contexts and motivations.
            </p>
          </div>

          {stats && (
            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
              <div style={{ padding: "12px 18px", background: "var(--bg-secondary)", borderRadius: "14px", border: "1px solid var(--border-subtle)", textAlign: "center" }}>
                <span style={{ fontSize: "20px", fontWeight: "800", color: "var(--accent-pink)", display: "block" }}>{stats.total_records.toLocaleString()}</span>
                <span style={{ fontSize: "11px", color: "var(--secondary-text)", fontWeight: "600" }}>Dataset Records</span>
              </div>
              <div style={{ padding: "12px 18px", background: "var(--bg-secondary)", borderRadius: "14px", border: "1px solid var(--border-subtle)", textAlign: "center" }}>
                <span style={{ fontSize: "20px", fontWeight: "800", color: "var(--primary-text)", display: "block" }}>{stats.skill_types_count}</span>
                <span style={{ fontSize: "11px", color: "var(--secondary-text)", fontWeight: "600" }}>Skill Types</span>
              </div>
              <div style={{ padding: "12px 18px", background: "var(--bg-secondary)", borderRadius: "14px", border: "1px solid var(--border-subtle)", textAlign: "center" }}>
                <span style={{ fontSize: "20px", fontWeight: "800", color: "var(--primary-text)", display: "block" }}>{stats.hobby_types_count}</span>
                <span style={{ fontSize: "11px", color: "var(--secondary-text)", fontWeight: "600" }}>Hobby Types</span>
              </div>
            </div>
          )}
        </section>

        {/* Tab Buttons */}
        <div style={{ display: "flex", gap: "12px", marginBottom: "24px", borderBottom: "1.5px solid var(--border-subtle)", paddingBottom: "12px" }}>
          <button
            type="button"
            onClick={() => handleTabChange("skills")}
            style={{
              padding: "10px 20px",
              borderRadius: "12px",
              fontSize: "14px",
              fontWeight: "700",
              cursor: "pointer",
              border: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: activeTab === "skills" ? "var(--primary-pink)" : "transparent",
              color: activeTab === "skills" ? "#FFFFFF" : "var(--secondary-text)",
              transition: "all 0.15s ease",
            }}
          >
            <Wrench size={16} /> Skills Explorer ({stats?.skill_types_count ?? masterSkills.length ?? 38} Types)
          </button>

          <button
            type="button"
            onClick={() => handleTabChange("hobbies")}
            style={{
              padding: "10px 20px",
              borderRadius: "12px",
              fontSize: "14px",
              fontWeight: "700",
              cursor: "pointer",
              border: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: activeTab === "hobbies" ? "var(--primary-pink)" : "transparent",
              color: activeTab === "hobbies" ? "#FFFFFF" : "var(--secondary-text)",
              transition: "all 0.15s ease",
            }}
          >
            <Palette size={16} /> Hobbies Explorer ({stats?.hobby_types_count ?? masterHobbies.length ?? 40} Types)
          </button>

          <button
            type="button"
            onClick={() => handleTabChange("dataset")}
            style={{
              padding: "10px 20px",
              borderRadius: "12px",
              fontSize: "14px",
              fontWeight: "700",
              cursor: "pointer",
              border: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: activeTab === "dataset" ? "var(--primary-pink)" : "transparent",
              color: activeTab === "dataset" ? "#FFFFFF" : "var(--secondary-text)",
              transition: "all 0.15s ease",
            }}
          >
            <BookOpen size={16} /> Dataset Insights & Schema
          </button>
        </div>

        {/* Tab 1 & 2: Search & Filter Toolbar */}
        {activeTab !== "dataset" && (
          <div
            style={{
              background: "var(--bg-card)",
              padding: "20px",
              borderRadius: "18px",
              border: "1.5px solid var(--border-subtle)",
              marginBottom: "28px",
              boxShadow: "0 4px 16px rgba(244, 182, 194, 0.15)",
            }}
          >
            {/* Search Input */}
            <div style={{ display: "flex", gap: "10px", marginBottom: "16px", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: "260px", position: "relative" }}>
                <Search size={18} style={{ position: "absolute", left: "14px", top: "12px", color: "var(--secondary-text)" }} />
                <input
                  type="text"
                  value={q}
                  onChange={(e) => {
                    setQ(e.target.value);
                    setPage(1);
                  }}
                  placeholder={`Search ${activeTab === "skills" ? "skills (e.g., Coding, Graphic Design, Leadership)" : "hobbies (e.g., Drawing, Chess, Hiking)"}...`}
                  style={{
                    width: "100%",
                    padding: "10px 14px 10px 42px",
                    borderRadius: "12px",
                    border: "1.5px solid var(--border-subtle)",
                    background: "var(--bg-secondary)",
                    color: "var(--primary-text)",
                    fontSize: "14px",
                    outline: "none",
                  }}
                />
              </div>

              {(q || selectedCategory !== "All" || selectedContext || selectedProficiency || selectedSetting || selectedFrequency || selectedMotivation) && (
                <button
                  type="button"
                  onClick={resetFilters}
                  style={{
                    padding: "10px 16px",
                    borderRadius: "12px",
                    border: "1px solid var(--border-subtle)",
                    background: "var(--bg-card)",
                    color: "var(--secondary-text)",
                    fontSize: "13px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  Clear Filters
                </button>
              )}
            </div>

            {/* Category Pills */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "14px" }}>
              <button
                type="button"
                onClick={() => {
                  setSelectedCategory("All");
                  setPage(1);
                }}
                style={{
                  padding: "6px 12px",
                  borderRadius: "100px",
                  fontSize: "12px",
                  fontWeight: "600",
                  cursor: "pointer",
                  border: "1px solid var(--border-subtle)",
                  background: selectedCategory === "All" ? "var(--powder-pink)" : "var(--bg-secondary)",
                  color: "var(--primary-text)",
                }}
              >
                All Categories
              </button>
              {currentCategories.map((c) => (
                <button
                  key={c.category}
                  type="button"
                  onClick={() => {
                    setSelectedCategory(c.category);
                    setPage(1);
                  }}
                  style={{
                    padding: "6px 12px",
                    borderRadius: "100px",
                    fontSize: "12px",
                    fontWeight: "600",
                    cursor: "pointer",
                    border: "1px solid var(--border-subtle)",
                    background: selectedCategory === c.category ? "var(--powder-pink)" : "var(--bg-secondary)",
                    color: "var(--primary-text)",
                  }}
                >
                  {c.category} ({c.count})
                </button>
              ))}
            </div>

            {/* Granular Context & Attribute Selectors */}
            {facets && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", paddingTop: "12px", borderTop: "1px solid var(--border-subtle)" }}>
                {/* Application Context */}
                <select
                  value={selectedContext}
                  onChange={(e) => {
                    setSelectedContext(e.target.value);
                    setPage(1);
                  }}
                  style={{
                    padding: "6px 10px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-subtle)",
                    fontSize: "12px",
                    background: selectedContext ? "var(--powder-pink)" : "var(--bg-secondary)",
                    color: "var(--primary-text)",
                    outline: "none",
                  }}
                >
                  <option value="">Application Context (All)</option>
                  {facets.contexts.map((ctx) => (
                    <option key={ctx} value={ctx}>{ctx}</option>
                  ))}
                </select>

                {/* Proficiency / Engagement */}
                <select
                  value={selectedProficiency}
                  onChange={(e) => {
                    setSelectedProficiency(e.target.value);
                    setPage(1);
                  }}
                  style={{
                    padding: "6px 10px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-subtle)",
                    fontSize: "12px",
                    background: selectedProficiency ? "var(--powder-pink)" : "var(--bg-secondary)",
                    color: "var(--primary-text)",
                    outline: "none",
                  }}
                >
                  <option value="">Level (All)</option>
                  {facets.proficiencies.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>

                {/* Setting */}
                <select
                  value={selectedSetting}
                  onChange={(e) => {
                    setSelectedSetting(e.target.value);
                    setPage(1);
                  }}
                  style={{
                    padding: "6px 10px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-subtle)",
                    fontSize: "12px",
                    background: selectedSetting ? "var(--powder-pink)" : "var(--bg-secondary)",
                    color: "var(--primary-text)",
                    outline: "none",
                  }}
                >
                  <option value="">Setting (All)</option>
                  {facets.settings.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>

                {/* Hobbies Specific: Frequency & Motivation */}
                {activeTab === "hobbies" && (
                  <>
                    <select
                      value={selectedFrequency}
                      onChange={(e) => {
                        setSelectedFrequency(e.target.value);
                        setPage(1);
                      }}
                      style={{
                        padding: "6px 10px",
                        borderRadius: "8px",
                        border: "1px solid var(--border-subtle)",
                        fontSize: "12px",
                        background: selectedFrequency ? "var(--powder-pink)" : "var(--bg-secondary)",
                        color: "var(--primary-text)",
                        outline: "none",
                      }}
                    >
                      <option value="">Frequency (All)</option>
                      {facets.frequencies.map((f) => (
                        <option key={f} value={f}>{f}</option>
                      ))}
                    </select>

                    <select
                      value={selectedMotivation}
                      onChange={(e) => {
                        setSelectedMotivation(e.target.value);
                        setPage(1);
                      }}
                      style={{
                        padding: "6px 10px",
                        borderRadius: "8px",
                        border: "1px solid var(--border-subtle)",
                        fontSize: "12px",
                        background: selectedMotivation ? "var(--powder-pink)" : "var(--bg-secondary)",
                        color: "var(--primary-text)",
                        outline: "none",
                      }}
                    >
                      <option value="">Primary Motivation (All)</option>
                      {facets.motivations.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Results Grid */}
        {activeTab !== "dataset" && (
          <div>
            {loading ? (
              <div style={{ textAlign: "center", padding: "60px 0" }}>
                <LoaderCircle className="spin" size={36} style={{ color: "var(--accent-pink)", margin: "0 auto 12px auto" }} />
                <p style={{ color: "var(--secondary-text)" }}>Searching dataset...</p>
              </div>
            ) : searchResults.length === 0 ? (
              <div style={{ textAlign: "center", padding: "60px 0", background: "var(--bg-card)", borderRadius: "20px", border: "1px solid var(--border-subtle)" }}>
                <p style={{ color: "var(--secondary-text)", fontSize: "15px" }}>No dataset records matched your criteria.</p>
                <button
                  type="button"
                  onClick={resetFilters}
                  style={{ marginTop: "10px", padding: "8px 16px", borderRadius: "10px", background: "var(--primary-pink)", color: "#FFFFFF", border: "none", fontWeight: "600", cursor: "pointer" }}
                >
                  Reset Filters
                </button>
              </div>
            ) : (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "20px" }}>
                  {searchResults.map((item) => (
                    <div
                      key={item.record_id}
                      style={{
                        background: "var(--bg-card)",
                        padding: "24px",
                        borderRadius: "20px",
                        border: "1.5px solid var(--border-subtle)",
                        boxShadow: "var(--shadow-card)",
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "space-between",
                      }}
                    >
                      <div>
                        {/* Top Badges */}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", gap: "8px" }}>
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: "700",
                              padding: "2px 8px",
                              borderRadius: "6px",
                              background: item.record_type === "Skill" ? "var(--powder-pink)" : "rgba(224, 138, 154, 0.2)",
                              color: "var(--primary-text)",
                            }}
                          >
                            {item.category}
                          </span>
                          <span style={{ fontSize: "11px", color: "var(--secondary-text)", fontWeight: "600" }}>
                            ID: {item.record_id}
                          </span>
                        </div>

                        {/* Title */}
                        <h3 style={{ fontSize: "18px", fontWeight: "800", color: "var(--primary-text)", margin: "0 0 6px 0" }}>
                          {item.type}
                        </h3>
                        <p style={{ fontSize: "13px", color: "var(--secondary-text)", margin: "0 0 14px 0", lineHeight: "1.45" }}>
                          {item.description}
                        </p>

                        {/* Context Attributes */}
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "14px" }}>
                          <span style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "8px", background: "var(--bg-secondary)", color: "var(--primary-text)", border: "1px solid var(--border-subtle)" }}>
                            Context: <strong>{item.application_context}</strong>
                          </span>
                          <span style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "8px", background: "var(--bg-secondary)", color: "var(--primary-text)", border: "1px solid var(--border-subtle)" }}>
                            Level: <strong>{item.proficiency_engagement_level}</strong>
                          </span>
                          <span style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "8px", background: "var(--bg-secondary)", color: "var(--primary-text)", border: "1px solid var(--border-subtle)" }}>
                            Setting: <strong>{item.setting}</strong>
                          </span>
                          {item.frequency && (
                            <span style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "8px", background: "var(--bg-secondary)", color: "var(--primary-text)", border: "1px solid var(--border-subtle)" }}>
                              Freq: <strong>{item.frequency}</strong>
                            </span>
                          )}
                          {item.primary_motivation && (
                            <span style={{ fontSize: "11px", padding: "3px 8px", borderRadius: "8px", background: "rgba(216, 75, 117, 0.12)", color: "var(--accent-pink)", border: "1px solid var(--border-subtle)", fontWeight: "600" }}>
                              Motivation: {item.primary_motivation}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Footer & Popularity Score */}
                      <div style={{ paddingTop: "12px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                          <Star size={14} style={{ color: "var(--accent-pink)", fill: "var(--accent-pink)" }} />
                          <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary-text)" }}>
                            Popularity: {item.popularity_score} / 10
                          </span>
                        </div>

                        <span style={{ fontSize: "11px", color: "var(--secondary-text)", fontStyle: "italic" }}>
                          {item.expanded_record_description.slice(0, 50)}...
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "16px", marginTop: "32px" }}>
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
                  <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--primary-text)" }}>
                    Page {page} ({totalFound} records shown)
                  </span>
                  <button
                    type="button"
                    disabled={searchResults.length < 24}
                    onClick={() => setPage((p) => p + 1)}
                    style={{
                      padding: "8px 18px",
                      borderRadius: "10px",
                      border: "1px solid var(--border-subtle)",
                      background: searchResults.length < 24 ? "var(--bg-secondary)" : "var(--bg-card)",
                      color: searchResults.length < 24 ? "var(--secondary-text)" : "var(--primary-text)",
                      fontSize: "13px",
                      fontWeight: "600",
                      cursor: searchResults.length < 24 ? "not-allowed" : "pointer",
                    }}
                  >
                    Next
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Tab 3: Dataset Insights & Schema */}
        {activeTab === "dataset" && stats && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div style={{ background: "var(--bg-card)", padding: "28px", borderRadius: "20px", border: "1.5px solid var(--border-subtle)" }}>
              <h2 style={{ fontSize: "20px", fontWeight: "800", color: "var(--primary-text)", marginBottom: "16px" }}>
                PostgreSQL Dataset Architecture
              </h2>
              <p style={{ color: "var(--secondary-text)", fontSize: "14px", lineHeight: "1.6", marginBottom: "20px" }}>
                The ALIGN skills and hobbies catalog is normalized into three PostgreSQL relational tables:
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                <div style={{ padding: "18px", background: "var(--bg-secondary)", borderRadius: "14px", border: "1px solid var(--border-subtle)" }}>
                  <h4 style={{ margin: "0 0 6px 0", color: "var(--accent-pink)", fontSize: "15px" }}>skills_hobbies_dataset</h4>
                  <p style={{ fontSize: "12px", color: "var(--secondary-text)", margin: "0 0 8px 0" }}>
                    Full 5,000 granular application records with contexts, proficiencies, settings, frequencies, motivations, and popularity scores.
                  </p>
                  <strong style={{ fontSize: "13px", color: "var(--primary-text)" }}>{stats.total_records.toLocaleString()} rows</strong>
                </div>

                <div style={{ padding: "18px", background: "var(--bg-secondary)", borderRadius: "14px", border: "1px solid var(--border-subtle)" }}>
                  <h4 style={{ margin: "0 0 6px 0", color: "var(--accent-pink)", fontSize: "15px" }}>skill_master</h4>
                  <p style={{ fontSize: "12px", color: "var(--secondary-text)", margin: "0 0 8px 0" }}>
                    Normalized master catalog of unique skills across Technical, Behavioral, Cognitive, and Sector-specific disciplines.
                  </p>
                  <strong style={{ fontSize: "13px", color: "var(--primary-text)" }}>{stats.skill_types_count} skill types</strong>
                </div>

                <div style={{ padding: "18px", background: "var(--bg-secondary)", borderRadius: "14px", border: "1px solid var(--border-subtle)" }}>
                  <h4 style={{ margin: "0 0 6px 0", color: "var(--accent-pink)", fontSize: "15px" }}>hobby_master</h4>
                  <p style={{ fontSize: "12px", color: "var(--secondary-text)", margin: "0 0 8px 0" }}>
                    Normalized master catalog of unique hobbies across Arts, Sports, Intellectual, Nature, and Craft categories.
                  </p>
                  <strong style={{ fontSize: "13px", color: "var(--primary-text)" }}>{stats.hobby_types_count} hobby types</strong>
                </div>
              </div>
            </div>

            {/* Categories Breakdown */}
            <div style={{ background: "var(--bg-card)", padding: "28px", borderRadius: "20px", border: "1.5px solid var(--border-subtle)" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "800", color: "var(--primary-text)", marginBottom: "16px" }}>
                Category Distribution ({stats.categories.length} Categories)
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
                {stats.categories.map((c) => (
                  <div key={c.category} style={{ padding: "16px", borderRadius: "12px", border: "1px solid var(--border-subtle)", background: "var(--bg-secondary)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <strong style={{ fontSize: "14px", color: "var(--primary-text)" }}>{c.category}</strong>
                      <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--accent-pink)", background: "var(--bg-card)", padding: "2px 8px", borderRadius: "8px" }}>
                        {c.count} records
                      </span>
                    </div>
                    <p style={{ fontSize: "11px", color: "var(--secondary-text)", margin: 0 }}>
                      Sample types: {c.sample_types.join(", ")}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
