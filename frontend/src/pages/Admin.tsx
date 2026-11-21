import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Database,
  DownloadCloud,
  FileSpreadsheet,
  Globe,
  Layers,
  LoaderCircle,
  MapPin,
  RefreshCw,
  Server,
  Shield,
  ShieldAlert,
  Users,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import {
  api,
  AdminStats,
  DatasetMetadataItem,
  User,
  UserReportItem,
} from "../lib/api";

export default function Admin() {
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [datasets, setDatasets] = useState<DatasetMetadataItem[]>([]);
  const [reports, setReports] = useState<UserReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingEvents, setSyncingEvents] = useState(false);
  const [syncingPlaces, setSyncingPlaces] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");
  const [syncError, setSyncError] = useState("");
  const [eventTopic, setEventTopic] = useState("tech");
  const [placeCity, setPlaceCity] = useState("Pune");

  const navigate = useNavigate();

  useEffect(() => {
    void loadAdminData();
  }, []);

  async function loadAdminData() {
    setLoading(true);
    setSyncError("");
    try {
      const me = await api.me();
      setUser(me);
      if (!me.is_admin) {
        setLoading(false);
        return;
      }

      const [s, d, r] = await Promise.all([
        api.adminStats().catch(() => null),
        api.adminDatasets().catch(() => []),
        api.adminReports("pending").catch(() => []),
      ]);

      if (s) setStats(s);
      setDatasets(d);
      setReports(r);
    } catch {
      setSyncError("Please sign in with an administrator account to access this dashboard.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSyncEvents() {
    setSyncingEvents(true);
    setSyncMessage("");
    setSyncError("");
    try {
      const res = await api.adminSyncEvents(eventTopic);
      setSyncMessage(`Eventbrite Sync: ${res.message}`);
      // Refresh stats
      const s = await api.adminStats();
      setStats(s);
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Failed to sync events.");
    } finally {
      setSyncingEvents(false);
    }
  }

  async function handleSyncPlaces() {
    setSyncingPlaces(true);
    setSyncMessage("");
    setSyncError("");
    try {
      const res = await api.adminSyncPlaces(placeCity);
      setSyncMessage(`OpenStreetMap Sync: ${res.message}`);
      // Refresh stats
      const s = await api.adminStats();
      setStats(s);
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Failed to sync places.");
    } finally {
      setSyncingPlaces(false);
    }
  }

  async function handleResolveReport(reportId: number, action: "resolved" | "dismissed") {
    try {
      await api.adminResolveReport(reportId, action);
      setReports((prev) => prev.filter((r) => r.id !== reportId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Action failed.");
    }
  }

  async function handleModerationAction(
    reportId: number,
    action: "remove_content" | "warn_user" | "suspend_user" | "dismiss_report"
  ) {
    try {
      const res = await api.adminModerationAction(reportId, action);
      alert(res.message);
      setReports((prev) => prev.filter((r) => r.id !== reportId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Moderation action failed.");
    }
  }

  return (
    <AppShell>
      <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "16px 8px 60px" }}>
        {/* Header */}
        <div style={{ marginBottom: "28px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
              <Shield size={26} style={{ color: "var(--primary-accent)" }} />
              <h1 style={{ fontSize: "24px", fontWeight: "800", color: "var(--primary-text)", margin: 0 }}>
                ALIGN Control & Data Management Console
              </h1>
            </div>
            <p style={{ color: "var(--secondary-text)", fontSize: "14px", margin: 0 }}>
              Inspect real database metrics, manage external API data pipelines, and oversee user reports.
            </p>
          </div>
          <button
            onClick={() => navigate("/admin/data-health")}
            style={{
              padding: "9px 18px",
              borderRadius: "10px",
              background: "rgba(216,245,106,0.15)",
              border: "1px solid var(--lime)",
              color: "var(--lime)",
              fontSize: "13px",
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <Activity size={16} /> View Data Health Dashboard →
          </button>
        </div>

        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "100px 0" }}>
            <LoaderCircle className="spin" size={36} style={{ color: "var(--primary-accent)" }} />
          </div>
        ) : !user?.is_admin ? (
          <div className="card" style={{ padding: "40px 24px", textAlign: "center", borderRadius: "18px" }}>
            <ShieldAlert size={48} style={{ color: "#EF4444", margin: "0 auto 16px" }} />
            <h2 style={{ color: "var(--primary-text)", margin: "0 0 8px 0" }}>Administrator Access Required</h2>
            <p style={{ color: "var(--secondary-text)", maxWidth: "500px", margin: "0 auto 20px" }}>
              The current account does not have administrator privileges (`is_admin: false`). Sign in with an authorized
              administrative account to view database health and trigger dataset synchronizations.
            </p>
            <button className="button primary" onClick={() => navigate("/login")}>
              Sign In with Admin Account
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            {/* Feedback Banners */}
            {syncMessage && (
              <div
                style={{
                  padding: "14px 18px",
                  borderRadius: "12px",
                  background: "rgba(16, 185, 129, 0.12)",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                  color: "#10B981",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  fontWeight: 600,
                  fontSize: "14px",
                }}
              >
                <CheckCircle size={18} />
                <span>{syncMessage}</span>
              </div>
            )}
            {syncError && (
              <div
                style={{
                  padding: "14px 18px",
                  borderRadius: "12px",
                  background: "rgba(239, 68, 68, 0.12)",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                  color: "#EF4444",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  fontWeight: 600,
                  fontSize: "14px",
                }}
              >
                <AlertTriangle size={18} />
                <span>{syncError}</span>
              </div>
            )}

            {/* Metrics Grid */}
            <section>
              <h2 style={{ fontSize: "16px", fontWeight: "700", color: "var(--primary-text)", margin: "0 0 14px 0" }}>
                Platform & Database Status
              </h2>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: "14px",
                }}
              >
                <div className="card" style={{ padding: "18px", borderRadius: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--secondary-text)", marginBottom: "8px" }}>
                    <Users size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase" }}>Registered Users</span>
                  </div>
                  <div style={{ fontSize: "28px", fontWeight: "800", color: "var(--primary-text)" }}>
                    {stats?.total_users ?? 0}
                  </div>
                </div>

                <div className="card" style={{ padding: "18px", borderRadius: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--secondary-text)", marginBottom: "8px" }}>
                    <Layers size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase" }}>Communities</span>
                  </div>
                  <div style={{ fontSize: "28px", fontWeight: "800", color: "var(--primary-text)" }}>
                    {stats?.total_communities ?? 0}
                  </div>
                </div>

                <div className="card" style={{ padding: "18px", borderRadius: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--secondary-text)", marginBottom: "8px" }}>
                    <Activity size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase" }}>Events</span>
                  </div>
                  <div style={{ fontSize: "28px", fontWeight: "800", color: "var(--primary-text)" }}>
                    {stats?.total_events ?? 0}
                  </div>
                </div>

                <div className="card" style={{ padding: "18px", borderRadius: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--secondary-text)", marginBottom: "8px" }}>
                    <MapPin size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase" }}>Places & Venues</span>
                  </div>
                  <div style={{ fontSize: "28px", fontWeight: "800", color: "var(--primary-text)" }}>
                    {stats?.total_places ?? 0}
                  </div>
                </div>

                <div className="card" style={{ padding: "18px", borderRadius: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--secondary-text)", marginBottom: "8px" }}>
                    <FileSpreadsheet size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase" }}>Taxonomy Records</span>
                  </div>
                  <div style={{ fontSize: "28px", fontWeight: "800", color: "var(--primary-accent)" }}>
                    {(stats?.total_dataset_records ?? 0).toLocaleString()}
                  </div>
                </div>

                <div className="card" style={{ padding: "18px", borderRadius: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--secondary-text)", marginBottom: "8px" }}>
                    <Database size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase" }}>pgvector</span>
                  </div>
                  <div style={{ fontSize: "15px", fontWeight: "700", color: "#10B981", marginTop: "6px" }}>
                    {stats?.pgvector_status ?? "Active"}
                  </div>
                </div>
              </div>
            </section>

            {/* Ingestion & Sync Controls */}
            <section className="card" style={{ padding: "24px", borderRadius: "18px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
                <RefreshCw size={20} style={{ color: "var(--primary-accent)" }} />
                <h2 style={{ fontSize: "18px", fontWeight: "700", color: "var(--primary-text)", margin: 0 }}>
                  External Data Synchronization
                </h2>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
                {/* Eventbrite Ingestion */}
                <div style={{ border: "1px solid var(--border-subtle)", borderRadius: "14px", padding: "18px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                    <Globe size={18} style={{ color: "var(--primary-accent)" }} />
                    <h3 style={{ fontSize: "15px", fontWeight: "700", color: "var(--primary-text)", margin: 0 }}>
                      Eventbrite Real-Time Events
                    </h3>
                  </div>
                  <p style={{ fontSize: "13px", color: "var(--secondary-text)", margin: "0 0 14px 0" }}>
                    Fetch live tech meetups and hackathons via the Eventbrite Destination API and generate 384-d embeddings.
                  </p>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <input
                      type="text"
                      value={eventTopic}
                      onChange={(e) => setEventTopic(e.target.value)}
                      placeholder="Topic (e.g. AI, tech, design)"
                      className="search"
                      style={{ flex: 1, height: "38px" }}
                    />
                    <button
                      className="button primary"
                      onClick={handleSyncEvents}
                      disabled={syncingEvents}
                      style={{ height: "38px" }}
                    >
                      {syncingEvents ? "Syncing..." : "Sync Events"}
                    </button>
                  </div>
                </div>

                {/* OpenStreetMap Places Ingestion */}
                <div style={{ border: "1px solid var(--border-subtle)", borderRadius: "14px", padding: "18px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                    <MapPin size={18} style={{ color: "var(--primary-accent)" }} />
                    <h3 style={{ fontSize: "15px", fontWeight: "700", color: "var(--primary-text)", margin: 0 }}>
                      OpenStreetMap Venues & Spaces
                    </h3>
                  </div>
                  <p style={{ fontSize: "13px", color: "var(--secondary-text)", margin: "0 0 14px 0" }}>
                    Ingest authentic third places, makerspaces, libraries, and coworking hubs for target Indian tech hubs.
                  </p>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <select
                      value={placeCity}
                      onChange={(e) => setPlaceCity(e.target.value)}
                      className="search"
                      style={{ flex: 1, height: "38px" }}
                    >
                      <option value="Pune">Pune</option>
                      <option value="Mumbai">Mumbai</option>
                      <option value="Kolhapur">Kolhapur</option>
                      <option value="Bangalore">Bangalore</option>
                    </select>
                    <button
                      className="button primary"
                      onClick={handleSyncPlaces}
                      disabled={syncingPlaces}
                      style={{ height: "38px" }}
                    >
                      {syncingPlaces ? "Syncing..." : "Sync Venues"}
                    </button>
                  </div>
                </div>
              </div>
            </section>

            {/* Benchmark Datasets Inventory */}
            <section className="card" style={{ padding: "24px", borderRadius: "18px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
                <FileSpreadsheet size={20} style={{ color: "var(--primary-accent)" }} />
                <h2 style={{ fontSize: "18px", fontWeight: "700", color: "var(--primary-text)", margin: 0 }}>
                  Empirical Benchmark Datasets
                </h2>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {datasets.map((d) => (
                  <div
                    key={d.id}
                    style={{
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "14px",
                      padding: "16px 20px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "16px",
                      flexWrap: "wrap",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                        <span style={{ fontWeight: 700, fontSize: "15px", color: "var(--primary-text)" }}>
                          {d.dataset_name}
                        </span>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "6px",
                            background: "rgba(83, 101, 245, 0.12)",
                            color: "var(--primary-accent)",
                          }}
                        >
                          {d.version}
                        </span>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "6px",
                            background: "rgba(16, 185, 129, 0.12)",
                            color: "#10B981",
                          }}
                        >
                          {d.status.toUpperCase()}
                        </span>
                      </div>
                      <p style={{ fontSize: "13px", color: "var(--secondary-text)", margin: "0 0 6px 0" }}>
                        {d.notes}
                      </p>
                      <div style={{ fontSize: "12px", color: "var(--secondary-text)" }}>
                        Source File: <code>{d.source_filename}</code> • Record Types: {d.record_types}
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "22px", fontWeight: 800, color: "var(--primary-accent)" }}>
                        {d.total_records.toLocaleString()}
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--secondary-text)", textTransform: "uppercase" }}>
                        Imported Records
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Moderation & User Reports */}
            <section className="card" style={{ padding: "24px", borderRadius: "18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px", marginBottom: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <ShieldAlert size={20} style={{ color: "#EF4444" }} />
                  <div>
                    <h2 style={{ fontSize: "18px", fontWeight: "700", color: "var(--primary-text)", margin: 0 }}>
                      Moderation & Content Review Queue ({reports.length})
                    </h2>
                    <p style={{ fontSize: "12px", color: "var(--secondary-text)", margin: "2px 0 0" }}>
                      Takedown & Safety Desk: <code>takedown@align.internal</code> (demo placeholder)
                    </p>
                  </div>
                </div>
              </div>

              {reports.length === 0 ? (
                <div style={{ textAlign: "center", padding: "30px 10px", color: "var(--secondary-text)" }}>
                  <CheckCircle size={36} style={{ color: "#10B981", margin: "0 auto 10px" }} />
                  <p style={{ margin: 0, fontWeight: 600 }}>All user and content reports resolved. Platform is clean and healthy.</p>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  {reports.map((r) => (
                    <div
                      key={r.id}
                      style={{
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "14px",
                        padding: "16px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "12px",
                        background: "var(--bg-card-glass)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "8px" }}>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                            <span
                              style={{
                                fontSize: "11px",
                                fontWeight: 700,
                                padding: "2px 8px",
                                borderRadius: "4px",
                                background: r.target_type === "post" ? "rgba(99, 102, 241, 0.15)" : r.target_type === "reel" ? "rgba(236, 72, 153, 0.15)" : "rgba(245, 158, 11, 0.15)",
                                color: r.target_type === "post" ? "var(--primary-accent)" : r.target_type === "reel" ? "#ec4899" : "#f59e0b",
                              }}
                            >
                              {(r.target_type || "user").toUpperCase()}
                            </span>
                            <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--primary-text)" }}>
                              Report #{r.id}: {r.reason}
                            </span>
                          </div>

                          <div style={{ fontSize: "12px", color: "var(--secondary-text)" }}>
                            Target User: <strong>{r.reported_user_name || "Unknown"}</strong> {r.reported_user_id ? `(ID: ${r.reported_user_id})` : ""}
                            {r.post_id && ` • Post ID: ${r.post_id}`}
                            {r.reel_id && ` • Reel ID: ${r.reel_id}`}
                          </div>
                        </div>

                        <span style={{ fontSize: "11px", color: "var(--secondary-text)" }}>
                          Reported by: <strong>{r.reporter_name}</strong> • {new Date(r.created_at).toLocaleString()}
                        </span>
                      </div>

                      {r.content_snippet && (
                        <div
                          style={{
                            padding: "8px 12px",
                            borderRadius: "8px",
                            background: "rgba(0,0,0,0.25)",
                            fontSize: "12px",
                            color: "var(--primary-text)",
                            fontStyle: "italic",
                            borderLeft: "3px solid var(--primary-accent)",
                          }}
                        >
                          "{r.content_snippet}"
                        </div>
                      )}

                      {r.details && (
                        <div style={{ fontSize: "12px", color: "var(--secondary-text)" }}>
                          <strong>Reporter Note:</strong> "{r.details}"
                        </div>
                      )}

                      {/* Admin Moderation Actions */}
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", borderTop: "1px solid var(--border-subtle)", paddingTop: "10px", marginTop: "4px" }}>
                        {(r.post_id || r.reel_id) && (
                          <button
                            type="button"
                            className="button"
                            onClick={() => handleModerationAction(r.id, "remove_content")}
                            style={{
                              fontSize: "12px",
                              padding: "6px 12px",
                              borderColor: "#EF4444",
                              color: "#EF4444",
                            }}
                          >
                            Remove Content
                          </button>
                        )}
                        <button
                          type="button"
                          className="button"
                          onClick={() => handleModerationAction(r.id, "warn_user")}
                          style={{
                            fontSize: "12px",
                            padding: "6px 12px",
                            borderColor: "#F59E0B",
                            color: "#F59E0B",
                          }}
                        >
                          Warn User
                        </button>
                        <button
                          type="button"
                          className="button"
                          onClick={() => handleModerationAction(r.id, "suspend_user")}
                          style={{
                            fontSize: "12px",
                            padding: "6px 12px",
                            background: "rgba(239, 68, 68, 0.2)",
                            borderColor: "#EF4444",
                            color: "#EF4444",
                          }}
                        >
                          Suspend User
                        </button>
                        <button
                          type="button"
                          className="button"
                          onClick={() => handleModerationAction(r.id, "dismiss_report")}
                          style={{ fontSize: "12px", padding: "6px 12px" }}
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </AppShell>
  );
}
