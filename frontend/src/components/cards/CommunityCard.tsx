import { useState } from "react";
import { Link } from "react-router-dom";
import { Community, api } from "../../lib/api";
import WhyThisPopover from "../common/WhyThisPopover";
import { SafeImage } from "../common/SafeImage";

interface CommunityCardProps {
  community: Community;
  onJoinToggle?: (id: number, joined: boolean) => void;
  onOpenDetail?: (community: Community) => void;
}

const DEFAULT_COMMUNITY_IMAGE = "https://images.pexels.com/photos/3184292/pexels-photo-3184292.jpeg?auto=compress&cs=tinysrgb&w=800";

export default function CommunityCard({
  community,
  onJoinToggle,
  onOpenDetail,
}: CommunityCardProps) {
  const [joined, setJoined] = useState(Boolean(community.is_member));
  const [loading, setLoading] = useState(false);
  const loggedIn = Boolean(localStorage.getItem("align_token"));

  async function handleToggleJoin() {
    if (!loggedIn) {
      window.location.href = "/login";
      return;
    }
    setLoading(true);
    try {
      if (joined) {
        await api.leaveCommunity(community.id);
        setJoined(false);
        onJoinToggle?.(community.id, false);
      } else {
        await api.joinCommunity(community.id);
        setJoined(true);
        onJoinToggle?.(community.id, true);
      }
    } catch (err) {
      console.error("Failed to toggle join:", err);
    } finally {
      setLoading(false);
    }
  }

  const count = community.member_count ?? 0;
  const memberCountText = `${count} ${count === 1 ? "member" : "members"}`;

  return (
    <article className="canva-card" data-content-key={String(community.id)}>
      <SafeImage
        src={community.image_url}
        fallbackSrc={DEFAULT_COMMUNITY_IMAGE}
        alt={community.name}
        className="card-image"
        loading="lazy"
      />
      <div className="card-body">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
          <span className="tag">
            {community.category || "Community"} · {memberCountText}
          </span>
          {community.score !== undefined && community.score !== null && (
            <WhyThisPopover
              score={community.score}
              whyRecommended={community.why_recommended}
              scoreBreakdown={community.score_breakdown || undefined}
              matchedTerms={community.matched_terms || undefined}
              graphPath={community.graph_path}
              title={community.name}
            />
          )}
        </div>
        <h3>{community.name}</h3>
        <p>{community.description || "A welcoming circle for curious minds."}</p>
        <div className="card-foot">
          <Link
            to={`/communities/${community.id}`}
            className="button"
            onClick={() => onOpenDetail?.(community)}
          >
            View community
          </Link>
          <button
            type="button"
            className={`button toggle-action ${joined ? "selected" : ""}`}
            onClick={handleToggleJoin}
            disabled={loading}
          >
            {loading ? "..." : joined ? "Joined" : "Join"}
          </button>
        </div>
      </div>
    </article>
  );
}
