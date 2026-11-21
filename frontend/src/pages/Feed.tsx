import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import {
  Bookmark,
  Calendar,
  Grid3X3,
  Heart,
  Image,
  Layers,
  LoaderCircle,
  MessageCircle,
  MessageSquare,
  Plus,
  Send,
  Share2,
  Sparkles,
  Upload,
  User as UserIcon,
  Lock,
  Globe,
  MapPin,
  Trash2,
  X as CloseIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import { SafeImage, SafeAvatar } from "../components/common/SafeImage";
import PostCard from "../components/cards/PostCard";
import PostDetailModal from "../components/PostDetailModal";
import { api, Post } from "../lib/api";
import { useToast } from "../components/common/ToastContext";
import { formatApiError } from "../lib/errorUtils";

type CommentItem = {
  id: number;
  post_id: number;
  author_id: number;
  content: string;
  created_at: string;
  author_name: string;
  author_avatar?: string | null;
};

export default function Feed() {
  const toast = useToast();
  const [posts, setPosts] = useState<Post[]>([]);
  const [viewMode, setViewMode] = useState<"grid" | "stream" | "saved">("grid");
  const [content, setContent] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [visibility, setVisibility] = useState<"connections_only" | "public">("connections_only");
  const [locationArea, setLocationArea] = useState("");
  const [mediaItems, setMediaItems] = useState<
    Array<{
      position: number;
      media_type: string;
      original_url: string;
      feed_url: string;
      thumbnail_url: string;
      width: number;
      height: number;
      alt_text?: string;
      isLocalPreview?: boolean;
    }>
  >([]);
  const localPreviewUrlsRef = useRef<string[]>([]);
  const [uploadingMedia, setUploadingMedia] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Comments state for stream view
  const [openComments, setOpenComments] = useState<Record<number, boolean>>({});
  const [commentsMap, setCommentsMap] = useState<Record<number, CommentItem[]>>({});
  const [commentInputs, setCommentInputs] = useState<Record<number, string>>({});
  const [commentingMap, setCommentingMap] = useState<Record<number, boolean>>({});

  const loggedIn = Boolean(localStorage.getItem("align_token"));

  useEffect(() => {
    loadFeed();
  }, []);

  async function loadFeed() {
    setLoading(true);
    setError("");
    try {
      const feedData = await api.feed();
      setPosts(feedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load feed");
    } finally {
      setLoading(false);
    }
  }

  // Cleanup local object preview URLs on unmount
  useEffect(() => {
    return () => {
      localPreviewUrlsRef.current.forEach((url) => {
        try {
          URL.revokeObjectURL(url);
        } catch {}
      });
    };
  }, []);

  async function handleCreatePost(e: FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    setSubmitting(true);
    try {
      const newPost = await api.createPost({
        content: content.trim(),
        visibility,
        location_area: locationArea.trim() || undefined,
        media_items: mediaItems,
        image_url: mediaItems.length > 0 ? mediaItems[0].feed_url : (imageUrl.trim() || undefined),
      });
      setPosts([newPost, ...posts]);
      setContent("");
      setImageUrl("");
      setMediaItems([]);
      setLocationArea("");
      setVisibility("connections_only");
      setShowCreateModal(false);
      toast.success("Post published to community feed!");
    } catch (err) {
      toast.error(formatApiError(err, "Failed to create post."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleImageUpload(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    if (mediaItems.length + files.length > 10) {
      toast.warning("A post can contain at most 10 carousel images.");
      return;
    }

    // 1. Instant local preview using URL.createObjectURL
    const startIndex = mediaItems.length;
    const instantItems = files.map((file, i) => {
      const blobUrl = URL.createObjectURL(file);
      localPreviewUrlsRef.current.push(blobUrl);
      return {
        position: startIndex + i,
        media_type: "image",
        original_url: blobUrl,
        feed_url: blobUrl,
        thumbnail_url: blobUrl,
        width: 1080,
        height: 1080,
        alt_text: "",
        isLocalPreview: true,
      };
    });

    setMediaItems((prev) => [...prev, ...instantItems]);
    setUploadingMedia(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const res = await api.uploadImageVariant(file);
        const targetPos = startIndex + i;
        setMediaItems((prev) =>
          prev.map((item) =>
            item.position === targetPos
              ? {
                  position: targetPos,
                  media_type: "image",
                  original_url: res.original_url,
                  feed_url: res.feed_url,
                  thumbnail_url: res.thumbnail_url,
                  width: res.width,
                  height: res.height,
                  alt_text: "",
                  isLocalPreview: false,
                }
              : item
          )
        );
      }
    } catch (err) {
      toast.error(formatApiError(err, "Image upload failed."));
      // Rollback unuploaded local items
      setMediaItems((prev) => prev.filter((item) => !item.isLocalPreview));
    } finally {
      setUploadingMedia(false);
      // Reset input value so same file can be re-selected if desired
      e.target.value = "";
    }
  }

  async function toggleLike(postId: number) {
    if (!loggedIn) {
      window.location.href = "/login";
      return;
    }
    try {
      const res = await api.toggleLike(postId);
      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId ? { ...p, is_liked: res.is_liked, likes_count: res.likes_count } : p
        )
      );
    } catch (err) {
      console.error("Like toggle error:", err);
    }
  }

  async function toggleOpenComments(postId: number) {
    const nextState = !openComments[postId];
    setOpenComments((prev) => ({ ...prev, [postId]: nextState }));
    if (nextState && !commentsMap[postId]) {
      try {
        const comments = await api.getComments(postId);
        setCommentsMap((prev) => ({ ...prev, [postId]: comments }));
      } catch (err) {
        console.error("Failed to load comments", err);
      }
    }
  }

  async function handleAddComment(e: FormEvent, postId: number) {
    e.preventDefault();
    const txt = commentInputs[postId]?.trim();
    if (!txt) return;
    if (!loggedIn) {
      window.location.href = "/login";
      return;
    }
    setCommentingMap((prev) => ({ ...prev, [postId]: true }));
    try {
      const newComment = await api.addComment(postId, txt);
      setCommentsMap((prev) => ({
        ...prev,
        [postId]: [...(prev[postId] || []), newComment],
      }));
      setCommentInputs((prev) => ({ ...prev, [postId]: "" }));
      setPosts((prev) =>
        prev.map((p) => (p.id === postId ? { ...p, comments_count: (p.comments_count || 0) + 1 } : p))
      );
    } catch (err) {
      toast.error(formatApiError(err, "Failed to add comment."));
    } finally {
      setCommentingMap((prev) => ({ ...prev, [postId]: false }));
    }
  }

  return (
    <AppShell title="Posts">
      {/* Profile / Community Stories Header */}
      <div className="profile-info">
        <div>
          <p className="eyebrow">Community stories</p>
          <h1 className="page-title">The moments in between.</h1>
          <p className="lead" style={{ margin: "0 0 12px 0" }}>
            A visual journal from curious people and creators across ALIGN.
          </p>
          <div className="stats">
            <span>
              <b>{posts.length}</b> {posts.length === 1 ? "post" : "posts"}
            </span>
          </div>
        </div>

        <div className="actions">
          {loggedIn && (
            <Link to="/messages" className="button">
              Messages
            </Link>
          )}
          {loggedIn && (
            <button
              type="button"
              className="button primary"
              onClick={() => setShowCreateModal(true)}
              style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
            >
              <Plus size={16} /> New post
            </button>
          )}
        </div>
      </div>

      {/* Tabs: Grid (Instagram 3-column), Stream (Detailed Cards), Saved */}
      <div className="chips" style={{ marginBottom: "24px" }}>
        <button
          type="button"
          className={`chip ${viewMode === "grid" ? "active" : ""}`}
          onClick={() => setViewMode("grid")}
          style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
        >
          <Grid3X3 size={15} /> Posts Grid
        </button>
        <button
          type="button"
          className={`chip ${viewMode === "stream" ? "active" : ""}`}
          onClick={() => setViewMode("stream")}
          style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
        >
          <Layers size={15} /> Card Stream
        </button>
        <button
          type="button"
          className={`chip ${viewMode === "saved" ? "active" : ""}`}
          onClick={() => setViewMode("saved")}
          style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
        >
          <Bookmark size={15} /> Saved
        </button>
      </div>

      {error && <div className="empty" style={{ color: "var(--error)" }}>{error}</div>}

      {/* TAB 1: Instagram 3-column square photo grid */}
      {viewMode === "grid" && (
        <>
          {loading ? (
            <div className="empty">
              <LoaderCircle className="spin" size={28} style={{ margin: "0 auto 8px auto", color: "var(--accent)" }} />
              <p>Loading posts...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="empty">
              <p>No posts published yet. Share the first moment!</p>
              {loggedIn && (
                <button
                  type="button"
                  className="button primary"
                  onClick={() => setShowCreateModal(true)}
                  style={{ marginTop: "12px" }}
                >
                  Create post
                </button>
              )}
            </div>
          ) : (
            <div className="photo-grid">
              {posts.map((post) => (
                <PostCard key={post.id} post={post} onOpen={setSelectedPost} />
              ))}
            </div>
          )}
        </>
      )}

      {/* TAB 2: Detailed Card Stream */}
      {viewMode === "stream" && (
        <div style={{ maxWidth: "680px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
          {loading ? (
            <div className="empty">
              <LoaderCircle className="spin" size={28} style={{ margin: "0 auto 8px auto", color: "var(--accent)" }} />
              <p>Loading stream...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="empty">No stream posts available.</div>
          ) : (
            posts.map((post) => {
              const isLiked = Boolean(post.is_liked);
              const comments = commentsMap[post.id] || [];
              const isCommentsOpen = openComments[post.id] || false;
              const isSubmittingComment = commentingMap[post.id] || false;

              return (
                <article
                  key={post.id}
                  className="canva-card"
                  style={{ borderRadius: "20px" }}
                >
                  {/* Author Header */}
                  <Link
                    to={post.author?.id ? `/profile/${post.author.id}` : "/profile"}
                    style={{
                      padding: "16px 20px",
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      textDecoration: "none",
                      color: "inherit",
                    }}
                    title={`View ${post.author?.name || "author"}'s profile`}
                  >
                    <div className="story-ring" style={{ padding: "2px" }}>
                      <div className="story-ring-inner" style={{ padding: "1.5px" }}>
                        <div
                          style={{
                            width: "38px",
                            height: "38px",
                            borderRadius: "50%",
                            overflow: "hidden",
                            background: "var(--sub)",
                            display: "grid",
                            placeItems: "center",
                          }}
                        >
                          <SafeAvatar
                            src={post.author?.avatar_url}
                            name={post.author?.name}
                            size={38}
                          />
                        </div>
                      </div>
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: "14px", fontWeight: "700", color: "var(--text)" }}>
                        {post.author?.name || "ALIGN Creator"}
                      </h4>
                      <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                        {new Date(post.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                        })}
                        {post.community_name ? ` · ${post.community_name}` : ""}
                      </span>
                    </div>
                  </Link>

                  {/* Post Image */}
                  {post.image_url && (
                    <SafeImage
                      src={post.image_url}
                      alt={post.content.slice(0, 50)}
                      style={{ width: "100%", maxHeight: "540px", objectFit: "cover", display: "block" }}
                      loading="lazy"
                    />
                  )}

                  {/* Actions & Caption */}
                  <div style={{ padding: "16px 20px" }}>
                    <div style={{ display: "flex", gap: "16px", alignItems: "center", marginBottom: "12px" }}>
                      <button
                        type="button"
                        onClick={() => toggleLike(post.id)}
                        style={{
                          background: "none",
                          border: "none",
                          color: isLiked ? "#EF4444" : "var(--text)",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          cursor: "pointer",
                          fontWeight: "700",
                          fontSize: "14px",
                          padding: 0,
                        }}
                      >
                        <Heart size={20} fill={isLiked ? "#EF4444" : "none"} />
                        <span>{post.likes_count || 0}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => toggleOpenComments(post.id)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--text)",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          cursor: "pointer",
                          fontWeight: "700",
                          fontSize: "14px",
                          padding: 0,
                        }}
                      >
                        <MessageSquare size={20} />
                        <span>{post.comments_count || 0}</span>
                      </button>
                    </div>

                    <p style={{ margin: 0, fontSize: "14.5px", lineHeight: "1.6", color: "var(--text)" }}>
                      <strong>{post.author?.name || "Creator"}:</strong> {post.content}
                    </p>

                    {/* Inline Comments */}
                    {isCommentsOpen && (
                      <div style={{ marginTop: "16px", paddingTop: "14px", borderTop: "1px solid var(--line)" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "14px" }}>
                          {comments.map((comm) => (
                            <div key={comm.id} style={{ fontSize: "13px" }}>
                              <strong style={{ color: "var(--text)" }}>{comm.author_name}:</strong>{" "}
                              <span style={{ color: "var(--muted)" }}>{comm.content}</span>
                            </div>
                          ))}
                        </div>

                        {loggedIn && (
                          <form onSubmit={(e) => handleAddComment(e, post.id)} style={{ display: "flex", gap: "8px" }}>
                            <input
                              type="text"
                              className="search"
                              placeholder="Write a comment..."
                              value={commentInputs[post.id] || ""}
                              onChange={(e) =>
                                setCommentInputs((prev) => ({ ...prev, [post.id]: e.target.value }))
                              }
                              style={{ height: "36px", fontSize: "13px" }}
                            />
                            <button
                              type="submit"
                              className="button primary"
                              disabled={isSubmittingComment}
                              style={{ padding: "6px 14px", fontSize: "12px" }}
                            >
                              Post
                            </button>
                          </form>
                        )}
                      </div>
                    )}
                  </div>
                </article>
              );
            })
          )}
        </div>
      )}

      {/* TAB 3: Saved */}
      {viewMode === "saved" && (
        <div className="empty">
          <p>Save posts by clicking the bookmark action in modal view.</p>
          <Link to="/saved" className="button">
            View all saved discoveries →
          </Link>
        </div>
      )}

      {/* Create Post Modal */}
      {showCreateModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
            zIndex: 1000,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowCreateModal(false);
          }}
        >
          <div
            style={{
              background: "var(--card)",
              borderRadius: "20px",
              padding: "28px",
              maxWidth: "520px",
              width: "100%",
              border: "1px solid var(--line)",
              boxShadow: "0 20px 50px rgba(0,0,0,0.3)",
            }}
          >
            <h2 style={{ fontSize: "20px", fontWeight: "800", color: "var(--text)", margin: "0 0 16px 0" }}>
              Share a Post
            </h2>
            <form onSubmit={handleCreatePost}>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="What project, insight, or photo are you sharing?"
                rows={4}
                className="search"
                style={{
                  width: "100%",
                  height: "auto",
                  padding: "12px",
                  borderRadius: "14px",
                  resize: "vertical",
                  marginBottom: "14px",
                }}
                required
              />

              {/* Multi-Image Carousel Uploader */}
              <div style={{ marginBottom: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                  <label style={{ fontSize: "13px", fontWeight: 700, color: "var(--text)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <Layers size={14} style={{ color: "var(--primary-accent)" }} />
                    Photo Carousel ({mediaItems.length}/10 images)
                  </label>
                  <label
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      cursor: mediaItems.length >= 10 ? "not-allowed" : "pointer",
                      fontSize: "12px",
                      color: mediaItems.length >= 10 ? "var(--muted)" : "var(--primary-accent)",
                      fontWeight: 600,
                    }}
                  >
                    <Upload size={13} />
                    {uploadingMedia ? "Processing WebP variants..." : "+ Add photos"}
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      multiple
                      onChange={handleImageUpload}
                      style={{ display: "none" }}
                      disabled={uploadingMedia || mediaItems.length >= 10}
                    />
                  </label>
                </div>

                {/* Previews strip */}
                {mediaItems.length > 0 && (
                  <div style={{ display: "flex", gap: "10px", overflowX: "auto", paddingBottom: "6px", marginBottom: "10px" }}>
                    {mediaItems.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          position: "relative",
                          width: "80px",
                          height: "80px",
                          borderRadius: "10px",
                          overflow: "hidden",
                          flexShrink: 0,
                          border: "2px solid var(--border-color)",
                        }}
                      >
                        <SafeImage
                          src={item.thumbnail_url || item.feed_url}
                          alt={item.alt_text || `Slide ${idx + 1}`}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        />
                        <button
                          type="button"
                          onClick={() => setMediaItems((prev) => prev.filter((_, i) => i !== idx))}
                          style={{
                            position: "absolute",
                            top: "4px",
                            right: "4px",
                            background: "rgba(0,0,0,0.7)",
                            color: "#fff",
                            border: "none",
                            borderRadius: "50%",
                            width: "20px",
                            height: "20px",
                            display: "grid",
                            placeItems: "center",
                            cursor: "pointer",
                            padding: 0,
                          }}
                          aria-label={`Remove image ${idx + 1}`}
                        >
                          <CloseIcon size={12} />
                        </button>
                        <span
                          style={{
                            position: "absolute",
                            bottom: "3px",
                            left: "4px",
                            background: "rgba(0,0,0,0.75)",
                            color: "#fff",
                            fontSize: "10px",
                            padding: "1px 4px",
                            borderRadius: "4px",
                            fontWeight: 700,
                          }}
                        >
                          {idx + 1}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Coarse Location & Privacy Visibility */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" }}>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text)", display: "flex", alignItems: "center", gap: "4px", marginBottom: "6px" }}>
                    <MapPin size={12} style={{ color: "var(--primary-accent)" }} />
                    Area / City (Coarse)
                  </label>
                  <input
                    type="text"
                    value={locationArea}
                    onChange={(e) => setLocationArea(e.target.value)}
                    placeholder="e.g. Sinhagad, Pune"
                    className="search"
                    style={{ width: "100%", height: "36px", fontSize: "12px" }}
                  />
                  {/* Quick Maharashtra Chips */}
                  <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginTop: "4px" }}>
                    {["Pune", "Mumbai", "Kolhapur", "Nagpur", "Nashik"].map((city) => (
                      <button
                        key={city}
                        type="button"
                        onClick={() => setLocationArea(city)}
                        style={{
                          border: "none",
                          background: locationArea === city ? "var(--primary-accent)" : "var(--bg-secondary)",
                          color: locationArea === city ? "#fff" : "var(--text-secondary)",
                          fontSize: "10px",
                          borderRadius: "4px",
                          padding: "2px 6px",
                          cursor: "pointer",
                        }}
                      >
                        {city}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text)", display: "flex", alignItems: "center", gap: "4px", marginBottom: "6px" }}>
                    {visibility === "connections_only" ? <Lock size={12} style={{ color: "var(--primary-accent)" }} /> : <Globe size={12} style={{ color: "#10b981" }} />}
                    Audience Visibility
                  </label>
                  <div style={{ display: "flex", gap: "6px" }}>
                    <button
                      type="button"
                      onClick={() => setVisibility("connections_only")}
                      style={{
                        flex: 1,
                        padding: "8px 6px",
                        borderRadius: "8px",
                        border: visibility === "connections_only" ? "2px solid var(--primary-accent)" : "1px solid var(--line)",
                        background: visibility === "connections_only" ? "rgba(83, 101, 245, 0.12)" : "var(--card)",
                        color: visibility === "connections_only" ? "var(--primary-accent)" : "var(--text-secondary)",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "4px",
                      }}
                    >
                      <Lock size={11} /> Connections
                    </button>
                    <button
                      type="button"
                      onClick={() => setVisibility("public")}
                      style={{
                        flex: 1,
                        padding: "8px 6px",
                        borderRadius: "8px",
                        border: visibility === "public" ? "2px solid #10b981" : "1px solid var(--line)",
                        background: visibility === "public" ? "rgba(16, 185, 129, 0.12)" : "var(--card)",
                        color: visibility === "public" ? "#10b981" : "var(--text-secondary)",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "4px",
                      }}
                    >
                      <Globe size={11} /> Public
                    </button>
                  </div>
                  <span style={{ fontSize: "10px", color: "var(--secondary-text)", display: "block", marginTop: "4px" }}>
                    {visibility === "connections_only" ? "🔒 Only accepted connections can view" : "🌐 Anyone on ALIGN can view"}
                  </span>
                </div>
              </div>

              <div className="actions" style={{ justifyContent: "flex-end", marginTop: "16px" }}>
                <button
                  type="button"
                  className="button"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="button primary"
                  disabled={submitting || uploadingMedia}
                >
                  {submitting ? "Sharing..." : "Share carousel"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Interactive Instagram Post Modal */}
      <PostDetailModal
        post={selectedPost}
        onClose={() => setSelectedPost(null)}
        onLikeChange={(postId: number, liked: boolean, count: number) => {
          setPosts((prev) =>
            prev.map((p) =>
              p.id === postId ? { ...p, is_liked: liked, likes_count: count } : p
            )
          );
        }}
      />
    </AppShell>
  );
}
