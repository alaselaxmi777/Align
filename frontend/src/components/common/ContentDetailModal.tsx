import React, { useEffect } from "react";
import { X } from "lucide-react";
import { SafeImage } from "./SafeImage";

export interface DetailModalData {
  kind: string;
  title: string;
  description: string;
  imageUrl?: string;
  actionText?: string;
  onAction?: () => void;
  actionActive?: boolean;
}

interface ContentDetailModalProps {
  data: DetailModalData | null;
  onClose: () => void;
}

export default function ContentDetailModal({ data, onClose }: ContentDetailModalProps) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (data) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [data, onClose]);

  if (!data) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 60,
        background: "rgba(10, 5, 18, 0.75)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="modal-box"
        style={{
          position: "relative",
          background: "var(--bg-elev)",
          color: "var(--text)",
          borderRadius: "28px",
          maxWidth: "760px",
          width: "100%",
          maxHeight: "90vh",
          overflow: "auto",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          border: "1px solid var(--border)",
          boxShadow: "0 24px 60px rgba(0,0,0,0.4)",
        }}
      >
        <button
          type="button"
          onClick={onClose}
          className="icon-btn modal-close"
          aria-label="Close details"
          style={{
            position: "absolute",
            right: "12px",
            top: "12px",
            zIndex: 10,
          }}
        >
          <X size={18} />
        </button>

        <SafeImage
          src={data.imageUrl || "https://images.pexels.com/photos/3184292/pexels-photo-3184292.jpeg?auto=compress&cs=tinysrgb&w=800"}
          alt={data.title}
          style={{ width: "100%", height: "100%", minHeight: "340px", objectFit: "cover" }}
        />

        <div style={{ padding: "35px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <p className="eyebrow">{data.kind}</p>
            <h2 style={{ fontSize: "24px", fontWeight: "800", margin: "0 0 12px 0", color: "var(--text)" }}>
              {data.title}
            </h2>
            <p className="lead" style={{ margin: "0 0 20px 0" }}>
              {data.description}
            </p>
          </div>

          <div className="actions">
            {data.actionText && (
              <button
                type="button"
                className={`button ${data.actionActive ? "selected" : "primary"}`}
                onClick={data.onAction}
              >
                {data.actionText}
              </button>
            )}
            <button type="button" className="button" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
