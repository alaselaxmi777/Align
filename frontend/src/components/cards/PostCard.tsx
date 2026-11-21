import { Heart, MessageCircle, Layers, Lock, Globe, MapPin, Pin } from "lucide-react";
import { PostItem } from "../../lib/api";
import { SafeImage } from "../common/SafeImage";

interface PostCardProps {
  post: PostItem;
  onOpen: (post: PostItem) => void;
}

const DEFAULT_POST_IMAGE = "https://images.pexels.com/photos/3184418/pexels-photo-3184418.jpeg?auto=compress&cs=tinysrgb&w=800";

export default function PostCard({ post, onOpen }: PostCardProps) {
  const displayImage =
    (post.media && post.media.length > 0 ? post.media[0].feed_url : post.image_url) ||
    DEFAULT_POST_IMAGE;

  const isCarousel = Boolean(post.media && post.media.length > 1);

  return (
    <button
      type="button"
      className="photo-tile group"
      onClick={() => onOpen(post)}
      aria-label={`View post by ${post.author?.name || "member"}`}
      style={{
        position: "relative",
        width: "100%",
        aspectRatio: "1 / 1",
        overflow: "hidden",
        border: "none",
        padding: 0,
        borderRadius: "8px",
        background: "var(--sub)",
        cursor: "pointer",
        transition: "transform 0.15s ease",
      }}
    >
      <SafeImage
        src={displayImage}
        fallbackSrc={DEFAULT_POST_IMAGE}
        alt={post.media?.[0]?.alt_text || post.content.slice(0, 40)}
        loading="lazy"
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />

      {/* Multi-image carousel badge */}
      {isCarousel && (
        <span
          style={{
            position: "absolute",
            top: "8px",
            right: "8px",
            background: "rgba(0, 0, 0, 0.65)",
            color: "#FFFFFF",
            padding: "3px 6px",
            borderRadius: "6px",
            fontSize: "11px",
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            gap: "4px",
            backdropFilter: "blur(4px)",
            zIndex: 2,
          }}
        >
          <Layers size={12} />
          {post.media!.length}
        </span>
      )}

      {/* Pinned indicator */}
      {post.is_pinned && (
        <span
          style={{
            position: "absolute",
            top: "8px",
            left: post.visibility === "connections_only" ? "95px" : "8px",
            background: "rgba(99, 102, 241, 0.85)",
            color: "#FFFFFF",
            padding: "3px 6px",
            borderRadius: "6px",
            fontSize: "10px",
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            gap: "3px",
            backdropFilter: "blur(4px)",
            zIndex: 2,
          }}
        >
          <Pin size={10} style={{ transform: "rotate(45deg)" }} />
          Pinned
        </span>
      )}

      {/* Visibility indicator */}
      {post.visibility === "connections_only" && (
        <span
          style={{
            position: "absolute",
            top: "8px",
            left: "8px",
            background: "rgba(0, 0, 0, 0.65)",
            color: "#FFFFFF",
            padding: "3px 6px",
            borderRadius: "6px",
            fontSize: "10px",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: "3px",
            backdropFilter: "blur(4px)",
            zIndex: 2,
          }}
        >
          <Lock size={10} />
          Connections
        </span>
      )}

      {/* Location badge if present */}
      {post.location_area && (
        <span
          style={{
            position: "absolute",
            bottom: "8px",
            left: "8px",
            background: "rgba(0, 0, 0, 0.65)",
            color: "#FFFFFF",
            padding: "2px 6px",
            borderRadius: "4px",
            fontSize: "10px",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: "3px",
            backdropFilter: "blur(4px)",
            zIndex: 2,
            maxWidth: "70%",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          <MapPin size={10} />
          {post.location_area}
        </span>
      )}

      {/* Feed Rank / Match pill */}
      {post.score != null && post.score > 0 && (
        <span
          style={{
            position: "absolute",
            bottom: "8px",
            right: "8px",
            background: "rgba(99, 102, 241, 0.85)",
            color: "#FFFFFF",
            padding: "2px 6px",
            borderRadius: "4px",
            fontSize: "10px",
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            gap: "3px",
            backdropFilter: "blur(4px)",
            zIndex: 2,
          }}
          title={post.why_recommended || `Match score: ${(post.score * 100).toFixed(0)}%`}
        >
          {Math.round(post.score * 100)}%
        </span>
      )}

      {/* Hover stats overlay */}
      <div
        className="opacity-0 group-hover:opacity-100 transition-opacity"
        style={{
          position: "absolute",
          inset: 0,
          background: "rgba(0, 0, 0, 0.45)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "18px",
          color: "#FFFFFF",
          fontWeight: 700,
          fontSize: "15px",
          zIndex: 3,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Heart size={18} fill="#FFFFFF" />
          <span>{post.likes_count ?? 0}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <MessageCircle size={18} fill="#FFFFFF" />
          <span>{post.comments_count ?? 0}</span>
        </div>
      </div>
    </button>
  );
}
