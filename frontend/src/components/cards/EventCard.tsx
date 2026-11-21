import { useState } from "react";
import { EventItem, api } from "../../lib/api";
import WhyThisPopover from "../common/WhyThisPopover";
import { SafeImage } from "../common/SafeImage";

interface EventCardProps {
  event: EventItem;
  onOpenDetail?: (event: EventItem) => void;
  onRsvpToggle?: (id: number, isRegistered: boolean) => void;
}

const DEFAULT_EVENT_IMAGE = "https://images.pexels.com/photos/2747449/pexels-photo-2747449.jpeg?auto=compress&cs=tinysrgb&w=800";

export default function EventCard({ event, onOpenDetail, onRsvpToggle }: EventCardProps) {
  const [registered, setRegistered] = useState(Boolean(event.is_registered));
  const [loading, setLoading] = useState(false);
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  async function handleToggleRsvp() {
    if (!loggedIn) {
      window.location.href = "/login";
      return;
    }
    setLoading(true);
    try {
      if (registered) {
        await api.cancelEventRegistration(event.id);
        setRegistered(false);
        onRsvpToggle?.(event.id, false);
      } else {
        await api.registerEvent(event.id);
        setRegistered(true);
        onRsvpToggle?.(event.id, true);
      }
    } catch (err) {
      console.error("Failed to toggle RSVP:", err);
    } finally {
      setLoading(false);
    }
  }

  // Format date
  const dateStr = event.starts_at
    ? new Date(event.starts_at).toLocaleDateString("en-US", {
        day: "numeric",
        month: "short",
      })
    : "Upcoming";

  const isOnline = event.location?.toLowerCase().includes("online");

  return (
    <article className="canva-card" data-content-key={String(event.id)}>
      <SafeImage
        src={DEFAULT_EVENT_IMAGE}
        alt={event.title}
        className="card-image"
      />
      <div className="card-body">
        <div style={{ display: "flex", gap: "6px", alignItems: "center", justifyContent: "space-between", marginBottom: "6px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
            <span className="tag">
              {isOnline ? "Online" : "In person"} · {dateStr}
            </span>
            {event.is_external || event.source?.toLowerCase() === "eventbrite" ? (
              <span className="tag" style={{ background: "rgba(240, 85, 55, 0.15)", color: "#f05537", border: "1px solid rgba(240, 85, 55, 0.3)" }}>
                Eventbrite
              </span>
            ) : (
              <span className="tag" style={{ background: "rgba(99, 102, 241, 0.15)", color: "#6366f1", border: "1px solid rgba(99, 102, 241, 0.3)" }}>
                ALIGN
              </span>
            )}
            {event.is_expired && (
              <span className="tag" style={{ background: "rgba(156, 163, 175, 0.2)", color: "#9ca3af" }}>
                Ended
              </span>
            )}
          </div>
          {event.score !== undefined && event.score !== null && (
            <WhyThisPopover
              score={event.score}
              whyRecommended={event.why_recommended}
              scoreBreakdown={event.score_breakdown || undefined}
              matchedTerms={event.matched_terms || undefined}
              graphPath={event.graph_path}
              title={event.title}
            />
          )}
        </div>
        <h3>{event.title}</h3>
        <p>
          {event.location} · {event.registered_count ?? 0} registered
        </p>
        <div className="card-foot">
          <button
            type="button"
            className="button"
            onClick={() => onOpenDetail?.(event)}
          >
            View details
          </button>
          <button
            type="button"
            className={`button toggle-action ${registered ? "selected" : ""}`}
            onClick={handleToggleRsvp}
            disabled={loading}
          >
            {loading ? "..." : registered ? "Going" : "RSVP"}
          </button>
        </div>
      </div>
    </article>
  );
}
