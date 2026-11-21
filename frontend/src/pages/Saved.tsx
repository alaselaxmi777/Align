import { useEffect, useState } from "react";
import { Bookmark, CalendarDays, LoaderCircle, MapPin, Trash2, Users } from "lucide-react";
import { Link } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import { api, SavedItem } from "../lib/api";

type SavedTab = "communities" | "events" | "places" | "posts" | "reels";

export default function Saved() {
  const [items, setItems] = useState<SavedItem[]>([]);
  const [activeTab, setActiveTab] = useState<SavedTab>("communities");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetchSaved();
  }, []);

  async function fetchSaved() {
    setLoading(true);
    try {
      const data = await api.saved();
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load saved items.");
    } finally {
      setLoading(false);
    }
  }

  async function removeSaved(item: SavedItem) {
    try {
      await api.unsaveItem(item.item_type, item.item_id);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to remove item.");
    }
  }

  const filteredItems = items.filter((item) => {
    if (activeTab === "communities") return item.item_type === "community";
    if (activeTab === "events") return item.item_type === "event";
    if (activeTab === "places") return item.item_type === "place";
    if (activeTab === "posts") return item.item_type === "post";
    if (activeTab === "reels") return item.item_type === "reel";
    return true;
  });

  return (
    <AppShell title="Saved">
      <p className="eyebrow">Your little collection</p>
      <h1 className="page-title">Worth coming back to.</h1>

      {/* Tabs */}
      <div className="chips">
        <button
          type="button"
          className={`chip ${activeTab === "communities" ? "active" : ""}`}
          onClick={() => setActiveTab("communities")}
        >
          Communities
        </button>
        <button
          type="button"
          className={`chip ${activeTab === "events" ? "active" : ""}`}
          onClick={() => setActiveTab("events")}
        >
          Events
        </button>
        <button
          type="button"
          className={`chip ${activeTab === "places" ? "active" : ""}`}
          onClick={() => setActiveTab("places")}
        >
          Places
        </button>
        <button
          type="button"
          className={`chip ${activeTab === "posts" ? "active" : ""}`}
          onClick={() => setActiveTab("posts")}
        >
          Posts
        </button>
        <button
          type="button"
          className={`chip ${activeTab === "reels" ? "active" : ""}`}
          onClick={() => setActiveTab("reels")}
        >
          Photo reels
        </button>
      </div>

      {error && <div className="empty" style={{ color: "var(--error)" }}>{error}</div>}

      {loading ? (
        <div className="empty">
          <LoaderCircle className="spin" size={28} style={{ margin: "0 auto 8px auto", color: "var(--accent)" }} />
          <p>Loading your saved collection...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <p className="empty">
          Nothing saved under {activeTab} yet. Explore and tap Save on something you love.
        </p>
      ) : (
        <div className="grid-3">
          {filteredItems.map((item) => (
            <article className="canva-card" key={item.id}>
              <div className="card-body">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                  <span className="tag">{item.category || item.item_type.toUpperCase()}</span>
                  <button
                    type="button"
                    onClick={() => removeSaved(item)}
                    title="Remove from saved"
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--muted)",
                      cursor: "pointer",
                      padding: "4px",
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <h3>{item.title || `${item.item_type} #${item.item_id}`}</h3>
                <p>{item.description || "Saved item from your ALIGN discovery journey."}</p>

                {item.location && (
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--muted)", marginBottom: "14px" }}>
                    <MapPin size={13} style={{ color: "var(--accent)" }} />
                    <span>{item.location}</span>
                  </div>
                )}

                <div className="card-foot">
                  <Link
                    to={
                      item.item_type === "community"
                        ? `/communities/${item.item_id}`
                        : item.item_type === "event"
                        ? "/events"
                        : item.item_type === "place"
                        ? "/places"
                        : "/feed"
                    }
                    className="button"
                  >
                    View discovery →
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </AppShell>
  );
}
