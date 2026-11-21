import { Play } from "lucide-react";
import { SafeImage } from "../common/SafeImage";

export interface ReelItem {
  id: string | number;
  title: string;
  creator: string;
  creatorAvatar?: string;
  views: string;
  likes: number;
  category: string;
  imageUrl: string;
  videoUrl?: string;
  audioTrack?: string;
  description?: string;
}

interface ReelCardProps {
  reel: ReelItem;
  onOpen: (reel: ReelItem) => void;
}

export default function ReelCard({ reel, onOpen }: ReelCardProps) {
  return (
    <button
      type="button"
      className="reel-tile group"
      onClick={() => onOpen(reel)}
      aria-label={`Watch reel: ${reel.title} by ${reel.creator}`}
    >
      <SafeImage
        src={reel.imageUrl}
        alt={reel.title}
        loading="lazy"
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
      <div
        className="reel-play group-hover:scale-110 transition-transform"
        style={{
          width: "44px",
          height: "44px",
          borderRadius: "50%",
          background: "rgba(0, 0, 0, 0.5)",
          backdropFilter: "blur(4px)",
          display: "grid",
          placeItems: "center",
          marginLeft: "-22px",
          marginTop: "-22px",
        }}
      >
        <Play size={20} fill="#FFFFFF" color="#FFFFFF" style={{ marginLeft: "2px" }} />
      </div>

      <div className="reel-overlay">
        <strong style={{ display: "block", fontSize: "14px", fontWeight: "700", marginBottom: "2px" }}>
          {reel.title}
        </strong>
        <span style={{ fontSize: "12px", opacity: 0.9 }}>
          ◉ {reel.views} · {reel.creator}
        </span>
      </div>
    </button>
  );
}
