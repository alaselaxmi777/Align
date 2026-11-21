import { useEffect, useState } from "react";
import {
  Briefcase,
  Bookmark,
  ExternalLink,
  Search,
  Filter,
  Sparkles,
  Clock,
  MapPin,
  Award,
  Globe,
  Share2,
  BookmarkCheck,
} from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, OpportunityItem, sanitizeExternalUrl } from "../lib/api";

const OPPORTUNITY_TYPES = [
  { label: "All Opportunities", value: "" },
  { label: "Hackathons", value: "hackathon" },
  { label: "Internships", value: "internship" },
  { label: "Scholarships", value: "scholarship" },
  { label: "Fellowships", value: "fellowship" },
  { label: "Competitions", value: "competition" },
];

export default function Opportunities() {
  const [opportunities, setOpportunities] = useState<OpportunityItem[]>([]);
  const [selectedType, setSelectedType] = useState("");
  const [remoteOnly, setRemoteOnly] = useState<boolean | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState("");
  const [bookmarksOnly, setBookmarksOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [bookmarkingId, setBookmarkingId] = useState<number | null>(null);

  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    loadOpportunities();
  }, [selectedType, remoteOnly, bookmarksOnly]);

  async function loadOpportunities(search = searchQuery) {
    setLoading(true);
    setError("");
    try {
      if (bookmarksOnly) {
        const data = await api.myBookmarkedOpportunities();
        setOpportunities(data);
      } else {
        const data = await api.opportunities(search, selectedType, remoteOnly);
        setOpportunities(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load opportunities");
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    loadOpportunities(searchQuery.trim());
  }

  async function handleToggleBookmark(id: number) {
    if (!loggedIn) {
      alert("Please sign in to save opportunities.");
      return;
    }
    setBookmarkingId(id);
    try {
      const res = await api.toggleBookmarkOpportunity(id);
      setOpportunities((prev) =>
        prev.map((o) => (o.id === id ? { ...o, is_bookmarked: res.is_bookmarked } : o))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to bookmark");
    } finally {
      setBookmarkingId(null);
    }
  }

  return (
    <AppShell title="Opportunities">
      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "20px 16px 80px" }}>
        {/* Header Hero */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(83,101,245,0.08) 0%, rgba(16,185,129,0.06) 100%)",
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
              <Briefcase size={14} /> Verified Student & Builder Openings
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px" }}>
              Curated Opportunities
            </h1>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0, maxWidth: 640 }}>
              Discover verified hackathons, technology internships, research fellowships, and merit scholarships. No expired links or phantom job postings.
            </p>
          </div>

          {loggedIn && (
            <button
              onClick={() => setBookmarksOnly(!bookmarksOnly)}
              className="btn btn-secondary"
              style={{
                borderRadius: 10,
                padding: "10px 16px",
                fontSize: 13,
                fontWeight: 600,
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: bookmarksOnly ? "rgba(83,101,245,0.1)" : "var(--bg-card)",
                borderColor: bookmarksOnly ? "var(--accent-primary)" : "var(--border-color)",
                color: bookmarksOnly ? "var(--accent-primary)" : "var(--text-primary)",
              }}
            >
              {bookmarksOnly ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
              {bookmarksOnly ? "Showing Saved Only" : "My Saved Opportunities"}
            </button>
          )}
        </div>

        {/* Filter Bar */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", marginBottom: 20 }}>
          <form onSubmit={handleSearch} style={{ flex: "1 1 260px", position: "relative" }}>
            <Search size={16} color="var(--text-secondary)" style={{ position: "absolute", left: 12, top: 11 }} />
            <input
              type="text"
              placeholder="Search by title, organization or skill..."
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

          {/* Type Select */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
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
            {OPPORTUNITY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>

          {/* Remote Toggle */}
          <button
            onClick={() => setRemoteOnly(remoteOnly === true ? undefined : true)}
            className="btn btn-secondary"
            style={{
              padding: "9px 14px",
              borderRadius: 8,
              fontSize: 13,
              background: remoteOnly === true ? "rgba(83,101,245,0.1)" : "var(--bg-card)",
              borderColor: remoteOnly === true ? "var(--accent-primary)" : "var(--border-color)",
              color: remoteOnly === true ? "var(--accent-primary)" : "var(--text-secondary)",
            }}
          >
            🌐 Remote Only
          </button>
        </div>

        {/* Opportunities List */}
        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 14,
                  padding: 24,
                  height: 140,
                  opacity: 0.5,
                }}
              />
            ))}
          </div>
        ) : error ? (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              background: "rgba(239,68,68,0.08)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: 14,
            }}
          >
            <p style={{ color: "#EF4444", fontWeight: 600, margin: "0 0 12px" }}>{error}</p>
            <button
              onClick={() => void loadOpportunities()}
              style={{
                padding: "8px 18px",
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
        ) : opportunities.length === 0 ? (
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
            <Briefcase size={40} style={{ margin: "0 auto 12px", opacity: 0.6 }} />
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 6px", color: "var(--text-primary)" }}>
              No opportunities match your filter
            </h3>
            <p style={{ fontSize: 13, margin: 0 }}>Try resetting your filters or search keywords.</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {opportunities.map((opp) => (
              <div
                key={opp.id}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 14,
                  padding: 20,
                  display: "flex",
                  flexWrap: "wrap",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: 16,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                }}
              >
                <div style={{ flex: "1 1 500px" }}>
                  <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8, marginBottom: 8 }}>
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
                      {opp.opportunity_type}
                    </span>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                      {opp.organization}
                    </span>
                    {opp.is_remote && (
                      <span style={{ fontSize: 11, color: "#10B981", background: "rgba(16,185,129,0.1)", padding: "2px 6px", borderRadius: 4, fontWeight: 600 }}>
                        Remote Eligible
                      </span>
                    )}
                  </div>

                  <h3 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
                    {opp.title}
                  </h3>

                  <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px", lineHeight: 1.5 }}>
                    {opp.description}
                  </p>

                  {/* Metadata chips */}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 14, fontSize: 12, color: "var(--text-secondary)", marginBottom: 12 }}>
                    {opp.location && (
                      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <MapPin size={14} color="var(--accent-primary)" />
                        {opp.location}
                      </div>
                    )}
                    {opp.stipend_or_prize && (
                      <div style={{ display: "flex", alignItems: "center", gap: 4, fontWeight: 600, color: "var(--text-primary)" }}>
                        <Award size={14} color="#F59E0B" />
                        {opp.stipend_or_prize}
                      </div>
                    )}
                    {opp.days_left !== null && opp.days_left !== undefined && (
                      <div style={{ display: "flex", alignItems: "center", gap: 4, color: opp.days_left <= 7 ? "#EF4444" : "var(--text-secondary)", fontWeight: opp.days_left <= 7 ? 700 : 500 }}>
                        <Clock size={14} />
                        {opp.days_left > 0 ? `${opp.days_left} days left to apply` : "Deadline today"}
                      </div>
                    )}
                  </div>

                  {/* Tags */}
                  {opp.tags && opp.tags.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {opp.tags.map((tag, idx) => (
                        <span
                          key={idx}
                          style={{
                            fontSize: 11,
                            padding: "2px 8px",
                            borderRadius: 4,
                            background: "var(--bg-secondary)",
                            color: "var(--text-secondary)",
                          }}
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Card Action Controls */}
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <button
                    onClick={() => handleToggleBookmark(opp.id)}
                    disabled={bookmarkingId === opp.id}
                    title={opp.is_bookmarked ? "Remove bookmark" : "Save opportunity"}
                    style={{
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border-color)",
                      color: opp.is_bookmarked ? "var(--accent-primary)" : "var(--text-secondary)",
                      borderRadius: 8,
                      padding: 10,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    {opp.is_bookmarked ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
                  </button>

                  <a
                    href={sanitizeExternalUrl(opp.apply_url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn"
                    style={{
                      background: "var(--accent-primary)",
                      color: "#fff",
                      borderRadius: 8,
                      padding: "9px 18px",
                      fontSize: 13,
                      fontWeight: 600,
                      textDecoration: "none",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    Apply Now <ExternalLink size={14} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
