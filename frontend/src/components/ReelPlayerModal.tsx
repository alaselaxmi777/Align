import { useState, useRef, useEffect } from "react";
import { X, Heart, MessageSquare, Share2, Bookmark, Volume2, VolumeX, Play, Pause, Music, User as UserIcon, Check } from "lucide-react";
import { api } from "../lib/api";
import { SafeAvatar } from "./common/SafeImage";

export interface ReelItem {
  id: number;
  authorId?: number;
  title: string;
  authorName: string;
  authorAvatar?: string;
  category: string;
  videoUrl?: string;
  thumbnailUrl: string;
  viewsCount: string;
  likesCount: number;
  commentsCount: number;
  audioTrack: string;
  caption: string;
  tags: string[];
  durationSeconds?: number;
  visibility?: string;
}

interface ReelPlayerModalProps {
  reel: ReelItem | null;
  onClose: () => void;
}

export default function ReelPlayerModal({ reel, onClose }: ReelPlayerModalProps) {
  if (!reel) return null;

  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(true);
  const [isLiked, setIsLiked] = useState(false);
  const [likesCount, setLikesCount] = useState(reel.likesCount);
  const [isSaved, setIsSaved] = useState(false);
  const [isFollowing, setIsFollowing] = useState(false);
  const [copied, setCopied] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // Record view on reel play
  useEffect(() => {
    if (reel?.id) {
      api.recordReelView(reel.id).catch(() => {});
    }
  }, [reel?.id]);

  function togglePlay() {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play();
        setIsPlaying(true);
      } else {
        videoRef.current.pause();
        setIsPlaying(false);
      }
    } else {
      setIsPlaying(!isPlaying);
    }
  }

  function toggleMute() {
    if (videoRef.current) {
      videoRef.current.muted = !videoRef.current.muted;
      setIsMuted(videoRef.current.muted);
    } else {
      setIsMuted(!isMuted);
    }
  }

  async function handleLike() {
    if (!reel) return;
    setIsLiked(!isLiked);
    setLikesCount((prev) => (isLiked ? prev - 1 : prev + 1));
    try {
      const res = await api.toggleReelLike(reel.id);
      setIsLiked(res.is_liked);
      setLikesCount(res.likes_count);
    } catch (e) {
      // optimistic fallback
    }
  }

  async function handleToggleSave() {
    if (!reel) return;
    const nextSaved = !isSaved;
    setIsSaved(nextSaved);
    try {
      if (nextSaved) {
        await api.saveItem("reel", reel.id);
      } else {
        await api.unsaveItem("reel", reel.id);
      }
    } catch (e) {
      // optimistic fallback
    }
  }

  function handleShare() {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 70,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
        background: "rgba(0, 0, 0, 0.85)",
        backdropFilter: "blur(12px)",
      }}
      onClick={onClose}
    >
      {/* Close button */}
      <button
        type="button"
        onClick={onClose}
        style={{
          position: "fixed",
          top: "20px",
          right: "24px",
          zIndex: 80,
          width: "40px",
          height: "40px",
          borderRadius: "50%",
          background: "rgba(255, 255, 255, 0.15)",
          backdropFilter: "blur(8px)",
          border: "none",
          color: "#FFFFFF",
          display: "grid",
          placeItems: "center",
          cursor: "pointer",
          transition: "transform 0.2s ease, background 0.2s ease",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.3)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.15)")}
        aria-label="Close Reels Player"
      >
        <X size={22} />
      </button>

      {/* Main Reel Container */}
      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: "420px",
          height: "85vh",
          maxHeight: "780px",
          borderRadius: "20px",
          overflow: "hidden",
          background: "#000000",
          boxShadow: "0 25px 60px rgba(0, 0, 0, 0.6)",
          display: "flex",
          flexDirection: "column",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Video or Animated Video Card */}
        <div
          style={{
            position: "relative",
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
          }}
          onClick={togglePlay}
        >
          {reel.videoUrl ? (
            <video
              ref={videoRef}
              src={reel.videoUrl}
              poster={reel.thumbnailUrl}
              loop
              autoPlay
              playsInline
              muted={isMuted}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
          ) : (
            <div
              style={{
                position: "relative",
                width: "100%",
                height: "100%",
                backgroundImage: `url(${reel.thumbnailUrl})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }}
            >
              {/* Play / Pause pulse overlay */}
              {!isPlaying && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    display: "grid",
                    placeItems: "center",
                    background: "rgba(0, 0, 0, 0.45)",
                  }}
                >
                  <div
                    style={{
                      width: "68px",
                      height: "68px",
                      borderRadius: "50%",
                      background: "rgba(255, 255, 255, 0.25)",
                      backdropFilter: "blur(8px)",
                      display: "grid",
                      placeItems: "center",
                      color: "#FFFFFF",
                    }}
                  >
                    <Play size={32} fill="#FFFFFF" />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Top Gradient & Controls */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              padding: "18px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              background: "linear-gradient(180deg, rgba(0, 0, 0, 0.7) 0%, transparent 100%)",
              zIndex: 10,
            }}
          >
            <span
              style={{
                color: "#FFFFFF",
                fontSize: "13px",
                fontWeight: "700",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                textShadow: "0 2px 4px rgba(0,0,0,0.5)",
              }}
            >
              <Play size={14} fill="#FFFFFF" /> ALIGN Reels
            </span>

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                toggleMute();
              }}
              style={{
                background: "rgba(0, 0, 0, 0.5)",
                border: "none",
                borderRadius: "50%",
                width: "34px",
                height: "34px",
                color: "#FFFFFF",
                display: "grid",
                placeItems: "center",
                cursor: "pointer",
              }}
            >
              {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
            </button>
          </div>

          {/* Right Floating Actions (Instagram Style) */}
          <div
            style={{
              position: "absolute",
              right: "12px",
              bottom: "90px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "18px",
              zIndex: 20,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Like Button */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
              <button
                type="button"
                onClick={handleLike}
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "50%",
                  background: isLiked ? "rgba(239, 68, 68, 0.25)" : "rgba(0, 0, 0, 0.4)",
                  border: "none",
                  color: isLiked ? "#EF4444" : "#FFFFFF",
                  display: "grid",
                  placeItems: "center",
                  cursor: "pointer",
                  transition: "transform 0.15s ease",
                }}
              >
                <Heart size={24} fill={isLiked ? "#EF4444" : "none"} strokeWidth={isLiked ? 0 : 2} />
              </button>
              <span style={{ color: "#FFFFFF", fontSize: "11px", fontWeight: "700", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
                {likesCount}
              </span>
            </div>

            {/* Comment Button */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
              <button
                type="button"
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "50%",
                  background: "rgba(0, 0, 0, 0.4)",
                  border: "none",
                  color: "#FFFFFF",
                  display: "grid",
                  placeItems: "center",
                  cursor: "pointer",
                }}
              >
                <MessageSquare size={22} strokeWidth={2} />
              </button>
              <span style={{ color: "#FFFFFF", fontSize: "11px", fontWeight: "700", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
                {reel.commentsCount}
              </span>
            </div>

            {/* Bookmark Button */}
            <button
              type="button"
              onClick={handleToggleSave}
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "50%",
                background: "rgba(0, 0, 0, 0.4)",
                border: "none",
                color: isSaved ? "#FBBF24" : "#FFFFFF",
                display: "grid",
                placeItems: "center",
                cursor: "pointer",
              }}
              title="Save Reel"
            >
              <Bookmark size={22} fill={isSaved ? "#FBBF24" : "none"} strokeWidth={isSaved ? 0 : 2} />
            </button>

            {/* Share Button */}
            <button
              type="button"
              onClick={handleShare}
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "50%",
                background: "rgba(0, 0, 0, 0.4)",
                border: "none",
                color: "#FFFFFF",
                display: "grid",
                placeItems: "center",
                cursor: "pointer",
              }}
              title="Share Reel"
            >
              {copied ? <Check size={20} style={{ color: "#34D399" }} /> : <Share2 size={20} />}
            </button>
          </div>

          {/* Bottom Overlay: Author, Caption, Audio */}
          <div
            style={{
              position: "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              padding: "20px 18px",
              background: "linear-gradient(0deg, rgba(0, 0, 0, 0.9) 0%, rgba(0, 0, 0, 0.6) 60%, transparent 100%)",
              zIndex: 15,
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Author details & follow button */}
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div className="story-ring" style={{ padding: "2px" }}>
                <div className="story-ring-inner" style={{ padding: "1px" }}>
                  <div
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "50%",
                      overflow: "hidden",
                      background: "rgba(255, 255, 255, 0.2)",
                      display: "grid",
                      placeItems: "center",
                    }}
                  >
                    <SafeAvatar
                      src={reel.authorAvatar}
                      name={reel.authorName}
                      size={36}
                    />
                  </div>
                </div>
              </div>

              <span style={{ color: "#FFFFFF", fontWeight: "700", fontSize: "14px", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
                {reel.authorName}
              </span>

              <button
                type="button"
                onClick={() => setIsFollowing(!isFollowing)}
                style={{
                  padding: "4px 12px",
                  borderRadius: "9999px",
                  border: isFollowing ? "1px solid rgba(255,255,255,0.4)" : "1px solid #FFFFFF",
                  background: isFollowing ? "transparent" : "#FFFFFF",
                  color: isFollowing ? "#FFFFFF" : "#000000",
                  fontSize: "11px",
                  fontWeight: "700",
                  cursor: "pointer",
                }}
              >
                {isFollowing ? "Following" : "Follow"}
              </button>

              <span style={{ marginLeft: "auto", color: "rgba(255,255,255,0.8)", fontSize: "11px", fontWeight: "600" }}>
                {reel.viewsCount} views
              </span>
            </div>

            {/* Caption */}
            <p
              style={{
                margin: 0,
                color: "#FFFFFF",
                fontSize: "13px",
                lineHeight: "1.4",
                textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                maxHeight: "44px",
                overflow: "hidden",
              }}
            >
              {reel.caption}
            </p>

            {/* Audio Ticker */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                color: "rgba(255, 255, 255, 0.85)",
                fontSize: "11px",
                fontWeight: "500",
              }}
            >
              <Music size={12} />
              <span>{reel.audioTrack}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
