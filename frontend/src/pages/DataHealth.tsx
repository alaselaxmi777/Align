import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Database,
  ExternalLink,
  Layers,
  RefreshCw,
  Server,
  Shield,
  Trash2,
  Users,
  Calendar,
  Sparkles,
  Award,
  MapPin,
  Clock,
  ArrowRight,
} from "lucide-react";
import AppShell from "../components/layout/AppShell";
import { api, DataHealthResponse, User } from "../lib/api";

export default function DataHealth() {
  const [dataHealth, setDataHealth] = useState<DataHealthResponse | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    void loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [currentUser, health] = await Promise.all([
        api.me().catch(() => null),
        api.adminDataHealth(),
      ]);
      setUser(currentUser);
      setDataHealth(health);
    } catch (err: any) {
      setError(err?.message || "Failed to load data health metrics. Please verify admin privileges.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeactivateExpired() {
    setActionLoading(true);
    setActionMessage("");
    try {
      const res = await api.deactivateExpiredOpportunities();
      setActionMessage(`Deactivated ${res.deactivated_count} expired opportunities.`);
      await loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to run expiry deactivation job.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSeedVerified() {
    setActionLoading(true);
    setActionMessage("");
    try {
      const res = await api.seedVerifiedOpportunities();
      setActionMessage(`Imported ${res.inserted_count} real verified opportunities.`);
      await loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to seed verified opportunities.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSyncKaggle() {
    setActionLoading(true);
    setActionMessage("");
    try {
      const res = await api.syncKaggleOpportunities();
      setActionMessage(res.message);
      await loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to sync Kaggle opportunities.");
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <AppShell>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 20px" }}>
        {/* Header Breadcrumbs & Status Bar */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }}>
              <Link to="/admin" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>Admin</Link>
              <span>/</span>
              <span style={{ color: "var(--accent-primary)", fontWeight: 600 }}>Data Health & Observability</span>
            </div>
            <h1 style={{ fontSize: 28, fontWeight: 800, margin: 0, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 10 }}>
              <Activity size={26} color="var(--lime)" /> Platform Data Health
            </h1>
            <p style={{ margin: "4px 0 0", fontSize: 14, color: "var(--text-secondary)" }}>
              Real-time audit of live external sources, database row counts, test row exclusions, and data hygiene.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button
              onClick={() => void loadData()}
              disabled={loading}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                color: "var(--text-primary)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
            </button>
            <Link
              to="/admin"
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                background: "rgba(166,124,245,0.15)",
                border: "1px solid var(--lilac)",
                color: "var(--lilac)",
                fontSize: 13,
                fontWeight: 600,
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              Admin Dashboard
            </Link>
          </div>
        </div>

        {/* Action / Success Banner */}
        {actionMessage && (
          <div
            style={{
              padding: "12px 16px",
              borderRadius: 10,
              background: "rgba(216,245,106,0.1)",
              border: "1px solid var(--lime)",
              color: "var(--lime)",
              fontSize: 13,
              marginBottom: 20,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <CheckCircle size={16} /> {actionMessage}
          </div>
        )}

        {/* Loading Skeleton */}
        {loading && !dataHealth && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ height: 160, background: "var(--bg-card)", borderRadius: 14, opacity: 0.6 }} />
            <div style={{ height: 240, background: "var(--bg-card)", borderRadius: 14, opacity: 0.6 }} />
            <div style={{ height: 200, background: "var(--bg-card)", borderRadius: 14, opacity: 0.6 }} />
          </div>
        )}

        {/* Error State with Retry Button */}
        {error && (
          <div
            style={{
              padding: "24px 20px",
              borderRadius: 12,
              background: "rgba(239,68,68,0.1)",
              border: "1px solid #EF4444",
              color: "#EF4444",
              marginBottom: 24,
              textAlign: "center",
            }}
          >
            <AlertTriangle size={32} style={{ margin: "0 auto 8px" }} />
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 6px" }}>Observability Error</h3>
            <p style={{ fontSize: 13, margin: "0 0 16px" }}>{error}</p>
            <button
              onClick={() => void loadData()}
              style={{
                padding: "8px 20px",
                borderRadius: 8,
                background: "#EF4444",
                color: "#ffffff",
                border: "none",
                fontWeight: 700,
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              Retry Loading Health Data
            </button>
          </div>
        )}

        {/* Data Health Dashboard Content */}
        {dataHealth && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* 1. External Ingestion Source Cards */}
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
                <Server size={18} color="var(--lilac)" /> External Data Sources & Ingestion Health
              </h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16 }}>
                {dataHealth.sources.map((src, i) => (
                  <div
                    key={i}
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border-color)",
                      borderRadius: 12,
                      padding: 16,
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                        <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{src.name}</span>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: 6,
                            background: src.status.includes("operational") || src.status.includes("active") || src.status.includes("configured") || src.status.includes("integrated")
                              ? "rgba(16,185,129,0.15)"
                              : "rgba(245,158,11,0.15)",
                            color: src.status.includes("operational") || src.status.includes("active") || src.status.includes("configured") || src.status.includes("integrated")
                              ? "#10B981"
                              : "#F59E0B",
                            textTransform: "uppercase",
                          }}
                        >
                          {src.status.split(" ")[0]}
                        </span>
                      </div>
                      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 10px", lineHeight: 1.4 }}>
                        {src.policy}
                      </p>
                    </div>

                    <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: 10, fontSize: 11, color: "var(--text-secondary)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span>Last Ingest: {src.last_successful_fetch ? new Date(src.last_successful_fetch).toLocaleTimeString() : "Pending"}</span>
                      {src.cache_entries !== undefined && (
                        <span style={{ color: "var(--lime)", fontWeight: 600 }}>{src.cache_entries} queries cached</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 2. Platform Entity Row Counts (Real vs Test) */}
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
                <Database size={18} color="var(--lime)" /> Live Entity Counts (Real vs Test Rows)
              </h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
                {/* Users */}
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: 12, padding: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>Users</span>
                    <Users size={16} color="var(--lilac)" />
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
                    {dataHealth.row_counts.users.total}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 8 }}>
                    <span style={{ color: "#10B981", fontWeight: 600 }}>{dataHealth.row_counts.users.real} real</span>
                    <span>•</span>
                    <span style={{ color: "#F59E0B" }}>{dataHealth.row_counts.users.test} test</span>
                  </div>
                </div>

                {/* Communities */}
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: 12, padding: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>Communities</span>
                    <Layers size={16} color="var(--lime)" />
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
                    {dataHealth.row_counts.communities.total}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 8 }}>
                    <span style={{ color: "#10B981", fontWeight: 600 }}>{dataHealth.row_counts.communities.real} real</span>
                    <span>•</span>
                    <span style={{ color: "#F59E0B" }}>{dataHealth.row_counts.communities.test} test</span>
                  </div>
                </div>

                {/* Projects */}
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: 12, padding: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>Projects</span>
                    <Sparkles size={16} color="var(--accent-primary)" />
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
                    {dataHealth.row_counts.projects.total}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 8 }}>
                    <span style={{ color: "#10B981", fontWeight: 600 }}>{dataHealth.row_counts.projects.real} real</span>
                    <span>•</span>
                    <span style={{ color: "#F59E0B" }}>{dataHealth.row_counts.projects.test} test</span>
                  </div>
                </div>

                {/* Opportunities */}
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: 12, padding: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>Opportunities</span>
                    <Award size={16} color="#EC4899" />
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
                    {dataHealth.row_counts.opportunities.total}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 8 }}>
                    <span style={{ color: "#10B981", fontWeight: 600 }}>{dataHealth.row_counts.opportunities.active} active</span>
                    <span>•</span>
                    <span style={{ color: "#EF4444" }}>{dataHealth.row_counts.opportunities.expired} expired</span>
                  </div>
                </div>

                {/* Events */}
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: 12, padding: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>Events</span>
                    <Calendar size={16} color="#3B82F6" />
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
                    {dataHealth.row_counts.events.total}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 8 }}>
                    <span style={{ color: "#10B981", fontWeight: 600 }}>{dataHealth.row_counts.events.upcoming} upcoming</span>
                    <span>•</span>
                    <span style={{ color: "var(--text-secondary)" }}>{dataHealth.row_counts.events.past} past</span>
                  </div>
                </div>

                {/* Places */}
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: 12, padding: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>Places & Venues</span>
                    <MapPin size={16} color="#10B981" />
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
                    {dataHealth.row_counts.places.total}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                    Verified OpenStreetMap nodes
                  </div>
                </div>
              </div>
            </div>

            {/* 3. Hygiene & Maintenance Watchdog */}
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: 14, padding: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 12 }}>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
                    <Shield size={18} color="var(--lime)" /> Data Hygiene & Inactive Exclusions
                  </h3>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 0" }}>
                    Nightly background jobs ensure expired entries are deindexed from discovery searches.
                  </p>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    onClick={() => void handleDeactivateExpired()}
                    disabled={actionLoading}
                    style={{
                      padding: "7px 14px",
                      borderRadius: 8,
                      background: "rgba(239,68,68,0.12)",
                      border: "1px solid #EF4444",
                      color: "#EF4444",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Deactivate Expired Now
                  </button>
                  <button
                    onClick={() => void handleSeedVerified()}
                    disabled={actionLoading}
                    style={{
                      padding: "7px 14px",
                      borderRadius: 8,
                      background: "rgba(216,245,106,0.15)",
                      border: "1px solid var(--lime)",
                      color: "var(--lime)",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Import Verified Seed CSV
                  </button>
                  <button
                    onClick={() => void handleSyncKaggle()}
                    disabled={actionLoading}
                    style={{
                      padding: "7px 14px",
                      borderRadius: 8,
                      background: "rgba(166,124,245,0.15)",
                      border: "1px solid var(--lilac)",
                      color: "var(--lilac)",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Sync Kaggle Competitions
                  </button>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginTop: 12 }}>
                <div style={{ padding: 12, background: "var(--bg-secondary)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Expired Opportunities</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#EF4444" }}>{dataHealth.inactive_and_expired.expired_opportunities}</div>
                </div>
                <div style={{ padding: 12, background: "var(--bg-secondary)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Inactive Opportunities</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-secondary)" }}>{dataHealth.inactive_and_expired.inactive_opportunities}</div>
                </div>
                <div style={{ padding: 12, background: "var(--bg-secondary)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Cancelled Events</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#F59E0B" }}>{dataHealth.inactive_and_expired.cancelled_events}</div>
                </div>
                <div style={{ padding: 12, background: "var(--bg-secondary)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Total Test Entities Flagged</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "var(--lime)" }}>{dataHealth.inactive_and_expired.test_entities_total}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
