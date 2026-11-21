import { useEffect, useState, useMemo, FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  MapPin,
  Calendar,
  Compass,
  Navigation,
  ExternalLink,
  Layers,
  Search,
  Filter,
  Info,
  Building,
  Coffee,
  Cpu,
  RefreshCw,
} from "lucide-react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import AppShell from "../components/layout/AppShell";
import { api, MapMarkerItem } from "../lib/api";

// Custom Leaflet Icons for Dark Theme
const placeIcon = L.divIcon({
  className: "custom-map-pin",
  html: `<div style="background:#D8F56A; color:#1C1126; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; box-shadow:0 3px 10px rgba(0,0,0,0.5); border:2px solid #ffffff; font-weight:bold; font-size:13px; cursor:pointer;">📍</div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
  popupAnchor: [0, -28],
});

const eventIcon = L.divIcon({
  className: "custom-map-pin",
  html: `<div style="background:#A779E8; color:#ffffff; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; box-shadow:0 3px 10px rgba(0,0,0,0.5); border:2px solid #ffffff; font-weight:bold; font-size:13px; cursor:pointer;">⚡</div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
  popupAnchor: [0, -28],
});

function MapRecenter({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom, { animate: true });
  }, [center, zoom, map]);
  return null;
}

export default function DiscoveryMap() {
  const [markers, setMarkers] = useState<MapMarkerItem[]>([]);
  const [selectedMarker, setSelectedMarker] = useState<MapMarkerItem | null>(null);
  const [filterType, setFilterType] = useState<"all" | "place" | "event">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [locationName, setLocationName] = useState("Local Region");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [centerCoords, setCenterCoords] = useState<[number, number]>([18.5204, 73.8567]); // Default to Pune/Regional tech center
  const [mapZoom, setMapZoom] = useState(12);

  useEffect(() => {
    // Attempt HTML5 geolocation first
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          setCenterCoords([lat, lon]);
          setLocationName("Your Current Location");
          loadMarkers(lat, lon, 35);
        },
        () => {
          // Fallback to Pune Regional Tech Center
          setCenterCoords([18.5204, 73.8567]);
          setLocationName("Pune Region");
          loadMarkers(18.5204, 73.8567, 35);
        },
        { timeout: 8000 }
      );
    } else {
      setCenterCoords([18.5204, 73.8567]);
      setLocationName("Pune Region");
      loadMarkers(18.5204, 73.8567, 35);
    }
  }, []);

  async function loadMarkers(lat?: number, lon?: number, radiusKm = 35, queryText?: string) {
    setLoading(true);
    setError("");
    try {
      const data = await api.mapMarkers(lat, lon, radiusKm, queryText);
      setMarkers(data);
      if (data.length > 0) {
        setSelectedMarker(data[0]);
        // Recenter map on first result if search was by text
        if (queryText && data[0].latitude && data[0].longitude) {
          setCenterCoords([data[0].latitude, data[0].longitude]);
          setMapZoom(13);
        }
      } else {
        setSelectedMarker(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load discovery markers from OpenStreetMap");
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setLocationName(searchQuery.trim());
    await loadMarkers(undefined, undefined, 35, searchQuery.trim());
  }

  const filteredMarkers = useMemo(() => {
    return markers.filter((m) => {
      const matchType = filterType === "all" || m.type === filterType;
      return matchType;
    });
  }, [markers, filterType]);

  return (
    <AppShell title="Discovery Map">
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "20px 16px 80px" }}>
        {/* Header Hero */}
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 16,
            padding: "20px 24px",
            marginBottom: 20,
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 16,
          }}
        >
          <div>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                fontWeight: 800,
                color: "var(--lime)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                marginBottom: 4,
              }}
            >
              <Navigation size={13} /> Geospatial Discovery Engine · OpenStreetMap
            </div>
            <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text)", margin: "0 0 4px" }}>
              Interactive Discovery Map
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0 }}>
              Real coworking spaces, colleges, universities, and tech venues within {locationName}.
            </p>
          </div>

          {/* Search Bar & Geocoding */}
          <form onSubmit={handleSearch} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <div style={{ position: "relative" }}>
              <input
                type="text"
                placeholder="Search city or area (e.g. Kolhapur, Pune)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  padding: "8px 12px 8px 34px",
                  fontSize: 13,
                  color: "var(--text)",
                  width: 260,
                }}
              />
              <Search
                size={15}
                style={{ position: "absolute", left: 10, top: 11, color: "var(--text-muted)" }}
              />
            </div>
            <button
              type="submit"
              className="button primary"
              style={{ padding: "8px 16px", fontSize: 13, fontWeight: 700 }}
              disabled={loading}
            >
              {loading ? "Searching..." : "Explore Area"}
            </button>
          </form>
        </div>

        {/* Filter Controls Row */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div
            style={{
              display: "flex",
              gap: 6,
              background: "var(--bg-secondary)",
              padding: 4,
              borderRadius: 10,
              border: "1px solid var(--border)",
            }}
          >
            <button
              onClick={() => setFilterType("all")}
              style={{
                padding: "6px 14px",
                borderRadius: 8,
                border: "none",
                background: filterType === "all" ? "var(--bg-card)" : "transparent",
                color: filterType === "all" ? "var(--lime)" : "var(--text-muted)",
                fontWeight: 700,
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              All ({markers.length})
            </button>
            <button
              onClick={() => setFilterType("place")}
              style={{
                padding: "6px 14px",
                borderRadius: 8,
                border: "none",
                background: filterType === "place" ? "var(--bg-card)" : "transparent",
                color: filterType === "place" ? "var(--lime)" : "var(--text-muted)",
                fontWeight: 700,
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              Venues ({markers.filter((m) => m.type === "place").length})
            </button>
            <button
              onClick={() => setFilterType("event")}
              style={{
                padding: "6px 14px",
                borderRadius: 8,
                border: "none",
                background: filterType === "event" ? "var(--bg-card)" : "transparent",
                color: filterType === "event" ? "var(--lilac)" : "var(--text-muted)",
                fontWeight: 700,
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              Events ({markers.filter((m) => m.type === "event").length})
            </button>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {filteredMarkers.length} verified {filteredMarkers.length === 1 ? "venue" : "venues"} within radius
            </span>
            <button
              onClick={() => loadMarkers(centerCoords[0], centerCoords[1], 35)}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text-muted)",
                borderRadius: 8,
                padding: "6px 10px",
                fontSize: 12,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              <RefreshCw size={12} /> Refresh
            </button>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div
            style={{
              padding: "16px 20px",
              background: "rgba(255, 107, 107, 0.12)",
              border: "1px solid var(--danger)",
              borderRadius: 12,
              color: "var(--danger)",
              marginBottom: 20,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>{error}</span>
            <button
              onClick={() => loadMarkers(centerCoords[0], centerCoords[1], 35)}
              className="button"
              style={{ fontSize: 12, padding: "4px 10px" }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Main Grid: Map on Left, Selected Card on Right */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20, alignItems: "start" }}>
          {/* Leaflet OpenStreetMap Container */}
          <div
            style={{
              height: 520,
              borderRadius: 16,
              overflow: "hidden",
              border: "1px solid var(--border)",
              boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
              position: "relative",
            }}
          >
            <MapContainer
              center={centerCoords}
              zoom={mapZoom}
              scrollWheelZoom={false}
              style={{ height: "100%", width: "100%" }}
            >
              <MapRecenter center={centerCoords} zoom={mapZoom} />
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {filteredMarkers.map((m) => (
                <Marker
                  key={m.id}
                  position={[m.latitude, m.longitude]}
                  icon={m.type === "event" ? eventIcon : placeIcon}
                  eventHandlers={{
                    click: () => setSelectedMarker(m),
                  }}
                >
                  <Popup>
                    <div style={{ color: "#1C1126", minWidth: 160 }}>
                      <strong style={{ fontSize: 14 }}>{m.name}</strong>
                      <p style={{ margin: "4px 0", fontSize: 12, color: "#4B5563" }}>
                        {m.category} · {m.city}
                      </p>
                      {m.distance_km && (
                        <p style={{ margin: 0, fontSize: 11, fontWeight: "bold", color: "#16A34A" }}>
                          ~{m.distance_km.toFixed(1)} km away
                        </p>
                      )}
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>

            {/* Map Legend */}
            <div
              style={{
                position: "absolute",
                bottom: 12,
                left: 12,
                background: "rgba(28, 17, 38, 0.90)",
                backdropFilter: "blur(8px)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "6px 12px",
                display: "flex",
                gap: 14,
                fontSize: 11,
                color: "var(--text-muted)",
                zIndex: 1000,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--lime)" }} />
                <span>Coworking / Campus</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--lilac)" }} />
                <span>Tech Event</span>
              </div>
            </div>
          </div>

          {/* Right Column: Selected Venue Details */}
          <div>
            {selectedMarker ? (
              <div
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: 16,
                  padding: 20,
                  boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 800,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      color: selectedMarker.type === "event" ? "var(--lilac)" : "var(--lime)",
                      background:
                        selectedMarker.type === "event"
                          ? "rgba(167,121,232,0.15)"
                          : "rgba(216,245,106,0.15)",
                      padding: "4px 8px",
                      borderRadius: 6,
                    }}
                  >
                    {selectedMarker.type === "event" ? "Tech Event" : selectedMarker.category}
                  </span>
                  {selectedMarker.distance_km && (
                    <span style={{ fontSize: 12, fontWeight: 700, color: "var(--lime)" }}>
                      ~{selectedMarker.distance_km.toFixed(1)} km
                    </span>
                  )}
                </div>

                <h3 style={{ fontSize: 18, fontWeight: 800, color: "var(--text)", margin: "0 0 8px" }}>
                  {selectedMarker.name}
                </h3>

                <div style={{ display: "flex", alignItems: "flex-start", gap: 6, fontSize: 13, color: "var(--text-muted)", marginBottom: 12 }}>
                  <MapPin size={16} color="var(--lime)" style={{ flexShrink: 0, marginTop: 2 }} />
                  <span>
                    {selectedMarker.address}, {selectedMarker.city}
                  </span>
                </div>

                <p style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.5, margin: "0 0 16px" }}>
                  {selectedMarker.description}
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <a
                    href={`https://www.google.com/maps/search/?api=1&query=${selectedMarker.latitude},${selectedMarker.longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="button"
                    style={{
                      padding: "9px 14px",
                      borderRadius: 8,
                      fontSize: 13,
                      fontWeight: 700,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                      textDecoration: "none",
                    }}
                  >
                    <Navigation size={14} /> Open GPS Navigation
                  </a>

                  <Link
                    to={selectedMarker.link}
                    className="button primary"
                    style={{
                      padding: "9px 14px",
                      borderRadius: 8,
                      fontSize: 13,
                      fontWeight: 700,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                      textDecoration: "none",
                    }}
                  >
                    <ExternalLink size={14} /> View Details
                  </Link>
                </div>
              </div>
            ) : (
              <div
                style={{
                  background: "var(--bg-card)",
                  border: "1px dashed var(--border)",
                  borderRadius: 16,
                  padding: 30,
                  textAlign: "center",
                  color: "var(--text-muted)",
                  fontSize: 13,
                }}
              >
                <Compass size={32} style={{ margin: "0 auto 12px", opacity: 0.5 }} />
                <p style={{ margin: "0 0 8px", fontWeight: 700, color: "var(--text)" }}>
                  No Venue Selected
                </p>
                <p style={{ margin: 0 }}>
                  Click any pin on the interactive OpenStreetMap to inspect details and directions.
                </p>
              </div>
            )}

            {/* Quick List of Nearby Places */}
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 8, letterSpacing: "0.06em" }}>
                Nearby In {locationName} ({filteredMarkers.length})
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 220, overflowY: "auto" }}>
                {filteredMarkers.map((m) => (
                  <div
                    key={m.id}
                    onClick={() => {
                      setSelectedMarker(m);
                      setCenterCoords([m.latitude, m.longitude]);
                    }}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 10,
                      background: selectedMarker?.id === m.id ? "rgba(216,245,106,0.08)" : "var(--bg-card)",
                      border: selectedMarker?.id === m.id ? "1px solid var(--lime)" : "1px solid var(--border)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>
                      {m.name}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                      {m.city} · {m.category}
                      {m.distance_km && ` · ${m.distance_km.toFixed(1)} km`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
