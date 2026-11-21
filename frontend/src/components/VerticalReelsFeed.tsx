import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Heart,
  MessageSquare,
  Share2,
  Volume2,
  VolumeX,
  Play,
  Pause,
  Music,
  Lock,
  Globe,
  Send,
  X,
  User as UserIcon,
  Reply,
  Trash2,
} from "lucide-react";
import { ReelItem } from "./ReelPlayerModal";
import { api } from "../lib/api";
import ShareToDmModal from "./ShareToDmModal";
import { SafeAvatar } from "./common/SafeImage";

interface VerticalReelsFeedProps {
  reels: ReelItem[];
  onOpenModal?: (reel: ReelItem) => void;
}

export default function VerticalReelsFeed({ reels }: VerticalReelsFeedProps) {
  const [reelsList, setReelsList] = useState<ReelItem[]>(reels);
  const myUserName = localStorage.getItem("align_user_name");

  useEffect(() => {
    setReelsList(reels);
  }, [reels]);

  const [activeIndex, setActiveIndex] = useState(0);
  const [isMuted, setIsMuted] = useState(true);
  const [playingStates, setPlayingStates] = useState<Record<number, boolean>>({});
  const [likesState, setLikesState] = useState<Record<number, { isLiked: boolean; count: number }>>({});
  const [progressState, setProgressState] = useState<Record<number, number>>({});
  const [copiedId, setCopiedId] = useState<number | null>(null);

  // Comments Drawer & Replies
  const [activeCommentsReelId, setActiveCommentsReelId] = useState<number | null>(null);
  const [comments, setComments] = useState<any[]>([]);
  const [commentInput, setCommentInput] = useState("");
  const [replyingTo, setReplyingTo] = useState<{ id: number; name: string } | null>(null);
  const [loadingComments, setLoadingComments] = useState(false);

  // DM Share Modal
  const [dmShareReel, setDmShareReel] = useState<{ id: number; title: string } | null>(null);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const videoRefs = useRef<Record<number, HTMLVideoElement | null>>({});
  const viewedReels = useRef<Set<number>>(new Set());

  // Initialize likes
  useEffect(() => {
    const initialLikes: Record<number, { isLiked: boolean; count: number }> = {};
    reels.forEach((r) => {
      initialLikes[r.id] = { isLiked: false, count: r.likesCount };
    });
    setLikesState(initialLikes);
  }, [reels]);

  // IntersectionObserver to auto-play active video
  useEffect(() => {
    const options = {
      root: containerRef.current,
      threshold: 0.6,
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const indexStr = entry.target.getAttribute("data-index");
        if (!indexStr) return;
        const index = parseInt(indexStr, 10);
        const reel = reels[index];
        if (!reel) return;

        const video = videoRefs.current[reel.id];

        if (entry.isIntersecting) {
          setActiveIndex(index);
          if (video) {
            video.currentTime = 0;
            video.play().catch(() => {});
            setPlayingStates((prev) => ({ ...prev, [reel.id]: true }));
          }

          // Record view once per reel session
          if (!viewedReels.current.has(reel.id)) {
            viewedReels.current.add(reel.id);
            api.recordReelView(reel.id).catch(() => {});
          }
        } else {
          if (video) {
            video.pause();
            setPlayingStates((prev) => ({ ...prev, [reel.id]: false }));
          }
        }
      });
    }, options);

    const slides = containerRef.current?.querySelectorAll(".reel-slide");
    slides?.forEach((slide) => observer.observe(slide));

    return () => {
      slides?.forEach((slide) => observer.unobserve(slide));
    };
  }, [reels]);

  // Keyboard accessibility for Reels: ArrowDown/j for next, ArrowUp/k for prev, m for mute, Space for play/pause
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (activeTag === "input" || activeTag === "textarea") {
        if (e.key === "Escape") {
          setActiveCommentsReelId(null);
        }
        return;
      }

      if (e.key === "Escape") {
        if (activeCommentsReelId) {
          setActiveCommentsReelId(null);
          return;
        }
        if (dmShareReel) {
          setDmShareReel(null);
          return;
        }
      }

      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        if (activeIndex < reels.length - 1) {
          const nextIndex = activeIndex + 1;
          const slides = containerRef.current?.querySelectorAll(".reel-slide");
          slides?.[nextIndex]?.scrollIntoView({ behavior: "smooth" });
        }
      } else if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        if (activeIndex > 0) {
          const prevIndex = activeIndex - 1;
          const slides = containerRef.current?.querySelectorAll(".reel-slide");
          slides?.[prevIndex]?.scrollIntoView({ behavior: "smooth" });
        }
      } else if (e.key === "m" || e.key === "M") {
        e.preventDefault();
        toggleMute();
      } else if (e.key === " " || e.code === "Space") {
        e.preventDefault();
        const currentReel = reels[activeIndex];
        if (currentReel) {
          togglePlay(currentReel.id);
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeIndex, reels, isMuted]);

  const togglePlay = (reelId: number) => {
    const video = videoRefs.current[reelId];
    if (!video) return;

    if (video.paused) {
      video.play().catch(() => {});
      setPlayingStates((prev) => ({ ...prev, [reelId]: true }));
    } else {
      video.pause();
      setPlayingStates((prev) => ({ ...prev, [reelId]: false }));
    }
  };

  const toggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    Object.values(videoRefs.current).forEach((vid) => {
      if (vid) vid.muted = nextMuted;
    });
  };

  const handleLike = async (reelId: number) => {
    const current = likesState[reelId] || { isLiked: false, count: 0 };
    const nextLiked = !current.isLiked;
    const nextCount = nextLiked ? current.count + 1 : Math.max(0, current.count - 1);

    setLikesState((prev) => ({
      ...prev,
      [reelId]: { isLiked: nextLiked, count: nextCount },
    }));

    try {
      const res = await api.toggleReelLike(reelId);
      setLikesState((prev) => ({
        ...prev,
        [reelId]: { isLiked: res.is_liked, count: res.likes_count },
      }));
    } catch (err) {
      // Revert on error
      setLikesState((prev) => ({ ...prev, [reelId]: current }));
    }
  };

  const handleShare = (reelId: number) => {
    const url = `${window.location.origin}/reels?id=${reelId}`;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url);
      setCopiedId(reelId);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const openComments = async (reelId: number) => {
    setActiveCommentsReelId(reelId);
    setReplyingTo(null);
    setLoadingComments(true);
    try {
      const data = await api.getReelComments(reelId);
      setComments(data || []);
    } catch (e) {
      setComments([]);
    } finally {
      setLoadingComments(false);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeCommentsReelId || !commentInput.trim()) return;

    try {
      const newComment = await api.addReelComment(
        activeCommentsReelId,
        commentInput.trim(),
        replyingTo ? replyingTo.id : undefined
      );

      if (replyingTo) {
        setComments((prev) =>
          prev.map((c) => {
            if (c.id === replyingTo.id) {
              return {
                ...c,
                replies: [...(c.replies || []), newComment],
              };
            }
            return c;
          })
        );
      } else {
        setComments((prev) => [newComment, ...prev]);
      }

      setCommentInput("");
      setReplyingTo(null);
    } catch (err) {
      console.error("Failed to add comment:", err);
    }
  };

  const handleDeleteReel = async (reelId: number) => {
    if (!confirm("Are you sure you want to delete this reel? This cannot be undone.")) return;
    try {
      await api.deleteReel(reelId);
      setReelsList((prev) => prev.filter((r) => r.id !== reelId));
    } catch (err: any) {
      alert(err.message || "Failed to delete reel.");
    }
  };

  return (
    <div style={{ position: "relative", width: "100%", maxWidth: "440px", margin: "0 auto" }}>
      {/* Sound Toggle (floating top-right) */}
      <button
        type="button"
        onClick={toggleMute}
        style={{
          position: "absolute",
          top: "16px",
          right: "16px",
          zIndex: 30,
          background: "rgba(0, 0, 0, 0.6)",
          backdropFilter: "blur(8px)",
          border: "none",
          borderRadius: "50%",
          width: "40px",
          height: "40px",
          display: "grid",
          placeItems: "center",
          color: "#fff",
          cursor: "pointer",
        }}
        aria-label={isMuted ? "Unmute audio" : "Mute audio"}
      >
        {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
      </button>

      {/* Vertical Snap Container */}
      <div
        ref={containerRef}
        style={{
          height: "calc(100vh - 180px)",
          minHeight: "560px",
          maxHeight: "780px",
          overflowY: "scroll",
          scrollSnapType: "y mandatory",
          scrollBehavior: "smooth",
          borderRadius: "20px",
          boxShadow: "0 20px 40px rgba(0, 0, 0, 0.4)",
          background: "#000",
        }}
      >
        {reelsList.map((reel, index) => {
          const isPlaying = playingStates[reel.id] ?? false;
          const likeData = likesState[reel.id] || { isLiked: false, count: reel.likesCount };
          const progress = progressState[reel.id] || 0;

          return (
            <div
              key={reel.id}
              className="reel-slide"
              data-index={index}
              style={{
                position: "relative",
                width: "100%",
                height: "100%",
                scrollSnapAlign: "start",
                scrollSnapStop: "always",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "#050505",
                overflow: "hidden",
              }}
            >
              {/* Video Element */}
              <video
                ref={(el) => (videoRefs.current[reel.id] = el)}
                src={reel.videoUrl}
                poster={reel.thumbnailUrl}
                loop
                muted={isMuted}
                playsInline
                onClick={() => togglePlay(reel.id)}
                onTimeUpdate={(e) => {
                  const target = e.currentTarget;
                  if (target.duration) {
                    setProgressState((prev) => ({
                      ...prev,
                      [reel.id]: (target.currentTime / target.duration) * 100,
                    }));
                  }
                }}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  cursor: "pointer",
                }}
              />

              {/* Pause Overlay indicator */}
              {!isPlaying && (
                <div
                  onClick={() => togglePlay(reel.id)}
                  style={{
                    position: "absolute",
                    inset: 0,
                    display: "grid",
                    placeItems: "center",
                    background: "rgba(0, 0, 0, 0.25)",
                    cursor: "pointer",
                    pointerEvents: "auto",
                  }}
                >
                  <div
                    style={{
                      width: "60px",
                      height: "60px",
                      borderRadius: "50%",
                      background: "rgba(0, 0, 0, 0.6)",
                      backdropFilter: "blur(6px)",
                      display: "grid",
                      placeItems: "center",
                      color: "#fff",
                    }}
                  >
                    <Play size={28} fill="#fff" style={{ marginLeft: "4px" }} />
                  </div>
                </div>
              )}

              {/* Top gradient */}
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  height: "80px",
                  background: "linear-gradient(to bottom, rgba(0,0,0,0.6) 0%, transparent 100%)",
                  pointerEvents: "none",
                }}
              />

              {/* Right Action Rail */}
              <div
                style={{
                  position: "absolute",
                  right: "12px",
                  bottom: "90px",
                  zIndex: 20,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "18px",
                }}
              >
                {/* Author Avatar */}
                <Link
                  to={reel.authorId ? `/profile/${reel.authorId}` : "/profile"}
                  style={{ position: "relative", display: "block", textDecoration: "none" }}
                  title={`View ${reel.authorName}'s profile`}
                >
                  <div
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "50%",
                      border: "2px solid #fff",
                      overflow: "hidden",
                      background: "#333",
                    }}
                  >
                    <SafeAvatar
                      src={reel.authorAvatar}
                      name={reel.authorName}
                      size={44}
                    />
                  </div>
                </Link>

                {/* Like Button */}
                <button
                  type="button"
                  onClick={() => handleLike(reel.id)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: likeData.isLiked ? "#ef4444" : "#ffffff",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <div
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "50%",
                      background: "rgba(0, 0, 0, 0.4)",
                      backdropFilter: "blur(4px)",
                      display: "grid",
                      placeItems: "center",
                      transition: "transform 0.15s ease",
                    }}
                  >
                    <Heart size={22} fill={likeData.isLiked ? "#ef4444" : "none"} />
                  </div>
                  <span style={{ fontSize: "11px", fontWeight: "600", color: "#fff", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
                    {likeData.count}
                  </span>
                </button>

                {/* Comment Button */}
                <button
                  type="button"
                  onClick={() => openComments(reel.id)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#ffffff",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <div
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "50%",
                      background: "rgba(0, 0, 0, 0.4)",
                      backdropFilter: "blur(4px)",
                      display: "grid",
                      placeItems: "center",
                    }}
                  >
                    <MessageSquare size={22} />
                  </div>
                  <span style={{ fontSize: "11px", fontWeight: "600", color: "#fff", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
                    {reel.commentsCount}
                  </span>
                </button>

                {/* Send in Direct Message */}
                <button
                  type="button"
                  onClick={() => setDmShareReel({ id: reel.id, title: reel.title })}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#ffffff",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "4px",
                  }}
                  title="Send in Direct Message"
                >
                  <div
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "50%",
                      background: "rgba(0, 0, 0, 0.4)",
                      backdropFilter: "blur(4px)",
                      display: "grid",
                      placeItems: "center",
                    }}
                  >
                    <Send size={19} />
                  </div>
                  <span style={{ fontSize: "11px", fontWeight: "600", color: "#fff", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
                    Send
                  </span>
                </button>

                {/* Share Link Button */}
                <button
                  type="button"
                  onClick={() => handleShare(reel.id)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#ffffff",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "4px",
                  }}
                  title="Copy link"
                >
                  <div
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "50%",
                      background: "rgba(0, 0, 0, 0.4)",
                      backdropFilter: "blur(4px)",
                      display: "grid",
                      placeItems: "center",
                    }}
                  >
                    <Share2 size={20} />
                  </div>
                  <span style={{ fontSize: "11px", fontWeight: "600", color: "#fff", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
                    {copiedId === reel.id ? "Copied!" : "Link"}
                  </span>
                </button>

                {/* Author Delete Button */}
                {myUserName && myUserName === reel.authorName && (
                  <button
                    type="button"
                    onClick={() => handleDeleteReel(reel.id)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "#ef4444",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "4px",
                    }}
                    title="Delete Reel"
                  >
                    <div
                      style={{
                        width: "44px",
                        height: "44px",
                        borderRadius: "50%",
                        background: "rgba(239, 68, 68, 0.25)",
                        backdropFilter: "blur(4px)",
                        border: "1px solid rgba(239, 68, 68, 0.5)",
                        display: "grid",
                        placeItems: "center",
                      }}
                    >
                      <Trash2 size={20} />
                    </div>
                    <span style={{ fontSize: "11px", fontWeight: "600", color: "#ef4444", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
                      Delete
                    </span>
                  </button>
                )}

                {/* Audio Disc Badge */}
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #333 0%, #111 100%)",
                    border: "2px solid #555",
                    display: "grid",
                    placeItems: "center",
                    color: "#fff",
                    animation: isPlaying ? "spin 4s linear infinite" : "none",
                  }}
                >
                  <Music size={16} />
                </div>
              </div>

              {/* Bottom Metadata Overlay */}
              <div
                style={{
                  position: "absolute",
                  bottom: 0,
                  left: 0,
                  right: "70px",
                  padding: "20px 16px 24px",
                  background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 60%, transparent 100%)",
                  color: "#fff",
                  pointerEvents: "auto",
                }}
              >
                {/* Author Name + Badge */}
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                  <Link
                    to={reel.authorId ? `/profile/${reel.authorId}` : "/profile"}
                    style={{ fontWeight: "700", fontSize: "15px", color: "#fff", textDecoration: "none" }}
                  >
                    {reel.authorName}
                  </Link>
                  {reel.visibility === "connections_only" ? (
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "11px",
                        background: "rgba(245, 158, 11, 0.3)",
                        color: "#fbbf24",
                        padding: "2px 6px",
                        borderRadius: "6px",
                      }}
                    >
                      <Lock size={10} /> Connections
                    </span>
                  ) : (
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "11px",
                        background: "rgba(255, 255, 255, 0.2)",
                        color: "#e2e8f0",
                        padding: "2px 6px",
                        borderRadius: "6px",
                      }}
                    >
                      <Globe size={10} /> Public
                    </span>
                  )}
                  {reel.durationSeconds && (
                    <span style={{ fontSize: "11px", color: "#cbd5e1", opacity: 0.8 }}>
                      · {Math.round(reel.durationSeconds)}s
                    </span>
                  )}
                </div>

                {/* Title */}
                <h3 style={{ fontSize: "14px", fontWeight: "600", margin: "0 0 6px", lineHeight: "1.3" }}>
                  {reel.title}
                </h3>

                {/* Caption */}
                {reel.caption && (
                  <p
                    style={{
                      fontSize: "13px",
                      margin: "0 0 8px",
                      color: "#e2e8f0",
                      lineHeight: "1.3",
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {reel.caption}
                  </p>
                )}

                {/* Tags */}
                {reel.tags && reel.tags.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "8px" }}>
                    {reel.tags.map((t, idx) => (
                      <span key={idx} style={{ fontSize: "12px", color: "var(--accent-color, #818cf8)", fontWeight: "500" }}>
                        #{t}
                      </span>
                    ))}
                  </div>
                )}

                {/* Audio Track Attribution */}
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#cbd5e1" }}>
                  <Music size={12} />
                  <span>{reel.audioTrack || "Original Audio"}</span>
                </div>
              </div>

              {/* Progress bar */}
              <div
                style={{
                  position: "absolute",
                  bottom: 0,
                  left: 0,
                  right: 0,
                  height: "3px",
                  background: "rgba(255, 255, 255, 0.2)",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${progress}%`,
                    background: "var(--accent-color, #6366f1)",
                    transition: "width 0.1s linear",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Slide-over Comments Drawer */}
      {activeCommentsReelId && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Reel comments"
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: "65%",
            zIndex: 40,
            background: "var(--bg-card, #1e293b)",
            borderTopLeftRadius: "20px",
            borderTopRightRadius: "20px",
            boxShadow: "0 -10px 30px rgba(0,0,0,0.5)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            color: "#fff",
          }}
        >
          {/* Drawer Header */}
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--border-color, #334155)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <strong style={{ fontSize: "14px" }}>Comments ({comments.length})</strong>
            <button
              type="button"
              onClick={() => setActiveCommentsReelId(null)}
              style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer" }}
            >
              <X size={18} />
            </button>
          </div>

          {/* Comments List */}
          <div style={{ flex: 1, overflowY: "auto", padding: "14px 16px", display: "flex", flexDirection: "column", gap: "12px" }}>
            {loadingComments ? (
              <div style={{ textAlign: "center", color: "#94a3b8", padding: "20px" }}>Loading comments...</div>
            ) : comments.length === 0 ? (
              <div style={{ textAlign: "center", color: "#94a3b8", padding: "20px" }}>No comments yet. Say something!</div>
            ) : (
              comments.map((c) => (
                <div key={c.id} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ display: "flex", gap: "10px" }}>
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "50%",
                        background: "#334155",
                        overflow: "hidden",
                        flexShrink: 0,
                      }}
                    >
                      <SafeAvatar
                        src={c.user_avatar}
                        name={c.user_name}
                        size={32}
                      />
                    </div>
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: "12px", color: "#e2e8f0" }}>{c.user_name}</strong>
                      <p style={{ margin: "2px 0 0", fontSize: "13px", color: "#cbd5e1" }}>{c.content}</p>
                      <button
                        type="button"
                        onClick={() => setReplyingTo({ id: c.id, name: c.user_name })}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#94a3b8",
                          fontSize: "11px",
                          fontWeight: "600",
                          cursor: "pointer",
                          padding: "2px 0 0",
                        }}
                      >
                        Reply
                      </button>
                    </div>
                  </div>

                  {/* Nested replies */}
                  {c.replies && c.replies.length > 0 && (
                    <div style={{ marginLeft: "36px", paddingLeft: "10px", borderLeft: "2px solid #334155", display: "flex", flexDirection: "column", gap: "8px" }}>
                      {c.replies.map((reply: any) => (
                        <div key={reply.id} style={{ display: "flex", gap: "8px" }}>
                          <div
                            style={{
                              width: "24px",
                              height: "24px",
                              borderRadius: "50%",
                              background: "#334155",
                              overflow: "hidden",
                              flexShrink: 0,
                            }}
                          >
                            <SafeAvatar
                              src={reply.user_avatar}
                              name={reply.user_name}
                              size={24}
                            />
                          </div>
                          <div>
                            <strong style={{ fontSize: "11px", color: "#e2e8f0" }}>{reply.user_name}</strong>
                            <p style={{ margin: "1px 0 0", fontSize: "12px", color: "#cbd5e1" }}>{reply.content}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Replying To Pill */}
          {replyingTo && (
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "6px 16px",
                background: "rgba(99, 102, 241, 0.2)",
                color: "#a5b4fc",
                fontSize: "12px",
                fontWeight: "600",
              }}
            >
              <span>Replying to @{replyingTo.name}</span>
              <button
                type="button"
                onClick={() => setReplyingTo(null)}
                style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer", padding: "2px" }}
              >
                <X size={14} />
              </button>
            </div>
          )}

          {/* Add Comment Input */}
          <form
            onSubmit={handleAddComment}
            style={{
              padding: "10px 14px",
              borderTop: "1px solid var(--border-color, #334155)",
              display: "flex",
              gap: "8px",
              background: "var(--bg-input, #0f172a)",
            }}
          >
            <input
              type="text"
              value={commentInput}
              onChange={(e) => setCommentInput(e.target.value)}
              placeholder={replyingTo ? `Reply to ${replyingTo.name}...` : "Add a comment..."}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "20px",
                border: "1px solid #334155",
                background: "#1e293b",
                color: "#fff",
                fontSize: "13px",
              }}
            />
            <button
              type="submit"
              disabled={!commentInput.trim()}
              style={{
                background: "var(--accent-color, #6366f1)",
                color: "#fff",
                border: "none",
                borderRadius: "50%",
                width: "36px",
                height: "36px",
                display: "grid",
                placeItems: "center",
                cursor: commentInput.trim() ? "pointer" : "not-allowed",
                opacity: commentInput.trim() ? 1 : 0.5,
              }}
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      )}

      {/* DM Share Modal */}
      {dmShareReel && (
        <ShareToDmModal
          itemType="reel"
          itemId={dmShareReel.id}
          itemTitle={dmShareReel.title}
          isOpen={true}
          onClose={() => setDmShareReel(null)}
        />
      )}
    </div>
  );
}
