import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  X,
  Heart,
  MessageSquare,
  Share2,
  Send,
  CornerDownRight,
  Calendar,
  User as UserIcon,
  LoaderCircle,
  ChevronLeft,
  ChevronRight,
  Layers,
  Lock,
  Globe,
  MapPin,
  Pin,
  Reply,
  Sparkles,
  Flag,
  Edit3,
  Trash2,
} from "lucide-react";
import { Post, api } from "../lib/api";
import ShareToDmModal from "./ShareToDmModal";
import { SafeImage, SafeAvatar } from "./common/SafeImage";
import { useToast } from "./common/ToastContext";
import { formatApiError } from "../lib/errorUtils";

type CommentItem = {
  id: number;
  post_id: number;
  author_id: number;
  content: string;
  parent_id?: number | null;
  created_at: string;
  author_name: string;
  author_avatar?: string | null;
  replies?: CommentItem[];
};

interface PostDetailModalProps {
  post: Post | null;
  onClose: () => void;
  onPostUpdated?: (updated: Post) => void;
  onLikeChange?: (postId: number, liked: boolean, count: number) => void;
}

export default function PostDetailModal({ post, onClose, onPostUpdated, onLikeChange }: PostDetailModalProps) {
  if (!post) return null;

  const toast = useToast();
  const [currentPost, setCurrentPost] = useState<Post>(post);
  const [slideIndex, setSlideIndex] = useState(0);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [newComment, setNewComment] = useState("");
  const [replyingTo, setReplyingTo] = useState<{ id: number; name: string } | null>(null);
  const [submittingComment, setSubmittingComment] = useState(false);
  const [shareDmOpen, setShareDmOpen] = useState(false);
  const [pinning, setPinning] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);

  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState("Spam");
  const [reportDetails, setReportDetails] = useState("");
  const [submittingReport, setSubmittingReport] = useState(false);

  // Author Edit & Delete States
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loggedIn = Boolean(localStorage.getItem("align_token"));
  const myName = localStorage.getItem("align_user_name");
  const isAuthor = Boolean(myName && currentPost.author?.name === myName);

  useEffect(() => {
    const targetPost = post;
    if (!targetPost) return;
    setCurrentPost(targetPost);
    setEditContent(targetPost.content);
    setIsEditing(false);
    setSlideIndex(0);
    setReplyingTo(null);
    setPinError(null);

    async function load() {
      setLoadingComments(true);
      try {
        const data = await api.getComments(targetPost.id);
        setComments(data as CommentItem[]);
      } catch (err) {
        console.error("Failed to load comments", err);
      } finally {
        setLoadingComments(false);
      }
    }
    load();
  }, [post?.id]);

  // Keyboard navigation: Escape to close, Arrow keys for carousel slides
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't intercept arrow keys if user is typing in comment input
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (activeTag === "input" || activeTag === "textarea") {
        if (e.key === "Escape") onClose();
        return;
      }

      if (e.key === "Escape") {
        onClose();
        return;
      }
      const mediaCount = currentPost.media?.length || (currentPost.image_url ? 1 : 0);
      if (mediaCount > 1) {
        if (e.key === "ArrowLeft") {
          setSlideIndex((prev) => (prev > 0 ? prev - 1 : mediaCount - 1));
        } else if (e.key === "ArrowRight") {
          setSlideIndex((prev) => (prev < mediaCount - 1 ? prev + 1 : 0));
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, currentPost.media, currentPost.image_url]);

  async function handleToggleLike() {
    if (!loggedIn) {
      toast.info("Please sign in to like this post.");
      return;
    }
    try {
      const res = await api.toggleLike(currentPost.id);
      const updated = {
        ...currentPost,
        is_liked: res.is_liked,
        likes_count: res.likes_count,
      };
      setCurrentPost(updated);
      onPostUpdated?.(updated);
      onLikeChange?.(currentPost.id, res.is_liked, res.likes_count);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleTogglePin() {
    setPinning(true);
    setPinError(null);
    try {
      const res = await api.togglePinPost(currentPost.id);
      const updated = {
        ...currentPost,
        is_pinned: res.is_pinned,
      };
      setCurrentPost(updated);
      onPostUpdated?.(updated);
    } catch (err: any) {
      setPinError(formatApiError(err, "Failed to update pin status."));
    } finally {
      setPinning(false);
    }
  }

  async function handleSaveEdit() {
    if (!editContent.trim()) return;
    setSavingEdit(true);
    try {
      const updated = await api.editPost(currentPost.id, { content: editContent.trim() });
      setCurrentPost(updated);
      setIsEditing(false);
      onPostUpdated?.(updated);
      toast.success("Post updated successfully!");
    } catch (err: any) {
      toast.error(formatApiError(err, "Failed to update post."));
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleDeletePost() {
    if (!confirm("Are you sure you want to delete this post? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await api.deletePost(currentPost.id);
      toast.success("Post deleted successfully.");
      onClose();
      window.location.reload();
    } catch (err: any) {
      toast.error(formatApiError(err, "Failed to delete post."));
    } finally {
      setDeleting(false);
    }
  }

  async function handleSubmitReport(e: FormEvent) {
    e.preventDefault();
    if (!loggedIn) {
      toast.info("Please sign in to report content.");
      return;
    }
    setSubmittingReport(true);
    try {
      await api.createReport({
        target_type: "post",
        target_id: currentPost.id,
        reason: reportReason,
        details: reportDetails.trim() || undefined,
      });
      toast.success("Thank you. Your report has been submitted to the moderation desk.");
      setReportOpen(false);
      setReportDetails("");
    } catch (err: any) {
      toast.error(formatApiError(err, "Failed to submit report."));
    } finally {
      setSubmittingReport(false);
    }
  }

  async function handleAddComment(e: FormEvent) {
    e.preventDefault();
    if (!newComment.trim()) return;
    if (!loggedIn) {
      toast.info("Please sign in to leave a comment.");
      return;
    }
    setSubmittingComment(true);
    try {
      const added = await api.addComment(
        currentPost.id,
        newComment.trim(),
        replyingTo ? replyingTo.id : undefined
      );

      if (replyingTo) {
        // Append to specific parent comment's replies
        setComments((prev) =>
          prev.map((c) => {
            if (c.id === replyingTo.id) {
              return {
                ...c,
                replies: [...(c.replies || []), added as CommentItem],
              };
            }
            return c;
          })
        );
      } else {
        setComments((prev) => [...prev, { ...(added as CommentItem), replies: [] }]);
      }

      setNewComment("");
      setReplyingTo(null);

      const updated = {
        ...currentPost,
        comments_count: (currentPost.comments_count || 0) + 1,
      };
      setCurrentPost(updated);
      onPostUpdated?.(updated);
    } catch (err: any) {
      toast.error(formatApiError(err, "Failed to add comment."));
    } finally {
      setSubmittingComment(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 60,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
        background: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(8px)",
      }}
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Post by ${currentPost.author?.name || "member"}`}
        tabIndex={-1}
        style={{
          position: "relative",
          width: "100%",
          maxWidth: "1050px",
          maxHeight: "85vh",
          background: "var(--bg-card)",
          borderRadius: "16px",
          overflow: "hidden",
          display: "flex",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.4)",
          border: "1px solid var(--border-subtle)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          style={{
            position: "absolute",
            top: "14px",
            right: "14px",
            zIndex: 20,
            background: "rgba(0,0,0,0.4)",
            border: "none",
            borderRadius: "50%",
            width: "32px",
            height: "32px",
            display: "grid",
            placeItems: "center",
            color: "#fff",
            cursor: "pointer",
          }}
          aria-label="Close post"
        >
          <X size={18} />
        </button>

        {/* Left Side: Media carousel / Image */}
        <div
          style={{
            flex: "1 1 50%",
            background: "#000000",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            minHeight: "400px",
            maxHeight: "85vh",
          }}
        >
          {(() => {
            const mediaList =
              currentPost.media && currentPost.media.length > 0
                ? currentPost.media
                : currentPost.image_url
                ? [
                    {
                      id: 0,
                      position: 0,
                      media_type: "image",
                      original_url: currentPost.image_url,
                      feed_url: currentPost.image_url,
                      thumbnail_url: currentPost.image_url,
                    },
                  ]
                : [];

            if (mediaList.length === 0) {
              return (
                <div style={{ color: "#64748b", fontSize: "14px", padding: "40px", textAlign: "center" }}>
                  <Layers size={40} style={{ margin: "0 auto 12px", opacity: 0.5 }} />
                  <p>Text-only update</p>
                </div>
              );
            }

            const activeMedia = mediaList[slideIndex] || mediaList[0];

            return (
              <div style={{ position: "relative", width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                {activeMedia.media_type === "video" ? (
                  <video
                    src={activeMedia.original_url || activeMedia.feed_url}
                    controls
                    playsInline
                    style={{ width: "100%", maxHeight: "85vh", objectFit: "contain" }}
                  />
                ) : (
                  <SafeImage
                    src={activeMedia.feed_url || activeMedia.original_url}
                    alt={activeMedia.alt_text || currentPost.content.slice(0, 30)}
                    style={{ width: "100%", maxHeight: "85vh", objectFit: "contain" }}
                  />
                )}

                {/* Left/Right Arrows for Carousel */}
                {mediaList.length > 1 && (
                  <>
                    <button
                      type="button"
                      onClick={() => setSlideIndex((prev) => (prev > 0 ? prev - 1 : mediaList.length - 1))}
                      style={{
                        position: "absolute",
                        left: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "rgba(0, 0, 0, 0.6)",
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: "50%",
                        width: "36px",
                        height: "36px",
                        display: "grid",
                        placeItems: "center",
                        cursor: "pointer",
                        zIndex: 5,
                      }}
                      aria-label="Previous slide"
                    >
                      <ChevronLeft size={20} />
                    </button>
                    <button
                      type="button"
                      onClick={() => setSlideIndex((prev) => (prev < mediaList.length - 1 ? prev + 1 : 0))}
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "rgba(0, 0, 0, 0.6)",
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: "50%",
                        width: "36px",
                        height: "36px",
                        display: "grid",
                        placeItems: "center",
                        cursor: "pointer",
                        zIndex: 5,
                      }}
                      aria-label="Next slide"
                    >
                      <ChevronRight size={20} />
                    </button>

                    {/* Dots indicator */}
                    <div
                      style={{
                        position: "absolute",
                        bottom: "16px",
                        display: "flex",
                        gap: "6px",
                        zIndex: 5,
                      }}
                    >
                      {mediaList.map((_, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => setSlideIndex(i)}
                          style={{
                            width: i === slideIndex ? "18px" : "6px",
                            height: "6px",
                            borderRadius: "3px",
                            background: i === slideIndex ? "var(--primary-accent, #6366f1)" : "rgba(255, 255, 255, 0.5)",
                            border: "none",
                            padding: 0,
                            cursor: "pointer",
                            transition: "all 0.2s ease",
                          }}
                          aria-label={`Go to slide ${i + 1}`}
                        />
                      ))}
                    </div>
                  </>
                )}
              </div>
            );
          })()}
        </div>

        {/* Right Side: Header, Comments & Actions */}
        <div
          style={{
            flex: "1 1 50%",
            display: "flex",
            flexDirection: "column",
            maxHeight: "85vh",
            background: "var(--bg-card)",
          }}
        >
          {/* Author Header */}
          <div
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
              <Link
                to={currentPost.author?.id ? `/profile/${currentPost.author.id}` : "/profile"}
                onClick={onClose}
                style={{
                  width: "38px",
                  height: "38px",
                  borderRadius: "50%",
                  overflow: "hidden",
                  background: "var(--bg-secondary)",
                  display: "grid",
                  placeItems: "center",
                  flexShrink: 0,
                  textDecoration: "none",
                }}
              >
                <SafeAvatar
                  src={currentPost.author?.avatar_url}
                  name={currentPost.author?.name}
                  size={40}
                />
              </Link>

              <div style={{ minWidth: 0 }}>
                <Link
                  to={currentPost.author?.id ? `/profile/${currentPost.author.id}` : "/profile"}
                  onClick={onClose}
                  style={{
                    fontWeight: 700,
                    fontSize: "14px",
                    color: "var(--primary-text)",
                    textDecoration: "none",
                  }}
                >
                  {currentPost.author?.name || "ALIGN Member"}
                </Link>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", marginTop: "2px" }}>
                  {currentPost.visibility === "connections_only" ? (
                    <span style={{ fontSize: "10px", padding: "1px 6px", borderRadius: "4px", background: "rgba(83, 101, 245, 0.12)", color: "var(--primary-accent)", display: "inline-flex", alignItems: "center", gap: "3px", fontWeight: 600 }}>
                      <Lock size={10} /> Connections
                    </span>
                  ) : (
                    <span style={{ fontSize: "10px", padding: "1px 6px", borderRadius: "4px", background: "rgba(16, 185, 129, 0.12)", color: "#10b981", display: "inline-flex", alignItems: "center", gap: "3px", fontWeight: 600 }}>
                      <Globe size={10} /> Public
                    </span>
                  )}
                  {currentPost.location_area && (
                    <span style={{ fontSize: "10px", padding: "1px 6px", borderRadius: "4px", background: "var(--bg-secondary)", color: "var(--secondary-text)", display: "inline-flex", alignItems: "center", gap: "3px" }}>
                      <MapPin size={10} /> {currentPost.location_area}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Author or Viewer Action Buttons */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              {isAuthor ? (
                <>
                  <button
                    type="button"
                    onClick={handleTogglePin}
                    disabled={pinning}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      padding: "5px 9px",
                      borderRadius: "8px",
                      border: "1px solid var(--border-subtle)",
                      background: currentPost.is_pinned ? "rgba(99, 102, 241, 0.15)" : "transparent",
                      color: currentPost.is_pinned ? "var(--primary-accent)" : "var(--secondary-text)",
                      fontSize: "11px",
                      fontWeight: "600",
                      cursor: pinning ? "not-allowed" : "pointer",
                    }}
                    title={currentPost.is_pinned ? "Unpin post" : "Pin post (max 3)"}
                  >
                    <Pin size={12} style={{ transform: "rotate(45deg)" }} />
                    <span>{currentPost.is_pinned ? "Pinned" : "Pin"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsEditing(!isEditing)}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      padding: "5px 9px",
                      borderRadius: "8px",
                      border: "1px solid var(--border-subtle)",
                      background: isEditing ? "rgba(250, 204, 21, 0.15)" : "transparent",
                      color: isEditing ? "#eab308" : "var(--secondary-text)",
                      fontSize: "11px",
                      fontWeight: "600",
                      cursor: "pointer",
                    }}
                    title="Edit post caption"
                  >
                    <Edit3 size={12} />
                    <span>{isEditing ? "Cancel" : "Edit"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleDeletePost}
                    disabled={deleting}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      padding: "5px 9px",
                      borderRadius: "8px",
                      border: "1px solid rgba(239, 68, 68, 0.3)",
                      background: "rgba(239, 68, 68, 0.1)",
                      color: "#ef4444",
                      fontSize: "11px",
                      fontWeight: "600",
                      cursor: deleting ? "not-allowed" : "pointer",
                    }}
                    title="Delete post"
                  >
                    <Trash2 size={12} />
                    <span>{deleting ? "Deleting…" : "Delete"}</span>
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setReportOpen(true)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    padding: "5px 9px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-subtle)",
                    background: "transparent",
                    color: "var(--secondary-text)",
                    fontSize: "11px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                  title="Report inappropriate content"
                >
                  <Flag size={12} />
                  <span>Report</span>
                </button>
              )}
            </div>
          </div>

          {pinError && (
            <div style={{ padding: "6px 20px", background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", fontSize: "12px" }}>
              {pinError}
            </div>
          )}

          {/* Comments List & Caption Scroll Container */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "18px 20px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            {/* Original Post Caption or Edit Area */}
            <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
              <div style={{ flex: 1 }}>
                {isEditing ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      rows={3}
                      style={{
                        width: "100%",
                        padding: "8px 10px",
                        borderRadius: "8px",
                        border: "1px solid var(--border-subtle)",
                        background: "var(--bg-secondary)",
                        color: "var(--primary-text)",
                        fontSize: "13px",
                        resize: "none",
                        outline: "none",
                      }}
                    />
                    <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                      <button
                        type="button"
                        onClick={() => {
                          setIsEditing(false);
                          setEditContent(currentPost.content);
                        }}
                        style={{
                          padding: "4px 10px",
                          borderRadius: "6px",
                          border: "1px solid var(--border-subtle)",
                          background: "transparent",
                          fontSize: "11px",
                          cursor: "pointer",
                          color: "var(--secondary-text)",
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={handleSaveEdit}
                        disabled={savingEdit || !editContent.trim()}
                        style={{
                          padding: "4px 12px",
                          borderRadius: "6px",
                          border: "none",
                          background: "var(--primary-accent)",
                          color: "#fff",
                          fontSize: "11px",
                          fontWeight: 600,
                          cursor: savingEdit ? "not-allowed" : "pointer",
                        }}
                      >
                        {savingEdit ? "Saving…" : "Save"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p style={{ margin: "0 0 4px 0", fontSize: "13px", lineHeight: "1.5", color: "var(--primary-text)" }}>
                      <strong style={{ marginRight: "6px" }}>{currentPost.author?.name || "Author"}</strong>
                      {currentPost.content}
                    </p>
                    <span style={{ fontSize: "11px", color: "var(--secondary-text)" }}>
                      {new Date(currentPost.created_at).toLocaleDateString()}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* 6-Factor Hybrid Ranking & SHAP Explanation */}
            {currentPost.why_recommended && (
              <div
                style={{
                  padding: "10px 12px",
                  borderRadius: "8px",
                  background: "rgba(99, 102, 241, 0.08)",
                  border: "1px solid rgba(99, 102, 241, 0.2)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--primary-accent)", fontSize: "11px", fontWeight: 700 }}>
                  <Sparkles size={13} />
                  <span>Why in your feed · {currentPost.score ? `${Math.round(currentPost.score * 100)}% Match` : "Recommended"}</span>
                </div>
                <div style={{ fontSize: "12px", color: "var(--primary-text)", lineHeight: 1.4 }}>
                  {currentPost.why_recommended}
                </div>
                {currentPost.score_breakdown && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "2px" }}>
                    {Object.entries(currentPost.score_breakdown).map(([factor, val]) => (
                      <span
                        key={factor}
                        style={{
                          fontSize: "10px",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: "var(--bg-secondary)",
                          color: "var(--secondary-text)",
                          fontFamily: "monospace",
                        }}
                      >
                        {factor}: +{val.toFixed(3)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div style={{ height: "1px", background: "var(--border-subtle)", margin: "4px 0" }} />

            {/* Comments & Replies */}
            {loadingComments ? (
              <div style={{ display: "flex", justifyContent: "center", padding: "20px" }}>
                <LoaderCircle className="spin" size={24} style={{ color: "var(--primary-accent)" }} />
              </div>
            ) : comments.length === 0 ? (
              <div style={{ textAlign: "center", padding: "24px 0", color: "var(--secondary-text)", fontSize: "13px" }}>
                <p style={{ margin: 0 }}>No comments yet.</p>
                <span style={{ fontSize: "12px" }}>Start the conversation!</span>
              </div>
            ) : (
              comments.map((c) => (
                <div key={c.id} style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {/* Parent Comment */}
                  <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                    <div
                      style={{
                        width: "30px",
                        height: "30px",
                        borderRadius: "50%",
                        overflow: "hidden",
                        background: "var(--bg-secondary)",
                        display: "grid",
                        placeItems: "center",
                        flexShrink: 0,
                      }}
                    >
                      <SafeAvatar
                        src={c.author_avatar}
                        name={c.author_name}
                        size={30}
                      />
                    </div>
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: "0 0 2px 0", fontSize: "13px", lineHeight: "1.4", color: "var(--primary-text)" }}>
                        <strong style={{ marginRight: "6px" }}>{c.author_name}</strong>
                        {c.content}
                      </p>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "2px" }}>
                        <span style={{ fontSize: "11px", color: "var(--secondary-text)" }}>
                          {new Date(c.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                        <button
                          type="button"
                          onClick={() => setReplyingTo({ id: c.id, name: c.author_name })}
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--secondary-text)",
                            fontSize: "11px",
                            fontWeight: "600",
                            cursor: "pointer",
                            padding: 0,
                          }}
                        >
                          Reply
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* 1-Level Threaded Replies */}
                  {c.replies && c.replies.length > 0 && (
                    <div style={{ marginLeft: "36px", paddingLeft: "10px", borderLeft: "2px solid var(--border-subtle)", display: "flex", flexDirection: "column", gap: "8px" }}>
                      {c.replies.map((reply) => (
                        <div key={reply.id} style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
                          <div
                            style={{
                              width: "24px",
                              height: "24px",
                              borderRadius: "50%",
                              overflow: "hidden",
                              background: "var(--bg-secondary)",
                              display: "grid",
                              placeItems: "center",
                              flexShrink: 0,
                            }}
                          >
                            <SafeAvatar
                              src={reply.author_avatar}
                              name={reply.author_name}
                              size={24}
                            />
                          </div>
                          <div style={{ flex: 1 }}>
                            <p style={{ margin: "0 0 2px 0", fontSize: "12px", lineHeight: "1.4", color: "var(--primary-text)" }}>
                              <strong style={{ marginRight: "6px" }}>{reply.author_name}</strong>
                              {reply.content}
                            </p>
                            <span style={{ fontSize: "10px", color: "var(--secondary-text)" }}>
                              {new Date(reply.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Action Bar */}
          <div
            style={{
              padding: "12px 20px",
              borderTop: "1px solid var(--border-subtle)",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
              <button
                type="button"
                onClick={handleToggleLike}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  color: currentPost.is_liked ? "var(--error-color, #ef4444)" : "var(--primary-text)",
                  padding: "4px",
                }}
                title={currentPost.is_liked ? "Unlike" : "Like"}
              >
                <Heart size={22} fill={currentPost.is_liked ? "var(--error-color, #ef4444)" : "none"} />
              </button>

              <button
                type="button"
                onClick={() => setShareDmOpen(true)}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--primary-text)",
                  padding: "4px",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
                title="Send in Direct Message"
              >
                <Send size={19} />
              </button>

              <button
                type="button"
                onClick={() => setReportOpen(true)}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--secondary-text)",
                  padding: "4px",
                  display: "inline-flex",
                  alignItems: "center",
                }}
                title="Report Post"
                aria-label="Report post for moderation"
              >
                <Flag size={18} />
              </button>

              <button
                type="button"
                onClick={() => {
                  if (navigator.clipboard) {
                    navigator.clipboard.writeText(window.location.origin + `/feed?post=${currentPost.id}`);
                    toast.success("Post link copied to clipboard!");
                  }
                }}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--primary-text)",
                  padding: "4px",
                  marginLeft: "auto",
                }}
                title="Copy Link"
              >
                <Share2 size={19} />
              </button>
            </div>

            {/* Likes count */}
            <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--primary-text)" }}>
              {currentPost.likes_count || 0} {currentPost.likes_count === 1 ? "like" : "likes"}
            </span>
          </div>

          {/* Replying To Pill */}
          {replyingTo && (
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "6px 18px",
                background: "rgba(99, 102, 241, 0.15)",
                color: "var(--primary-accent, #6366f1)",
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
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 18px",
              borderTop: "1px solid var(--border-subtle)",
              background: "var(--bg-card)",
            }}
          >
            <input
              type="text"
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder={replyingTo ? `Reply to ${replyingTo.name}...` : "Add a comment..."}
              style={{
                flex: 1,
                border: "none",
                outline: "none",
                background: "transparent",
                color: "var(--primary-text)",
                fontSize: "13px",
              }}
            />
            <button
              type="submit"
              disabled={submittingComment || !newComment.trim()}
              style={{
                background: "transparent",
                border: "none",
                color: newComment.trim() ? "var(--primary-accent)" : "var(--secondary-text)",
                fontWeight: "700",
                fontSize: "13px",
                cursor: newComment.trim() ? "pointer" : "default",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              {submittingComment ? <LoaderCircle className="spin" size={14} /> : "Post"}
            </button>
          </form>
        </div>
      </div>

      {/* Share to DM Modal */}
      <ShareToDmModal
        itemType="post"
        itemId={currentPost.id}
        itemTitle={currentPost.content}
        isOpen={shareDmOpen}
        onClose={() => setShareDmOpen(false)}
      />

      {/* Report Modal */}
      {reportOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 70,
            background: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "16px",
          }}
          onClick={() => !submittingReport && setReportOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Report Post"
            style={{
              width: "100%",
              maxWidth: "420px",
              background: "var(--bg-card, #1e293b)",
              borderRadius: "16px",
              padding: "20px",
              border: "1px solid var(--border-color, #334155)",
              color: "var(--primary-text)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Flag size={18} style={{ color: "#ef4444" }} />
                <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700 }}>Report Content</h3>
              </div>
              <button
                type="button"
                onClick={() => setReportOpen(false)}
                disabled={submittingReport}
                style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer" }}
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSubmitReport} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "4px" }}>
                  Reason for Report
                </label>
                <select
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "8px",
                    background: "var(--bg-secondary)",
                    color: "inherit",
                    border: "1px solid var(--border-subtle)",
                    fontSize: "13px",
                  }}
                >
                  <option value="Spam">Spam or Commercial Solicitation</option>
                  <option value="Harassment">Harassment or Hate Speech</option>
                  <option value="Inappropriate / NSFW">Inappropriate / NSFW Content</option>
                  <option value="Misinformation">Misinformation</option>
                  <option value="Intellectual Property">Copyright / Impersonation</option>
                  <option value="Other">Other Community Standard Violation</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, marginBottom: "4px" }}>
                  Additional Details (Optional)
                </label>
                <textarea
                  value={reportDetails}
                  onChange={(e) => setReportDetails(e.target.value)}
                  placeholder="Explain why this content violates guidelines..."
                  rows={3}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "8px",
                    background: "var(--bg-secondary)",
                    color: "inherit",
                    border: "1px solid var(--border-subtle)",
                    fontSize: "13px",
                    resize: "none",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button
                  type="button"
                  onClick={() => setReportOpen(false)}
                  disabled={submittingReport}
                  style={{
                    padding: "8px 14px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-subtle)",
                    background: "transparent",
                    color: "inherit",
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingReport}
                  style={{
                    padding: "8px 16px",
                    borderRadius: "8px",
                    border: "none",
                    background: "#ef4444",
                    color: "#ffffff",
                    fontWeight: 700,
                    fontSize: "13px",
                    cursor: submittingReport ? "not-allowed" : "pointer",
                  }}
                >
                  {submittingReport ? "Submitting..." : "Submit Report"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
