import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { PlaceItem, api } from "../../lib/api";
import WhyThisPopover from "../common/WhyThisPopover";
import { SafeImage } from "../common/SafeImage";

interface PlaceCardProps {
  place: PlaceItem;
  isSaved?: boolean;
  onSaveToggle?: (id: number, saved: boolean) => void;
  onOpenDetail?: (place: PlaceItem) => void;
}

const CATEGORY_FALLBACK_IMAGES: Record<string, string> = {
  "Innovation & Labs": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800&auto=format&fit=crop&q=80",
  "Libraries & Learning": "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=800&auto=format&fit=crop&q=80",
  "Makerspaces & Hardware": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800&auto=format&fit=crop&q=80",
  "Research & Tech": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=800&auto=format&fit=crop&q=80",
  "Co-Working & Startups": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&auto=format&fit=crop&q=80",
  "Parks & Outdoors": "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&auto=format&fit=crop&q=80",
  "Cafes & Culture": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=800&auto=format&fit=crop&q=80",
  "Co-Working & Social": "https://images.unsplash.com/photo-1527192491265-7e15c55b1ed2?w=800&auto=format&fit=crop&q=80",
};

const DEFAULT_PLACE_IMAGE = "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&auto=format&fit=crop&q=80";

function getPlaceImage(place: PlaceItem): string {
  if (place.image_url) return place.image_url;
  if (place.category && CATEGORY_FALLBACK_IMAGES[place.category]) {
    return CATEGORY_FALLBACK_IMAGES[place.category];
  }
  return DEFAULT_PLACE_IMAGE;
}

export default function PlaceCard({
  place,
  isSaved = false,
  onSaveToggle,
  onOpenDetail,
}: PlaceCardProps) {
  const [saved, setSaved] = useState(isSaved);
  const [loading, setLoading] = useState(false);
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  async function handleToggleSave() {
    if (!loggedIn) {
      window.location.href = "/login";
      return;
    }
    setLoading(true);
    try {
      if (saved) {
        await api.unsaveItem("place", place.id);
        setSaved(false);
        onSaveToggle?.(place.id, false);
      } else {
        await api.saveItem("place", place.id);
        setSaved(true);
        onSaveToggle?.(place.id, true);
      }
    } catch (err) {
      console.error("Failed to toggle save:", err);
    } finally {
      setLoading(false);
    }
  }

  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    `${place.name}, ${place.address || ""} ${place.city}`
  )}`;

  return (
    <article className="canva-card" data-content-key={String(place.id)}>
      <SafeImage
        src={getPlaceImage(place)}
        fallbackSrc={DEFAULT_PLACE_IMAGE}
        alt={place.name}
        className="card-image"
        loading="lazy"
      />
      <div className="card-body">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
          <span className="tag">
            {place.category || "Community Space"}
          </span>
          {place.score !== undefined && place.score !== null && (
            <WhyThisPopover
              score={place.score}
              whyRecommended={place.why_recommended}
              scoreBreakdown={place.score_breakdown || undefined}
              matchedTerms={place.matched_terms || undefined}
              graphPath={place.graph_path}
              title={place.name}
            />
          )}
        </div>
        <h3>{place.name}</h3>
        <p>
          {place.address ? `${place.address}, ` : ""}
          {place.city}
          {place.distance_km != null ? ` · ${place.distance_km.toFixed(1)} km away` : ""}
        </p>
        <div className="card-foot">
          <a
            href={mapUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="button"
            title="Open in Google Maps"
            style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}
          >
            <span>Directions</span>
            <ExternalLink size={13} />
          </a>
          <button
            type="button"
            className={`button toggle-action ${saved ? "selected" : ""}`}
            onClick={handleToggleSave}
            disabled={loading}
          >
            {loading ? "..." : saved ? "Saved" : "Save"}
          </button>
        </div>
      </div>
    </article>
  );
}
