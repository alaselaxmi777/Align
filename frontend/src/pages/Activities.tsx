import { FormEvent, useEffect, useState } from "react";
import { Bookmark, Calendar, CalendarDays, Check, Clock, ExternalLink, Globe, LoaderCircle, MapPin, Plus, RefreshCw, Sparkles, Target, Users, X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import SearchBar from "../components/common/SearchBar";
import CategoryChips from "../components/common/CategoryChips";
import { api, EventItem, RegistrationResult } from "../lib/api";
import EventRegistrationModal from "../components/EventRegistrationModal";
import { useToast } from "../components/common/ToastContext";
import { formatApiError } from "../lib/errorUtils";

const ACTIVITY_CATEGORIES = [
  "All",
  "Workshop",
  "Hackathon",
  "Outdoors",
  "Meetup",
  "Tech & Community",
];

export default function Activities() {
  const [activities, setActivities] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [showModal, setShowModal] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [selectedActivityForReg, setSelectedActivityForReg] = useState<EventItem | null>(null);

  // Host Activity Form
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [cat, setCat] = useState("Workshop");
  const [loc, setLoc] = useState("Online");
  const [capacity, setCapacity] = useState<number | undefined>(undefined);
  const [startsAt, setStartsAt] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const navigate = useNavigate();
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    void fetchActivities();
  }, [selectedCategory]);

  async function fetchActivities(searchTerm = query) {
    setLoading(true);
    setError("");
    try {
      const categoryParam = selectedCategory === "All" ? "" : selectedCategory;
      const data = await api.events(searchTerm, true, categoryParam);
      setActivities(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load community activities.");
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    void fetchActivities(query);
  }

  const toast = useToast();

  async function handleToggleSave(item: EventItem) {
    if (!loggedIn) {
      navigate("/login?next=/activities");
      return;
    }
    setSavingId(item.id);
    try {
      await api.saveItem("event", item.id);
      toast.success(`Activity "${item.title}" saved to your collection.`);
    } catch (err) {
      toast.error(formatApiError(err, "Failed to save activity."));
    } finally {
      setSavingId(null);
    }
  }

  async function handleCreateActivity(e: FormEvent) {
    e.preventDefault();
    if (!loggedIn) {
      navigate("/login?next=/activities");
      return;
    }
    setSubmitting(true);
    try {
      const created = await api.createEvent({
        title,
        description: desc,
        category: cat,
        location: loc,
        capacity: capacity ? Number(capacity) : undefined,
        starts_at: startsAt ? new Date(startsAt).toISOString() : undefined,
      });
      setActivities([created, ...activities]);
      toast.success("Activity hosted successfully!");
      setShowModal(false);
      setTitle("");
      setDesc("");
      setStartsAt("");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to host activity."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell title="Activities">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px", marginBottom: "20px" }}>
        <div>
          <p className="eyebrow">Real-World Experiences &amp; Collaborative Sprints</p>
          <h1 className="page-title">Activities</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "14px", margin: "4px 0 0 0" }}>
            Join workshops, outdoor adventures, coding jams, and collaborative community activities.
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            if (!loggedIn) {
              navigate("/login?next=/activities");
              return;
            }
            setShowModal(true);
          }}
          className="button primary"
          style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
        >
          <Plus size={16} /> Host an Activity
        </button>
      </div>

      {/* Search and Category Filters */}
      <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginBottom: "24px" }}>
        <SearchBar
          value={query}
          onChange={(val) => {
            setQuery(val);
            void fetchActivities(val);
          }}
          onClear={() => void fetchActivities("")}
          placeholder="Search activities by keyword, craft, or topic..."
        />
        <CategoryChips
          categories={ACTIVITY_CATEGORIES}
          activeCategory={selectedCategory}
          onSelect={(c) => setSelectedCategory(c)}
        />
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <LoaderCircle className="spin" size={32} style={{ color: "var(--lime)" }} />
        </div>
      ) : error ? (
        <div className="empty-state" style={{ padding: "40px 20px" }}>
          <p style={{ color: "var(--danger)", marginBottom: "12px" }}>{error}</p>
          <button type="button" onClick={() => void fetchActivities()} className="button">
            <RefreshCw size={14} style={{ marginRight: "6px" }} /> Try Again
          </button>
        </div>
      ) : activities.length === 0 ? (
        <div className="empty-state" style={{ padding: "60px 20px" }}>
          <Target size={44} style={{ color: "var(--text-muted)", margin: "0 auto 12px" }} />
          <h3 style={{ margin: "0 0 6px 0" }}>No Activities Found</h3>
          <p style={{ color: "var(--text-muted)", margin: "0 0 16px 0", maxWidth: "420px", marginLeft: "auto", marginRight: "auto" }}>
            No verified activities currently match this filter. Be the first to host an activity or explore upcoming community events.
          </p>
          <button
            type="button"
            onClick={() => {
              setSelectedCategory("All");
              setQuery("");
              void fetchActivities("");
            }}
            className="button"
          >
            Clear Filter
          </button>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: "20px",
          }}
        >
          {activities.map((act) => (
            <article
              key={act.id}
              className="panel"
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                padding: "22px",
                borderRadius: "16px",
                transition: "transform 0.15s ease",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px", marginBottom: "10px" }}>
                  <span className="tag" style={{ textTransform: "uppercase", letterSpacing: "0.05em", fontSize: "11px" }}>
                    {act.category || "Activity"}
                  </span>
                  {act.is_external && (
                    <span className="tag" style={{ background: "rgba(139, 92, 246, 0.15)", color: "var(--accent)" }}>
                      Live Provider
                    </span>
                  )}
                </div>

                <h3 style={{ margin: "0 0 8px 0", fontSize: "17px", fontWeight: 700, color: "var(--text)" }}>
                  {act.title}
                </h3>

                <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.5", margin: "0 0 16px 0" }}>
                  {act.description || "Interactive community session."}
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px", color: "var(--text-muted)", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <MapPin size={13} style={{ color: "var(--lime)" }} />
                    <span>{act.location || "Online"}</span>
                  </div>
                  {act.starts_at && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <CalendarDays size={13} style={{ color: "var(--lilac)" }} />
                      <span>{new Date(act.starts_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}</span>
                    </div>
                  )}
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <Users size={13} style={{ color: "var(--pink)" }} />
                    <span>{act.registered_count || 0} participants {act.capacity ? `/ ${act.capacity} max` : ""}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px", paddingTop: "14px", borderTop: "1px solid var(--border)" }}>
                <button
                  type="button"
                  onClick={() => setSelectedActivityForReg(act)}
                  className={`button ${act.is_registered ? "" : "primary"}`}
                  style={{ flex: 1, fontSize: "12px", fontWeight: 700 }}
                >
                  {act.is_registered ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--success)" }}>
                      <Check size={14} /> Registered
                    </span>
                  ) : (
                    "Register Now"
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => handleToggleSave(act)}
                  disabled={savingId === act.id}
                  className="button"
                  title="Bookmark activity"
                  style={{ padding: "8px 12px" }}
                >
                  <Bookmark size={15} />
                </button>

                {act.event_url && (
                  <a
                    href={act.event_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="button"
                    title="External Link"
                    style={{ padding: "8px 12px" }}
                  >
                    <ExternalLink size={14} />
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Host Activity Modal */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ maxWidth: "480px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>Host a Community Activity</h2>
              <button type="button" onClick={() => setShowModal(false)} className="icon-button" style={{ background: "none", border: "none" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateActivity} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label className="text-xs font-bold block mb-1">Title</label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Pune Weekend Photography Walk"
                  required
                  className="w-full"
                />
              </div>

              <div>
                <label className="text-xs font-bold block mb-1">Category</label>
                <select
                  value={cat}
                  onChange={(e) => setCat(e.target.value)}
                  className="search w-full"
                >
                  <option value="Workshop">Workshop</option>
                  <option value="Hackathon">Hackathon</option>
                  <option value="Outdoors">Outdoors</option>
                  <option value="Meetup">Meetup</option>
                  <option value="Tech & Community">Tech &amp; Community</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold block mb-1">Location</label>
                <input
                  value={loc}
                  onChange={(e) => setLoc(e.target.value)}
                  placeholder="e.g. FC Road, Pune or Online"
                  required
                  className="w-full"
                />
              </div>

              <div>
                <label className="text-xs font-bold block mb-1">Date &amp; Time</label>
                <input
                  type="datetime-local"
                  value={startsAt}
                  onChange={(e) => setStartsAt(e.target.value)}
                  className="w-full"
                />
              </div>

              <div>
                <label className="text-xs font-bold block mb-1">Max Capacity (Optional)</label>
                <input
                  type="number"
                  min="1"
                  max="500"
                  value={capacity ?? ""}
                  onChange={(e) => setCapacity(e.target.value ? Number(e.target.value) : undefined)}
                  placeholder="e.g. 25"
                  className="w-full"
                />
              </div>

              <div>
                <label className="text-xs font-bold block mb-1">Description</label>
                <textarea
                  value={desc}
                  onChange={(e) => setDesc(e.target.value)}
                  placeholder="Outline what participants will do, learn, and what to bring..."
                  rows={3}
                  className="w-full"
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button type="button" onClick={() => setShowModal(false)} className="button">
                  Cancel
                </button>
                <button type="submit" disabled={submitting} className="button primary">
                  {submitting ? "Publishing..." : "Publish Activity"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Registration Modal */}
      {selectedActivityForReg && (
        <EventRegistrationModal
          isOpen={Boolean(selectedActivityForReg)}
          event={selectedActivityForReg}
          onClose={() => setSelectedActivityForReg(null)}
          onSuccess={(_eventId: number, res: RegistrationResult) => {
            setActivities((prev) =>
              prev.map((a) =>
                a.id === selectedActivityForReg.id
                  ? {
                      ...a,
                      is_registered: res.status === "registered",
                      registered_count:
                        res.status === "registered"
                          ? (a.registered_count || 0) + 1
                          : Math.max(0, (a.registered_count || 1) - 1),
                    }
                  : a
              )
            );
          }}
        />
      )}
    </AppShell>
  );
}
