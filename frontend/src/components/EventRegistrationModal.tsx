import { FormEvent, useEffect, useState } from "react";
import { Calendar, CheckCircle2, Clock, ExternalLink, Globe, LoaderCircle, MapPin, Sparkles, Ticket, X } from "lucide-react";
import { api, RegistrationResult } from "../lib/api";

export interface EventRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  event: {
    id: number;
    title: string;
    description?: string;
    category?: string;
    location?: string;
    starts_at?: string | null;
    is_eventbrite?: boolean;
    event_url?: string | null;
  } | null;
  onSuccess?: (eventId: number, result: RegistrationResult) => void;
}

export default function EventRegistrationModal({
  isOpen,
  onClose,
  event,
  onSuccess,
}: EventRegistrationModalProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [ticketCount, setTicketCount] = useState(1);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState("");
  const [confirmedData, setConfirmedData] = useState<RegistrationResult | null>(null);

  useEffect(() => {
    if (isOpen) {
      setConfirmedData(null);
      setError("");
      const storedName = localStorage.getItem("align_user_name") || "";
      const storedEmail = localStorage.getItem("align_user_email") || "";
      setName(storedName);
      setEmail(storedEmail);
      setTicketCount(1);
      setNotes("");
    }
  }, [isOpen, event]);

  if (!isOpen || !event) return null;

  const isEventbrite =
    event.is_eventbrite ||
    (event.category || "").toLowerCase().includes("eventbrite") ||
    (event.description || "").toLowerCase().includes("eventbrite");

  function getEventbriteLink(): string | null {
    if (event?.event_url) return event.event_url;
    const match = (event?.description || "").match(/https?:\/\/[^\s]+/);
    return match ? match[0] : null;
  }

  const ebUrl = getEventbriteLink();

  function makeGoogleCalendarUrl(): string {
    if (!event) return "#";
    const title = encodeURIComponent(event.title);
    const details = encodeURIComponent(
      `${event.description?.slice(0, 300) || "ALIGN Community Gathering"}\n\nRegistered via ALIGN`
    );
    const location = encodeURIComponent(event.location || "Online");
    let dates = "";
    if (event.starts_at) {
      try {
        const start = new Date(event.starts_at).toISOString().replace(/-|:|\.\d\d\d/g, "");
        const end = new Date(new Date(event.starts_at).getTime() + 2 * 60 * 60 * 1000)
          .toISOString()
          .replace(/-|:|\.\d\d\d/g, "");
        dates = `&dates=${start}/${end}`;
      } catch {
        dates = "";
      }
    }
    return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${title}&details=${details}&location=${location}${dates}`;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!event) return;
    setSubmitting(true);
    setError("");

    try {
      const res = await api.registerEvent(event.id, {
        name,
        email,
        phone,
        ticket_count: ticketCount,
        notes,
      });

      setConfirmedData(res);
      if (onSuccess) {
        onSuccess(event.id, res);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel() {
    if (!event) return;
    if (!confirm("Are you sure you want to cancel your event registration?")) return;
    setCancelling(true);
    try {
      await api.cancelEvent(event.id, email);
      alert("Your registration has been cancelled.");
      onClose();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to cancel.");
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(61, 41, 51, 0.45)",
        backdropFilter: "blur(10px)",
        display: "grid",
        placeItems: "center",
        zIndex: 250,
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="auth-card"
        style={{
          maxWidth: "520px",
          width: "100%",
          position: "relative",
          maxHeight: "90vh",
          overflowY: "auto",
          background: "#FFFFFF",
          border: "1px solid var(--border-subtle)",
          borderRadius: "18px",
          padding: "28px",
          boxShadow: "0 20px 50px rgba(244, 182, 194, 0.35)",
        }}
      >
        <button
          onClick={onClose}
          aria-label="Close"
          style={{
            position: "absolute",
            top: "18px",
            right: "18px",
            background: "transparent",
            border: "none",
            color: "var(--secondary-text)",
            cursor: "pointer",
            padding: "4px",
          }}
        >
          <X size={20} />
        </button>

        {confirmedData ? (
          /* Confirmation Ticket Pass View */
          <div style={{ textAlign: "center", padding: "10px 0" }}>
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "50%",
                background: "var(--powder-pink)",
                border: "2px solid var(--primary-pink)",
                display: "grid",
                placeItems: "center",
                margin: "0 auto 16px auto",
                color: "var(--primary-text)",
              }}
            >
              <CheckCircle2 size={32} style={{ color: "var(--accent-pink)" }} />
            </div>

            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                textTransform: "uppercase",
                letterSpacing: "1px",
                color: "var(--accent-pink)",
              }}
            >
              Registration Confirmed
            </span>

            <h2 style={{ fontSize: "22px", margin: "8px 0 16px 0", color: "var(--primary-text)" }}>
              You're Going! 🎉
            </h2>

            {/* Digital Pass Card */}
            <div
              style={{
                background: "var(--bg-main)",
                border: "1.5px dashed var(--primary-pink)",
                borderRadius: "14px",
                padding: "18px",
                textAlign: "left",
                marginBottom: "20px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <span style={{ fontSize: "11px", color: "var(--secondary-text)", fontWeight: "600" }}>PASS REFERENCE</span>
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: "700",
                    background: "var(--powder-pink)",
                    color: "var(--primary-text)",
                    padding: "3px 8px",
                    borderRadius: "6px",
                    fontFamily: "monospace",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  {confirmedData.ticket_code || `ALIGN-EVT-${event.id}`}
                </span>
              </div>

              <h4 style={{ margin: "0 0 10px 0", fontSize: "16px", color: "var(--primary-text)" }}>{event.title}</h4>

              <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px", color: "var(--secondary-text)" }}>
                {event.starts_at && (
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--primary-text)" }}>
                    <Clock size={13} style={{ color: "var(--accent-pink)" }} />
                    {new Date(event.starts_at).toLocaleDateString(undefined, {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                )}
                <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--primary-text)" }}>
                  <MapPin size={13} style={{ color: "var(--accent-pink)" }} />
                  {event.location || "Online"}
                </span>
                <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--primary-text)" }}>
                  <Ticket size={13} style={{ color: "var(--accent-pink)" }} />
                  Attendee: <strong>{confirmedData.attendee_name || name}</strong> ({confirmedData.attendee_email || email})
                </span>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <a
                href={makeGoogleCalendarUrl()}
                target="_blank"
                rel="noopener noreferrer"
                className="cta-button"
                style={{
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  background: "var(--button-pink)",
                  borderColor: "var(--border-subtle)",
                  color: "#FFFFFF",
                  fontWeight: "600",
                }}
              >
                <Calendar size={15} /> Add to Google Calendar
              </a>

              {ebUrl && (
                <a
                  href={ebUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    padding: "10px",
                    borderRadius: "10px",
                    background: "var(--powder-pink)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--primary-text)",
                    fontSize: "12px",
                    fontWeight: "600",
                    textDecoration: "none",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "6px",
                  }}
                >
                  View Official Eventbrite Page <ExternalLink size={13} />
                </a>
              )}

              <div style={{ display: "flex", gap: "10px", marginTop: "6px" }}>
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={cancelling}
                  style={{
                    flex: 1,
                    padding: "10px",
                    borderRadius: "10px",
                    background: "#FFFFFF",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--error)",
                    fontSize: "12px",
                    cursor: "pointer",
                    fontWeight: "600",
                  }}
                >
                  {cancelling ? "Cancelling..." : "Cancel RSVP"}
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="submit-button"
                  style={{ flex: 1, margin: 0 }}
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Registration Form View */
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "8px" }}>
              {isEventbrite ? (
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: "700",
                    padding: "3px 9px",
                    borderRadius: "100px",
                    background: "rgba(239, 163, 181, 0.15)",
                    color: "var(--primary-text)",
                    border: "1px solid var(--border-subtle)",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <Globe size={11} /> Eventbrite Live Event
                </span>
              ) : (
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: "700",
                    padding: "3px 9px",
                    borderRadius: "100px",
                    background: "var(--powder-pink)",
                    color: "var(--primary-text)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  ALIGN Community
                </span>
              )}
              {event.category && (
                <span style={{ fontSize: "11px", color: "var(--secondary-text)" }}>
                  {event.category}
                </span>
              )}
            </div>

            <h2 style={{ fontSize: "20px", margin: "4px 0 10px 0", color: "var(--primary-text)" }}>
              Register for Event
            </h2>
            <h4 style={{ margin: "0 0 12px 0", fontSize: "14px", color: "var(--secondary-text)", fontWeight: "500" }}>
              {event.title}
            </h4>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "5px",
                padding: "10px 14px",
                background: "var(--bg-subtle)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "12px",
                fontSize: "12px",
                color: "var(--primary-text)",
                marginBottom: "18px",
              }}
            >
              {event.starts_at && (
                <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                  <Clock size={13} style={{ color: "var(--accent-pink)" }} />
                  {new Date(event.starts_at).toLocaleDateString(undefined, {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              )}
              <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                <MapPin size={13} style={{ color: "var(--accent-pink)" }} />
                {event.location || "Online"}
              </span>
            </div>

            {error && (
              <div
                style={{
                  padding: "10px",
                  borderRadius: "8px",
                  background: "rgba(229, 115, 115, 0.12)",
                  color: "var(--error)",
                  border: "1px solid var(--error)",
                  fontSize: "12px",
                  marginBottom: "14px",
                }}
              >
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="auth-form">
              <label>
                Your Full Name
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex Morgan"
                  required
                />
              </label>

              <label>
                Email Address
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                />
              </label>

              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "10px" }}>
                <label>
                  Phone / WhatsApp (Optional)
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+91 98765 43210"
                  />
                </label>
                <label>
                  Passes
                  <select
                    value={ticketCount}
                    onChange={(e) => setTicketCount(Number(e.target.value))}
                    style={{
                      padding: "12px",
                      borderRadius: "12px",
                      background: "#FFFFFF",
                      color: "var(--primary-text)",
                      border: "1.5px solid var(--border-subtle)",
                    }}
                  >
                    <option value={1}>1 Attendee</option>
                    <option value={2}>2 Attendees</option>
                    <option value={3}>3 Attendees</option>
                    <option value={4}>4 Attendees</option>
                  </select>
                </label>
              </div>

              <label>
                Questions or Notes for Host (Optional)
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Interested in learning more about the topic"
                />
              </label>

              <button
                type="submit"
                disabled={submitting}
                className="submit-button"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  marginTop: "8px",
                }}
              >
                {submitting ? (
                  <>
                    <LoaderCircle className="spin" size={16} /> Registering...
                  </>
                ) : (
                  <>
                    <Ticket size={16} /> Complete RSVP Registration
                  </>
                )}
              </button>

              {ebUrl && (
                <div style={{ textAlign: "center", marginTop: "12px" }}>
                  <span style={{ fontSize: "11px", color: "var(--secondary-text)", display: "block", marginBottom: "6px" }}>
                    Or view official Eventbrite ticketing:
                  </span>
                  <a
                    href={ebUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: "12px",
                      color: "var(--accent-pink)",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      textDecoration: "none",
                      fontWeight: "600",
                    }}
                  >
                    Official Eventbrite Page <ExternalLink size={12} />
                  </a>
                </div>
              )}
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
