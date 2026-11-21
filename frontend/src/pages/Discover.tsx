import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, Bookmark, CalendarDays, Check, Code2, Compass, ExternalLink, Globe, LoaderCircle, MapPin, Search, Sparkles, User, Users } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import SearchBar from "../components/common/SearchBar";
import CategoryChips from "../components/common/CategoryChips";
import WhyThisPopover from "../components/common/WhyThisPopover";
import { api, DiscoveryResult } from "../lib/api";
import EventRegistrationModal from "../components/EventRegistrationModal";
import { SafeAvatar } from "../components/common/SafeImage";

const CATEGORIES = ["All", "People", "Technology", "Outdoors", "Design", "Career", "Arts"];

export default function Discover() {
  const [query, setQuery] = useState(() => sessionStorage.getItem("align_search_query") || "");
  const [results, setResults] = useState<DiscoveryResult[]>([]);
  const [recommendations, setRecommendations] = useState<DiscoveryResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [error, setError] = useState("");
  const [selectedCat, setSelectedCat] = useState("All");
  const [savingId, setSavingId] = useState<string | null>(null);
  const [selectedEventForReg, setSelectedEventForReg] = useState<DiscoveryResult | null>(null);

  const navigate = useNavigate();
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    if (query.trim()) {
      void search(query);
    }
    if (loggedIn) {
      void loadRecommendations();
    }
  }, []);

  async function loadRecommendations() {
    setLoadingRecs(true);
    try {
      const recs = await api.recommendations(6);
      setRecommendations(recs);
    } catch {
      // Graceful ignore if recommendations endpoint has no profile yet
    } finally {
      setLoadingRecs(false);
    }
  }

  async function search(value: string, cat = selectedCat) {
    if (!value.trim()) return;
    setLoading(true);
    setError("");
    sessionStorage.setItem("align_search_query", value);
    try {
      const categoryParam = cat === "All" ? undefined : cat;
      const data = await api.search(value, undefined, undefined, categoryParam);
      setResults(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not search. Is the API service running?");
    } finally {
      setLoading(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    void search(query, selectedCat);
  }

  async function saveItem(result: DiscoveryResult) {
    if (!loggedIn) {
      navigate("/login?next=/discover");
      return;
    }
    const key = `${result.result_type}-${result.id}`;
    setSavingId(key);
    try {
      if (result.result_type === "community" || result.result_type === "event" || result.result_type === "place") {
        await api.saveItem(result.result_type, result.id);
        alert(`Saved ${result.title} to your bookmarks!`);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to bookmark item.");
    } finally {
      setSavingId(null);
    }
  }

  async function takeAction(result: DiscoveryResult) {
    if (!loggedIn) {
      navigate("/login?next=/discover");
      return;
    }
    try {
      if (result.result_type === "community") {
        await api.joinCommunity(result.id);
        alert(`Joined ${result.title}!`);
      } else if (result.result_type === "event") {
        await api.registerEvent(result.id);
        alert(`RSVP confirmed for ${result.title}!`);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Action failed.");
    }
  }

  return (
    <AppShell title="Explore">
      <p className="eyebrow">The discovery desk</p>
      <h1 className="page-title">Follow your curiosity.</h1>
      <p className="lead" style={{ margin: "0 0 24px 0" }}>
        Search communities, upcoming gatherings, and beautiful places in one space using semantic AI matching.
      </p>

      {/* Toolbar */}
      <div className="toolbar">
        <SearchBar
          value={query}
          onChange={(val) => {
            setQuery(val);
            if (val.trim()) void search(val);
          }}
          placeholder="Search discoveries, AI groups, weekend hikes, photography..."
        />
        <Link to="/places" className="button">
          <MapPin size={16} /> Explore places
        </Link>
      </div>

      {/* Category Chips */}
      <CategoryChips
        categories={CATEGORIES}
        activeCategory={selectedCat}
        onSelect={(cat) => {
          setSelectedCat(cat);
          if (query.trim()) void search(query, cat);
        }}
      />

        {error && (
          <div className="error-box">
            {error}
            <p>Ensure backend service is running and PostgreSQL is connected.</p>
          </div>
        )}

        {loading && (
          <div className="empty-state">
            <LoaderCircle className="spin" size={26} />
            <p>Searching vectors and intent embeddings…</p>
          </div>
        )}

        {/* Search Results */}
        {!loading && results.length > 0 && (
          <section className="results-section">
            <div className="results-heading">
              <h2>Matched for your intent</h2>
              <span>{results.length} matches</span>
            </div>
            <div className="results-grid">
              {results.map((r) => {
                const key = `${r.result_type}-${r.id}`;
                const isEb =
                  r.result_type === "event" &&
                  (r.is_eventbrite ||
                    r.source === "Eventbrite" ||
                    (r.description && r.description.toLowerCase().includes("eventbrite")));
                const isUser = r.result_type === "user";

                return (
                  <article className="result-card" key={key}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      {isUser && r.avatar_url ? (
                        <SafeAvatar
                          src={r.avatar_url}
                          name={r.title}
                          size={44}
                          style={{ border: "2px solid var(--accent-pink)" }}
                        />
                      ) : (
                        <div className={`result-icon ${r.result_type === "community" ? "lilac" : "pink"}`}>
                          {isUser ? <User size={19} /> : r.result_type === "community" ? <Users size={19} /> : <CalendarDays size={19} />}
                        </div>
                      )}

                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        {isEb && (
                          <span
                            style={{
                              fontSize: "10px",
                              fontWeight: "700",
                              padding: "3px 9px",
                              borderRadius: "100px",
                              background: "var(--powder-pink)",
                              color: "var(--primary-text)",
                              border: "1px solid var(--border-subtle)",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                            }}
                          >
                            <Globe size={11} style={{ color: "var(--accent-pink)" }} /> Eventbrite Live
                          </span>
                        )}

                        {isUser && (
                          <span
                            style={{
                              fontSize: "10px",
                              fontWeight: "700",
                              padding: "3px 9px",
                              borderRadius: "100px",
                              background: "var(--bg-secondary)",
                              color: "var(--primary-text)",
                              border: "1px solid var(--border-subtle)",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                            }}
                          >
                            <Code2 size={11} style={{ color: "var(--accent-pink)" }} /> GitHub Developer
                          </span>
                        )}

                        <button
                          onClick={() => saveItem(r)}
                          disabled={savingId === key}
                          title="Save to bookmarks"
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--secondary-text)",
                            padding: "6px",
                            cursor: "pointer",
                            transition: "color .2s",
                          }}
                        >
                          <Bookmark size={18} />
                        </button>
                      </div>
                    </div>

                    <div className="result-type">
                      {isEb
                        ? "EVENT · EVENTBRITE LIVE"
                        : isUser
                        ? "PEOPLE · GITHUB SKILLS"
                        : `${r.result_type.toUpperCase()} · ${r.category}`}
                    </div>
                    <h3>{r.title}</h3>
                    <p>{r.description}</p>

                    {/* Skills pills for developers/people */}
                    {isUser && r.tags && (
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", margin: "8px 0" }}>
                        {r.tags.split(",").slice(0, 5).map((skill) => (
                          <span
                            key={skill}
                            style={{
                              fontSize: "10px",
                              padding: "3px 8px",
                              borderRadius: "8px",
                              background: "var(--bg-main)",
                              color: "var(--secondary-text)",
                              border: "1px solid var(--border-subtle)",
                              fontWeight: "600",
                            }}
                          >
                            {skill.trim()}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="result-location">
                      <MapPin size={14} style={{ color: "var(--accent-pink)" }} />
                      {r.location}
                      {r.distance_km !== null && r.distance_km !== undefined && (
                        <span style={{ color: "var(--accent-pink)", fontWeight: "600", marginLeft: "auto" }}>
                          {r.distance_km} km
                        </span>
                      )}
                    </div>

                    <div className="match-reason">
                      <Sparkles size={14} />
                      <span>{r.reason}</span>
                    </div>

                    <div className="score-row" style={{ marginTop: "10px" }}>
                      <span>Relevance</span>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <WhyThisPopover
                          score={r.score}
                          whyRecommended={r.why_recommended}
                          scoreBreakdown={r.score_breakdown}
                          matchedTerms={r.matched_terms}
                          graphPath={r.graph_path}
                          title={r.title}
                        />
                        <b>{Math.round(r.score * 100)}%</b>
                      </div>
                    </div>
                    <div className="score-track">
                      <span style={{ width: `${Math.round(r.score * 100)}%` }} />
                    </div>

                    <div className="score-row">
                      <span>Intent relevance</span>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <WhyThisPopover
                          score={r.score}
                          whyRecommended={r.why_recommended}
                          scoreBreakdown={r.score_breakdown}
                          matchedTerms={r.matched_terms}
                          graphPath={r.graph_path}
                          title={r.title}
                        />
                        <b>{Math.round(r.score * 100)}%</b>
                      </div>
                    </div>
                    <div className="score-track">
                      <span style={{ width: `${Math.round(r.score * 100)}%` }} />
                    </div>

                    {isUser ? (
                      <a
                        href={r.profile_url || `https://github.com/${r.title}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          width: "100%",
                          marginTop: "16px",
                          padding: "10px",
                          borderRadius: "12px",
                          border: "1px solid var(--border-subtle)",
                          background: "var(--bg-card)",
                          color: "var(--primary-text)",
                          fontSize: "12px",
                          fontWeight: "700",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "6px",
                          textDecoration: "none",
                          boxShadow: "var(--card-shadow)",
                          transition: "all .2s ease",
                        }}
                      >
                        <ExternalLink size={14} /> Connect on GitHub
                      </a>
                    ) : (
                      <button
                        onClick={() => {
                          if (r.result_type === "event") {
                            setSelectedEventForReg(r);
                          } else {
                            takeAction(r);
                          }
                        }}
                        style={{
                          width: "100%",
                          marginTop: "16px",
                          padding: "11px",
                          borderRadius: "12px",
                          border: "none",
                          background: "var(--button-pink)",
                          color: "#FFFFFF",
                          fontSize: "12px",
                          fontWeight: "700",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "6px",
                          boxShadow: "0 4px 12px rgba(232, 160, 176, 0.35)",
                          transition: "all .2s ease",
                        }}
                      >
                        {r.result_type === "community"
                          ? "Join Community"
                          : isEb
                          ? "Register for Event (Eventbrite Live)"
                          : "Register for Event"}
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
        )}

        {/* Personalized Recommendations for Logged In User */}
        {!loading && loggedIn && recommendations.length > 0 && (
          <section className="results-section" style={{ marginTop: "55px", borderTop: "1px solid var(--border-subtle)", paddingTop: "35px" }}>
            <div className="results-heading">
              <div>
                <div className="eyebrow" style={{ marginBottom: "5px" }}>
                  <Sparkles size={13} style={{ color: "var(--accent-pink)" }} /> CURATED FOR YOU
                </div>
                <h2>Recommended from your profile intent</h2>
              </div>
              <span>{recommendations.length} suggestions</span>
            </div>
            <div className="results-grid">
              {recommendations.map((r) => {
                const isEb =
                  r.result_type === "event" &&
                  (r.is_eventbrite ||
                    r.source === "Eventbrite" ||
                    (r.description && r.description.toLowerCase().includes("eventbrite")));

                return (
                  <article className="result-card" key={`rec-${r.result_type}-${r.id}`}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div className={`result-icon ${r.result_type === "community" ? "lilac" : "pink"}`}>
                        {r.result_type === "community" ? <Users size={19} /> : <CalendarDays size={19} />}
                      </div>

                      {isEb && (
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: "700",
                            padding: "3px 9px",
                            borderRadius: "100px",
                            background: "var(--powder-pink)",
                            color: "var(--primary-text)",
                            border: "1px solid var(--border-subtle)",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <Globe size={11} style={{ color: "var(--accent-pink)" }} /> Eventbrite Live
                        </span>
                      )}
                    </div>

                    <div className="result-type">
                      {isEb ? "EVENT · EVENTBRITE LIVE" : `${r.result_type.toUpperCase()} · ${r.category}`}
                    </div>
                    <h3>{r.title}</h3>
                    <p>{r.description}</p>
                    <div className="result-location">
                      <MapPin size={14} style={{ color: "var(--accent-pink)" }} />
                      {r.location}
                    </div>
                    <div className="match-reason">
                      <Sparkles size={14} />
                      <span>{r.reason}</span>
                    </div>

                    <div className="score-row" style={{ marginTop: "10px" }}>
                      <span>Relevance</span>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <WhyThisPopover
                          score={r.score}
                          whyRecommended={r.why_recommended}
                          scoreBreakdown={r.score_breakdown}
                          matchedTerms={r.matched_terms}
                          graphPath={r.graph_path}
                          title={r.title}
                        />
                        <b>{Math.round(r.score * 100)}%</b>
                      </div>
                    </div>
                    <div className="score-track">
                      <span style={{ width: `${Math.round(r.score * 100)}%` }} />
                    </div>

                    {r.result_type === "event" && (
                      <button
                        onClick={() => setSelectedEventForReg(r)}
                        style={{
                          width: "100%",
                          marginTop: "14px",
                          padding: "10px",
                          borderRadius: "12px",
                          border: "none",
                          background: "var(--button-pink)",
                          color: "#FFFFFF",
                          fontSize: "12px",
                          fontWeight: "700",
                          cursor: "pointer",
                          boxShadow: "0 3px 10px rgba(232, 160, 176, 0.35)",
                          transition: "all .2s ease",
                        }}
                      >
                        {isEb ? "Register (Eventbrite Live)" : "Register RSVP"}
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
        )}

        {/* Empty state suggestions */}
        {!loading && !error && results.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">
              <Search size={26} />
            </div>
            <h2>Start with a thought</h2>
            <p>Search for a hobby, skill, goal, community, or experience to see matches here.</p>
            <div className="suggestions">
              {[
                "AI and machine learning projects",
                "Weekend trail hikes and photography in Pune",
                "Product design and UX portfolio reviews",
                "Women in technology mentorship",
                "Creative makers and side projects",
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setQuery(s);
                    void search(s);
                  }}
                >
                  {s}
                  <ArrowRight size={14} />
                </button>
              ))}
            </div>
          </div>
        )}
        {/* Event Registration Modal */}
        <EventRegistrationModal
          isOpen={selectedEventForReg !== null}
          onClose={() => setSelectedEventForReg(null)}
          event={selectedEventForReg}
          onSuccess={(eventId, result) => {
            alert(`🎉 ${result.message}\nPass Reference: ${result.ticket_code || "Confirmed"}`);
          }}
        />
    </AppShell>
  );
}
