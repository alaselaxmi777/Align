import { FormEvent, useEffect, useState } from "react";
import { Bookmark, Calendar, CalendarDays, Check, Clock, ExternalLink, Globe, LoaderCircle, MapPin, Plus, RefreshCw, Sparkles, Users, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import SearchBar from "../components/common/SearchBar";
import CategoryChips from "../components/common/CategoryChips";
import { api, EventItem, RegistrationResult } from "../lib/api";
import EventRegistrationModal from "../components/EventRegistrationModal";
import { useToast } from "../components/common/ToastContext";
import { formatApiError } from "../lib/errorUtils";

const CATEGORIES = ["All", "Workshop", "Meetup", "Tech & Community", "Hackathon", "Outdoors"];

export default function Events() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [showModal, setShowModal] = useState(false);
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [selectedEventForReg, setSelectedEventForReg] = useState<EventItem | null>(null);

  // Eventbrite Live Sync State
  const [syncQuery, setSyncQuery] = useState("tech");
  const [syncLocation, setSyncLocation] = useState("India");
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");

  // New Event Form (Host Event)
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
    void fetchEvents();
  }, [selectedCategory]);

  async function fetchEvents(searchTerm = query) {
    setLoading(true);
    setError("");
    try {
      const categoryParam = selectedCategory === "All" ? "" : selectedCategory;
      const data = await api.events(searchTerm, true, categoryParam);
      setEvents(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load events.");
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    void fetchEvents(query);
  }

  async function handleSyncEventbrite(e: FormEvent) {
    e.preventDefault();
    setSyncing(true);
    setSyncMessage("");
    try {
      const res = await api.syncEventbrite(syncQuery, syncLocation);
      setSyncMessage(res.message || `Successfully synced ${res.synced} events!`);
      void fetchEvents();
      setTimeout(() => {
        setShowSyncModal(false);
        setSyncMessage("");
      }, 2000);
    } catch (err) {
      setSyncMessage(err instanceof Error ? err.message : "Sync failed.");
    } finally {
      setSyncing(false);
    }
  }

  function handleRegisterClick(e: EventItem) {
    // Open registration modal directly from our website
    setSelectedEventForReg(e);
  }

  function handleRegistrationSuccess(eventId: number, regResult: RegistrationResult) {
    setEvents((prev) =>
      prev.map((item) =>
        item.id === eventId
          ? {
              ...item,
              is_registered: true,
              registered_count: (item.registered_count || 0) + (regResult.ticket_count || 1),
            }
          : item
      )
    );
  }

  const toast = useToast();

  async function saveItem(id: number) {
    if (!loggedIn) {
      navigate("/login?next=/events");
      return;
    }
    setSavingId(id);
    try {
      await api.saveItem("event", id);
      toast.success("Event saved to your collection!");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to save item."));
    } finally {
      setSavingId(null);
    }
  }

  async function submitCreate(e: FormEvent) {
    e.preventDefault();
    if (!loggedIn) {
      navigate("/login?next=/events");
      return;
    }
    setSubmitting(true);
    try {
      const created = await api.createEvent({
        title,
        description: desc,
        category: cat,
        location: loc,
        starts_at: startsAt ? new Date(startsAt).toISOString() : undefined,
        capacity: capacity ? Number(capacity) : undefined,
      });
      setEvents([created, ...events]);
      toast.success("Event created successfully!");
      setShowModal(false);
      setTitle("");
      setDesc("");
      setStartsAt("");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to create event."));
    } finally {
      setSubmitting(false);
    }
  }

  function extractEventbriteUrl(description: string): string | null {
    const match = description.match(/https?:\/\/[^\s]+/);
    return match ? match[0] : null;
  }

  return (
    <AppShell title="Events">
      <p className="eyebrow">Make plans worth keeping</p>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 className="page-title">There’s always something happening.</h1>
          <p className="lead" style={{ margin: 0 }}>
            Real-time community meetups, hackathons, and gatherings powered by Eventbrite &amp; ALIGN.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            className="button"
            type="button"
            onClick={() => setShowSyncModal(true)}
            style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
          >
            <RefreshCw size={14} /> Sync Eventbrite
          </button>
          <button
            className="button primary"
            type="button"
            onClick={() => (loggedIn ? setShowModal(true) : navigate("/login?next=/events"))}
          >
            <Plus size={15} /> Host event
          </button>
        </div>
      </div>

      {/* Toolbar with Search and Date picker */}
      <div className="toolbar" style={{ marginTop: "24px" }}>
        <SearchBar
          value={query}
          onChange={(val) => {
            setQuery(val);
            void fetchEvents(val);
          }}
          placeholder="Search events by title, topic, or location..."
        />
        <input
          type="date"
          className="search"
          style={{ flex: "0 1 190px", minWidth: "160px" }}
          onChange={(e) => {
            if (e.target.value) {
              setEvents((prev) => prev.filter((ev) => !ev.starts_at || ev.starts_at >= e.target.value));
            } else {
              void fetchEvents(query);
            }
          }}
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
            onClick={() => void fetchEvents()}
            style={{ fontSize: 13, padding: "7px 18px", borderRadius: 8, cursor: "pointer" }}
          >
            Retry Loading Events
          </button>
        </div>
      )}

      <div className="section-heading">
        <h2>Upcoming &amp; recommended events</h2>
        <small className="meta">
          Showing {events.length} {events.length === 1 ? "event" : "events"}
        </small>
      </div>

        {loading ? (
          <div className="results-grid">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div
                key={n}
                className="result-card"
                style={{ height: 260, opacity: 0.5, background: "var(--bg-card)" }}
              />
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <CalendarDays size={28} />
            </div>
            <h2>No upcoming events found</h2>
            <p>Click "Sync Eventbrite Live" to pull real-time events, or host the first event!</p>
            <button
              className="cta-button"
              style={{ marginTop: "14px", background: "var(--button-pink)", color: "#FFFFFF" }}
              onClick={() => setShowSyncModal(true)}
            >
              <RefreshCw size={14} /> Sync Real-Time Events
            </button>
          </div>
        ) : (
          <div className="results-grid">
            {events.map((e) => {
              const externalLink = extractEventbriteUrl(e.description);
              const isEventbrite = externalLink !== null || e.category.toLowerCase().includes("eventbrite");

              return (
                <article className="result-card" key={e.id}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div className="result-icon pink">
                      <CalendarDays size={19} />
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      {isEventbrite && (
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: "700",
                            padding: "3px 9px",
                            borderRadius: "100px",
                            background: "var(--powder-pink)",
                            color: "var(--primary-text)",
                            border: "1px solid var(--border-subtle)",
                          }}
                        >
                          Eventbrite Live
                        </span>
                      )}
                      <button
                        onClick={() => saveItem(e.id)}
                        disabled={savingId === e.id}
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

                  <div className="result-type">{e.category.toUpperCase()}</div>
                  <h3>{e.title}</h3>
                  <p>{e.description.replace(/Event Link \/ Tickets: https?:\/\/[^\s]+/g, "").trim()}</p>

                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", margin: "14px 0", color: "var(--secondary-text)", fontSize: "12px" }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                      <MapPin size={13} style={{ color: "var(--accent-pink)" }} /> {e.location}
                    </span>
                    {e.starts_at && (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        <Clock size={13} style={{ color: "var(--accent-pink)" }} />{" "}
                        {new Date(e.starts_at).toLocaleDateString(undefined, {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    )}
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                      <Users size={13} style={{ color: "var(--accent-pink)" }} /> {e.registered_count || 0}
                      {e.capacity ? ` / ${e.capacity} attending` : " attending"}
                    </span>
                  </div>

                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      onClick={() => handleRegisterClick(e)}
                      style={{
                        flex: 1,
                        padding: "11px",
                        borderRadius: "12px",
                        border: e.is_registered ? "1px solid var(--border-subtle)" : "none",
                        background: e.is_registered ? "var(--bg-secondary)" : "var(--button-pink)",
                        color: e.is_registered ? "var(--secondary-text)" : "#FFFFFF",
                        fontWeight: "700",
                        fontSize: "12px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                        cursor: "pointer",
                        boxShadow: e.is_registered ? "none" : "0 4px 12px rgba(232, 160, 176, 0.35)",
                        transition: "all .2s ease",
                      }}
                    >
                      {e.is_registered ? (
                        <>
                          <Check size={14} style={{ color: "var(--accent-pink)" }} /> Attending (Pass)
                        </>
                      ) : (
                        "Register RSVP"
                      )}
                    </button>

                    {externalLink && (
                      <a
                        href={externalLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          padding: "10px 14px",
                          borderRadius: "12px",
                          background: "var(--bg-card)",
                          border: "1px solid var(--border-subtle)",
                          color: "var(--primary-accent)",
                          fontWeight: "600",
                          fontSize: "12px",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          textDecoration: "none",
                          boxShadow: "var(--card-shadow)",
                          transition: "all .2s ease",
                        }}
                        title="View Official Eventbrite Page"
                      >
                        Tickets <ExternalLink size={14} />
                      </a>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {/* Modal: Live Eventbrite Sync */}
        {showSyncModal && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(61, 41, 51, 0.45)",
              backdropFilter: "blur(8px)",
              WebkitBackdropFilter: "blur(8px)",
              display: "grid",
              placeItems: "center",
              zIndex: 100,
              padding: "20px",
            }}
          >
            <div className="auth-card" style={{ maxWidth: "480px", width: "100%", position: "relative" }}>
              <button
                onClick={() => setShowSyncModal(false)}
                style={{
                  position: "absolute",
                  top: "20px",
                  right: "20px",
                  background: "transparent",
                  border: "none",
                  color: "var(--secondary-text)",
                  cursor: "pointer",
                }}
              >
                <X size={20} />
              </button>

              <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--accent-pink)", fontSize: "12px", fontWeight: "700", marginBottom: "6px" }}>
                <Globe size={14} /> REAL-TIME EVENTBRITE INGESTION
              </div>
              <h2>Sync Live Events</h2>
              <p className="auth-subtitle">
                Pull verified real-time events and workshops from Eventbrite directly into the ALIGN database.
              </p>

              <form onSubmit={handleSyncEventbrite} className="auth-form">
                <label>
                  Topic or Keywords
                  <input
                    value={syncQuery}
                    onChange={(e) => setSyncQuery(e.target.value)}
                    placeholder="e.g. tech, startup, ai, design, networking"
                    required
                  />
                </label>

                <label>
                  City or Location Filter (Optional)
                  <input
                    value={syncLocation}
                    onChange={(e) => setSyncLocation(e.target.value)}
                    placeholder="e.g. Pune, Mumbai, Bangalore, or leave blank"
                  />
                </label>

                {syncMessage && (
                  <div
                    style={{
                      padding: "12px 14px",
                      borderRadius: "10px",
                      background: "var(--bg-main)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--primary-text)",
                      fontSize: "12px",
                      textAlign: "center",
                    }}
                  >
                    {syncMessage}
                  </div>
                )}

                <button
                  className="submit-button"
                  disabled={syncing}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                  }}
                >
                  {syncing ? (
                    <>
                      <LoaderCircle className="spin" size={16} /> Querying Eventbrite API...
                    </>
                  ) : (
                    <>
                      <RefreshCw size={16} /> Pull Live Events
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Host Event */}
        {showModal && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(61, 41, 51, 0.45)",
              backdropFilter: "blur(8px)",
              WebkitBackdropFilter: "blur(8px)",
              display: "grid",
              placeItems: "center",
              zIndex: 100,
              padding: "20px",
            }}
          >
            <div className="auth-card" style={{ maxWidth: "520px", width: "100%", position: "relative" }}>
              <button
                onClick={() => setShowModal(false)}
                style={{
                  position: "absolute",
                  top: "20px",
                  right: "20px",
                  background: "transparent",
                  border: "none",
                  color: "var(--secondary-text)",
                  cursor: "pointer",
                }}
              >
                <X size={20} />
              </button>

              <h2>Host an Event</h2>
              <p className="auth-subtitle">Bring people together for a workshop, hike, or meetup.</p>

              <form onSubmit={submitCreate} className="auth-form">
                <label>
                  Event Title
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    placeholder="e.g. Build Your First Vector Search App"
                  />
                </label>
                <label>
                  Category
                  <select
                    value={cat}
                    onChange={(e) => setCat(e.target.value)}
                  >
                    <option value="Workshop">Workshop</option>
                    <option value="Meetup">Meetup</option>
                    <option value="Tech & Community">Tech & Community</option>
                    <option value="Hackathon">Hackathon</option>
                    <option value="Outdoors">Outdoors</option>
                  </select>
                </label>
                <label>
                  Description
                  <textarea
                    value={desc}
                    onChange={(e) => setDesc(e.target.value)}
                    required
                    rows={3}
                    placeholder="What will attendees experience or learn?"
                  />
                </label>
                <label>
                  Date & Time
                  <input
                    type="datetime-local"
                    value={startsAt}
                    onChange={(e) => setStartsAt(e.target.value)}
                  />
                </label>
                <label>
                  Location / Platform
                  <input
                    value={loc}
                    onChange={(e) => setLoc(e.target.value)}
                    placeholder="e.g. Online or Pune, India"
                  />
                </label>
                <label>
                  Capacity Limit (Optional)
                  <input
                    type="number"
                    value={capacity || ""}
                    onChange={(e) => setCapacity(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="Max attendees (e.g. 30)"
                  />
                </label>

                <button className="submit-button" disabled={submitting}>
                  {submitting ? "Publishing..." : "Publish Event"}
                </button>
              </form>
            </div>
          </div>
        )}
        {/* Event Registration Modal */}
        <EventRegistrationModal
          isOpen={selectedEventForReg !== null}
          onClose={() => setSelectedEventForReg(null)}
          event={selectedEventForReg}
          onSuccess={handleRegistrationSuccess}
        />
    </AppShell>
  );
}
