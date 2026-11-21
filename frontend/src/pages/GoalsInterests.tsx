import { useEffect, useState } from "react";
import { Compass, Search, Target, Sparkles } from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, GoalMaster, InterestMaster, CategorySummary, GoalInterestDatasetItem } from "../lib/api";

type Tab = "goals" | "interests";

export default function GoalsInterests() {
  const [tab, setTab] = useState<Tab>("goals");

  // Goals state
  const [goalMasters, setGoalMasters] = useState<GoalMaster[]>([]);
  const [goalCats, setGoalCats] = useState<CategorySummary[]>([]);
  const [goalSearchResults, setGoalSearchResults] = useState<GoalInterestDatasetItem[]>([]);
  const [goalCategory, setGoalCategory] = useState("All");
  const [goalQ, setGoalQ] = useState("");
  const [goalMinPop, setGoalMinPop] = useState(1);
  const [goalLoading, setGoalLoading] = useState(true);

  // Interests state
  const [interestMasters, setInterestMasters] = useState<InterestMaster[]>([]);
  const [interestCats, setInterestCats] = useState<CategorySummary[]>([]);
  const [interestSearchResults, setInterestSearchResults] = useState<GoalInterestDatasetItem[]>([]);
  const [interestCategory, setInterestCategory] = useState("All");
  const [interestQ, setInterestQ] = useState("");
  const [interestMinPop, setInterestMinPop] = useState(1);
  const [interestLoading, setInterestLoading] = useState(true);

  // Stats
  const [stats, setStats] = useState<{ total_records: number; goals_count: number; interests_count: number; goal_types_count: number; interest_types_count: number } | null>(null);

  useEffect(() => {
    Promise.all([
      api.goals({ limit: 200 }).catch(() => []),
      api.goalCategories().catch(() => []),
      api.interests({ limit: 200 }).catch(() => []),
      api.interestCategories().catch(() => []),
      api.goalsInterestsStats().catch(() => null),
    ]).then(([gMasters, gCats, iMasters, iCats, s]) => {
      setGoalMasters(gMasters);
      setGoalCats(gCats);
      setInterestMasters(iMasters);
      setInterestCats(iCats);
      if (s) setStats(s);
      setGoalLoading(false);
      setInterestLoading(false);
    });
  }, []);

  useEffect(() => {
    if (tab !== "goals") return;
    setGoalLoading(true);
    api.searchGoals({
      q: goalQ || undefined,
      category: goalCategory !== "All" ? goalCategory : undefined,
      min_popularity: goalMinPop > 1 ? goalMinPop : undefined,
      limit: 60,
    }).then((res) => {
      setGoalSearchResults(res);
      setGoalLoading(false);
    }).catch(() => setGoalLoading(false));
  }, [tab, goalQ, goalCategory, goalMinPop]);

  useEffect(() => {
    if (tab !== "interests") return;
    setInterestLoading(true);
    api.searchInterests({
      q: interestQ || undefined,
      category: interestCategory !== "All" ? interestCategory : undefined,
      min_popularity: interestMinPop > 1 ? interestMinPop : undefined,
      limit: 60,
    }).then((res) => {
      setInterestSearchResults(res);
      setInterestLoading(false);
    }).catch(() => setInterestLoading(false));
  }, [tab, interestQ, interestCategory, interestMinPop]);

  const inputStyle: React.CSSProperties = {
    padding: "9px 14px",
    borderRadius: "10px",
    border: "1.5px solid var(--border-subtle)",
    background: "var(--bg-secondary)",
    color: "var(--primary-text)",
    fontSize: "13px",
    outline: "none",
  };

  const chipStyle = (active: boolean): React.CSSProperties => ({
    padding: "5px 12px",
    borderRadius: "100px",
    fontSize: "12px",
    fontWeight: "600",
    cursor: "pointer",
    border: "1px solid var(--border-subtle)",
    background: active ? "var(--primary-pink)" : "var(--bg-secondary)",
    color: active ? "#FFFFFF" : "var(--primary-text)",
    transition: "all 0.15s ease",
  });

  return (
    <AppShell title="Goals & Interests">
      <div style={{ maxWidth: "960px", margin: "0 auto" }}>

        {/* Header */}
        <div style={{ marginBottom: "28px" }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "4px 14px", borderRadius: "100px", background: "var(--powder-pink)", color: "var(--primary-text)", fontSize: "12px", fontWeight: "600", marginBottom: "10px" }}>
            <Sparkles size={13} style={{ color: "var(--accent-pink)" }} />
            Goals &amp; Interests Dataset
          </span>
          <h1 style={{ fontSize: "28px", fontWeight: "800", color: "var(--primary-text)", margin: "0 0 6px 0" }}>
            Goals &amp; Interests Explorer
          </h1>
          <p style={{ color: "var(--secondary-text)", fontSize: "14px", margin: 0 }}>
            Browse 10,000 structured goals and interest records powering ALIGN's recommendation engine.
          </p>
          {stats && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "16px" }}>
              {[
                { label: "Total Records", value: stats.total_records.toLocaleString() },
                { label: "Goal Types", value: stats.goal_types_count },
                { label: "Interest Types", value: stats.interest_types_count },
                { label: "Goals", value: stats.goals_count.toLocaleString() },
                { label: "Interests", value: stats.interests_count.toLocaleString() },
              ].map((s) => (
                <div key={s.label} style={{ padding: "10px 18px", background: "var(--bg-card)", borderRadius: "12px", border: "1.5px solid var(--border-subtle)", textAlign: "center" }}>
                  <div style={{ fontSize: "20px", fontWeight: "800", color: "var(--accent-pink)" }}>{s.value}</div>
                  <div style={{ fontSize: "11px", color: "var(--secondary-text)", fontWeight: "600" }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
          {(["goals", "interests"] as Tab[]).map((t) => (
            <button key={t} type="button" onClick={() => setTab(t)} style={{ padding: "8px 20px", borderRadius: "10px", fontWeight: "700", fontSize: "14px", cursor: "pointer", border: "1.5px solid var(--border-subtle)", background: tab === t ? "var(--primary-pink)" : "var(--bg-secondary)", color: tab === t ? "#FFF" : "var(--primary-text)", transition: "all 0.2s ease" }}>
              {t === "goals" ? <><Target size={14} style={{ marginRight: "6px", verticalAlign: "middle" }} />Goals</> : <><Compass size={14} style={{ marginRight: "6px", verticalAlign: "middle" }} />Interests</>}
            </button>
          ))}
        </div>

        {/* GOALS TAB */}
        {tab === "goals" && (
          <div>
            {/* Master quick-chips */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "7px", marginBottom: "16px" }}>
              <button type="button" style={chipStyle(goalCategory === "All")} onClick={() => setGoalCategory("All")}>All ({goalMasters.length})</button>
              {goalCats.map((c) => (
                <button key={c.category} type="button" style={chipStyle(goalCategory === c.category)} onClick={() => setGoalCategory(c.category)}>
                  {c.category} ({c.count})
                </button>
              ))}
            </div>

            {/* Search & filter bar */}
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "20px", alignItems: "center" }}>
              <div style={{ position: "relative", flex: "1 1 220px" }}>
                <Search size={14} style={{ position: "absolute", left: "10px", top: "11px", color: "var(--secondary-text)" }} />
                <input type="text" value={goalQ} onChange={(e) => setGoalQ(e.target.value)} placeholder="Search goals..." style={{ ...inputStyle, paddingLeft: "30px", width: "100%", boxSizing: "border-box" }} />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <label style={{ fontSize: "12px", color: "var(--secondary-text)", whiteSpace: "nowrap" }}>Min popularity:</label>
                <select value={goalMinPop} onChange={(e) => setGoalMinPop(Number(e.target.value))} style={{ ...inputStyle, padding: "8px" }}>
                  {[1, 5, 7, 8, 9].map((v) => <option key={v} value={v}>{v}+</option>)}
                </select>
              </div>
            </div>

            {/* Results grid */}
            {goalLoading ? (
              <p style={{ color: "var(--secondary-text)", textAlign: "center" }}>Loading goals...</p>
            ) : goalSearchResults.length === 0 ? (
              <p style={{ color: "var(--secondary-text)", textAlign: "center" }}>No goals matched your filters.</p>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "14px" }}>
                {goalSearchResults.map((item) => (
                  <div key={item.id} style={{ padding: "16px", background: "var(--bg-card)", borderRadius: "14px", border: "1.5px solid var(--border-subtle)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "6px" }}>
                      <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--primary-text)" }}>{item.type}</span>
                      <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "100px", background: "var(--powder-pink)", color: "var(--accent-pink)", fontWeight: "700", whiteSpace: "nowrap" }}>★ {item.popularity_score}</span>
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--accent-pink)", fontWeight: "600", marginBottom: "6px" }}>{item.category}</div>
                    <p style={{ fontSize: "12px", color: "var(--secondary-text)", margin: "0 0 6px 0", lineHeight: "1.5" }}>{item.description}</p>
                    {item.life_context && <div style={{ fontSize: "11px", color: "var(--secondary-text)" }}>📍 {item.life_context}</div>}
                    {item.timeline_engagement_level && <div style={{ fontSize: "11px", color: "var(--secondary-text)" }}>⏱ {item.timeline_engagement_level}</div>}
                    {item.priority_setting && <div style={{ fontSize: "11px", color: "var(--secondary-text)" }}>🎯 {item.priority_setting}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* INTERESTS TAB */}
        {tab === "interests" && (
          <div>
            {/* Master quick-chips */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "7px", marginBottom: "16px" }}>
              <button type="button" style={chipStyle(interestCategory === "All")} onClick={() => setInterestCategory("All")}>All ({interestMasters.length})</button>
              {interestCats.map((c) => (
                <button key={c.category} type="button" style={chipStyle(interestCategory === c.category)} onClick={() => setInterestCategory(c.category)}>
                  {c.category} ({c.count})
                </button>
              ))}
            </div>

            {/* Search & filter bar */}
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "20px", alignItems: "center" }}>
              <div style={{ position: "relative", flex: "1 1 220px" }}>
                <Search size={14} style={{ position: "absolute", left: "10px", top: "11px", color: "var(--secondary-text)" }} />
                <input type="text" value={interestQ} onChange={(e) => setInterestQ(e.target.value)} placeholder="Search interests..." style={{ ...inputStyle, paddingLeft: "30px", width: "100%", boxSizing: "border-box" }} />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <label style={{ fontSize: "12px", color: "var(--secondary-text)", whiteSpace: "nowrap" }}>Min popularity:</label>
                <select value={interestMinPop} onChange={(e) => setInterestMinPop(Number(e.target.value))} style={{ ...inputStyle, padding: "8px" }}>
                  {[1, 5, 7, 8, 9].map((v) => <option key={v} value={v}>{v}+</option>)}
                </select>
              </div>
            </div>

            {/* Results grid */}
            {interestLoading ? (
              <p style={{ color: "var(--secondary-text)", textAlign: "center" }}>Loading interests...</p>
            ) : interestSearchResults.length === 0 ? (
              <p style={{ color: "var(--secondary-text)", textAlign: "center" }}>No interests matched your filters.</p>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "14px" }}>
                {interestSearchResults.map((item) => (
                  <div key={item.id} style={{ padding: "16px", background: "var(--bg-card)", borderRadius: "14px", border: "1.5px solid var(--border-subtle)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "6px" }}>
                      <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--primary-text)" }}>{item.type}</span>
                      <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "100px", background: "var(--powder-pink)", color: "var(--accent-pink)", fontWeight: "700", whiteSpace: "nowrap" }}>★ {item.popularity_score}</span>
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--accent-pink)", fontWeight: "600", marginBottom: "6px" }}>{item.category}</div>
                    <p style={{ fontSize: "12px", color: "var(--secondary-text)", margin: "0 0 6px 0", lineHeight: "1.5" }}>{item.description}</p>
                    {item.life_context && <div style={{ fontSize: "11px", color: "var(--secondary-text)" }}>📍 {item.life_context}</div>}
                    {item.timeline_engagement_level && <div style={{ fontSize: "11px", color: "var(--secondary-text)" }}>⏱ {item.timeline_engagement_level}</div>}
                    {item.status_frequency && <div style={{ fontSize: "11px", color: "var(--secondary-text)" }}>🔁 {item.status_frequency}</div>}
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
