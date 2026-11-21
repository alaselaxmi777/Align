import { useEffect, useState } from "react";
import { Plus, LayoutGrid, Smartphone } from "lucide-react";
import AppShell from "../components/layout/AppShell";
import CategoryChips from "../components/common/CategoryChips";
import ReelPlayerModal, { ReelItem } from "../components/ReelPlayerModal";
import ReelCard from "../components/cards/ReelCard";
import VerticalReelsFeed from "../components/VerticalReelsFeed";
import CreateReelModal from "../components/CreateReelModal";
import { api } from "../lib/api";

const REEL_CATEGORIES = [
  "All",
  "Fort Trekking",
  "AgriTech",
  "Marathi Literature",
  "Kushti & Kabaddi",
  "Art & Culture",
  "Technology",
  "Travel",
  "Social",
];

export default function Reels() {
  const [category, setCategory] = useState("All");
  const [viewMode, setViewMode] = useState<"feed" | "grid">("feed");
  const [reels, setReels] = useState<ReelItem[]>([]);
  const [selectedReel, setSelectedReel] = useState<ReelItem | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadReels = () => {
    setLoading(true);
    setError("");
    api.reels(category)
      .then((data) => {
        if (data) {
          setReels(
            data.map((r) => ({
              id: r.id,
              authorId: r.author_id,
              title: r.title,
              authorName: r.author_name,
              authorAvatar: r.author_avatar || undefined,
              category: r.category,
              videoUrl: r.video_url,
              thumbnailUrl: r.thumbnail_url,
              viewsCount: r.views_count,
              likesCount: r.likes_count,
              commentsCount: r.comments_count,
              durationSeconds: r.duration_seconds || undefined,
              visibility: r.visibility,
              audioTrack: r.audio_track || "",
              caption: r.caption || "",
              tags: r.tags || [],
            }))
          );
        }
      })
      .catch((err) => {
        console.error("Failed to load reels:", err);
        setError("Unable to load reels from database.");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadReels();
  }, [category]);

  const filteredReels = reels.filter((r) => {
    if (category === "All") return true;
    return r.category.toLowerCase() === category.toLowerCase();
  });

  const handleReelCreated = (newReel: any) => {
    const mapped: ReelItem = {
      id: newReel.id,
      title: newReel.title,
      authorName: newReel.author_name,
      authorAvatar: newReel.author_avatar || undefined,
      category: newReel.category,
      videoUrl: newReel.video_url,
      thumbnailUrl: newReel.thumbnail_url,
      viewsCount: newReel.views_count || "0 views",
      likesCount: newReel.likes_count || 0,
      commentsCount: newReel.comments_count || 0,
      durationSeconds: newReel.duration_seconds || undefined,
      visibility: newReel.visibility,
      audioTrack: newReel.audio_track || "",
      caption: newReel.caption || "",
      tags: newReel.tags || [],
    };
    setReels((prev) => [mapped, ...prev]);
  };

  return (
    <AppShell title="Reels">
      {/* Top Bar with Title and Actions */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px", marginBottom: "16px" }}>
        <div>
          <p className="eyebrow">In motion, in the moment</p>
          <h1 className="page-title" style={{ margin: "4px 0 8px" }}>Little windows into big worlds.</h1>
          <p className="lead" style={{ margin: 0 }}>
            Explore immersive photo and vertical video reels from across Maharashtra.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {/* View Mode Switcher */}
          <div
            style={{
              display: "inline-flex",
              background: "var(--bg-card, #1e293b)",
              borderRadius: "10px",
              padding: "3px",
              border: "1px solid var(--border-color, #334155)",
            }}
          >
            <button
              type="button"
              onClick={() => setViewMode("feed")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "8px",
                border: "none",
                background: viewMode === "feed" ? "var(--accent-color, #6366f1)" : "transparent",
                color: viewMode === "feed" ? "#fff" : "var(--text-secondary, #94a3b8)",
                fontSize: "13px",
                fontWeight: "600",
                cursor: "pointer",
              }}
            >
              <Smartphone size={16} />
              <span>Feed</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "8px",
                border: "none",
                background: viewMode === "grid" ? "var(--accent-color, #6366f1)" : "transparent",
                color: viewMode === "grid" ? "#fff" : "var(--text-secondary, #94a3b8)",
                fontSize: "13px",
                fontWeight: "600",
                cursor: "pointer",
              }}
            >
              <LayoutGrid size={16} />
              <span>Grid</span>
            </button>
          </div>

          {/* Create Reel Button */}
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 16px",
              borderRadius: "10px",
              border: "none",
              background: "var(--accent-color, #6366f1)",
              color: "#fff",
              fontSize: "13px",
              fontWeight: "600",
              cursor: "pointer",
            }}
          >
            <Plus size={16} />
            <span>Create Reel</span>
          </button>
        </div>
      </div>

      {/* Category Chips */}
      <div style={{ marginBottom: "20px" }}>
        <CategoryChips
          categories={REEL_CATEGORIES}
          activeCategory={category}
          onSelect={setCategory}
        />
      </div>

      {/* Content Rendering */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-secondary)" }}>
          <div className="spinner" style={{ margin: "0 auto 16px" }} />
          <p>Loading verified community reels...</p>
        </div>
      ) : error ? (
        <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--error-color, #ef4444)" }}>
          <p>{error}</p>
        </div>
      ) : filteredReels.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            background: "var(--bg-card)",
            border: "1px dashed var(--border-color)",
            borderRadius: 16,
            color: "var(--text-secondary)",
          }}
        >
          <p style={{ fontSize: 16, fontWeight: 500, marginBottom: 8, color: "var(--text-primary)" }}>
            No community reels in {category} yet
          </p>
          <p style={{ fontSize: 14, marginBottom: 16 }}>
            Be the first creator to share your build, project, or journey with the community!
          </p>
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            style={{
              padding: "8px 18px",
              borderRadius: "8px",
              border: "none",
              background: "var(--accent-color, #6366f1)",
              color: "#fff",
              fontSize: "13px",
              fontWeight: "600",
              cursor: "pointer",
            }}
          >
            Create First Reel
          </button>
        </div>
      ) : viewMode === "feed" ? (
        <VerticalReelsFeed reels={filteredReels} onOpenModal={(r) => setSelectedReel(r)} />
      ) : (
        <div className="reel-grid">
          {filteredReels.map((reel) => (
            <ReelCard
              key={reel.id}
              reel={{
                id: reel.id,
                title: reel.title,
                creator: reel.authorName,
                creatorAvatar: reel.authorAvatar,
                views: reel.viewsCount,
                likes: reel.likesCount,
                category: reel.category,
                imageUrl: reel.thumbnailUrl,
                videoUrl: reel.videoUrl,
                audioTrack: reel.audioTrack,
                description: reel.caption,
              }}
              onOpen={() => setSelectedReel(reel)}
            />
          ))}
        </div>
      )}

      {/* Interactive Reel Modal Player (for grid view or direct modal links) */}
      <ReelPlayerModal
        reel={selectedReel}
        onClose={() => setSelectedReel(null)}
      />

      {/* Create Reel Modal */}
      <CreateReelModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleReelCreated}
      />
    </AppShell>
  );
}
