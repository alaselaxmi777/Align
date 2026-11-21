import { useEffect, useState } from "react";
import { X, Send, User as UserIcon, CheckCircle, Search, AlertCircle, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { SafeAvatar } from "./common/SafeImage";

interface ShareToDmModalProps {
  itemType: "post" | "reel";
  itemId: number;
  itemTitle?: string;
  isOpen: boolean;
  onClose: () => void;
}

interface ConnectionUser {
  id: number;
  name: string;
  avatar_url?: string | null;
}

export default function ShareToDmModal({
  itemType,
  itemId,
  itemTitle,
  isOpen,
  onClose,
}: ShareToDmModalProps) {
  if (!isOpen) return null;

  const [connections, setConnections] = useState<ConnectionUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.myConnections("accepted")
      .then((data) => {
        if (data && Array.isArray(data)) {
          const list = data.map((c) => ({
            id: c.partner_id,
            name: c.partner_name,
            avatar_url: c.partner_avatar || null,
          }));
          setConnections(list);
          if (list.length > 0) setSelectedUserId(list[0].id);
        }
      })
      .catch((err: unknown) => {
        console.error("Failed to load connections:", err);
        setError("Unable to load connections.");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, submitting]);

  const handleSend = async () => {
    if (!selectedUserId) {
      setError("Please select a connection to send to.");
      return;
    }
    setSubmitting(true);
    setError(null);

    try {
      if (itemType === "post") {
        await api.sharePostToDM(itemId, selectedUserId, note.trim() || undefined);
      } else {
        await api.shareReelToDM(itemId, selectedUserId, note.trim() || undefined);
      }
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Failed to share item in message.");
    } finally {
      setSubmitting(false);
    }
  };

  const filtered = connections.filter((c) =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 95,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
        background: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(6px)",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Share via Direct Message"
        style={{
          width: "100%",
          maxWidth: "460px",
          background: "var(--bg-card, #1e293b)",
          borderRadius: "16px",
          border: "1px solid var(--border-color, #334155)",
          color: "#fff",
          padding: "20px",
          boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: "700", margin: 0 }}>
              Send in Direct Message
            </h3>
            {itemTitle && (
              <p style={{ fontSize: "12px", color: "var(--text-secondary, #94a3b8)", margin: "2px 0 0" }}>
                "{itemTitle.slice(0, 45)}..."
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer" }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Search connections */}
        <div style={{ position: "relative", marginBottom: "12px" }}>
          <Search size={14} style={{ position: "absolute", left: "12px", top: "11px", color: "#64748b" }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search connections..."
            style={{
              width: "100%",
              padding: "8px 12px 8px 34px",
              borderRadius: "10px",
              border: "1px solid var(--border-color, #334155)",
              background: "var(--bg-input, #0f172a)",
              color: "#fff",
              fontSize: "13px",
            }}
          />
        </div>

        {/* Connections List */}
        <div
          style={{
            maxHeight: "180px",
            overflowY: "auto",
            borderRadius: "10px",
            border: "1px solid var(--border-color, #334155)",
            background: "var(--bg-input, #0f172a)",
            marginBottom: "14px",
            padding: "4px",
          }}
        >
          {loading ? (
            <div style={{ textAlign: "center", padding: "20px", color: "#94a3b8", fontSize: "13px" }}>
              Loading connections...
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: "center", padding: "20px", color: "#94a3b8", fontSize: "13px" }}>
              No mutual connections found. Connect with members first to message them!
            </div>
          ) : (
            filtered.map((c) => {
              const isSelected = selectedUserId === c.id;
              return (
                <div
                  key={c.id}
                  onClick={() => setSelectedUserId(c.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "8px 10px",
                    borderRadius: "8px",
                    cursor: "pointer",
                    background: isSelected ? "rgba(99, 102, 241, 0.2)" : "transparent",
                    border: isSelected ? "1px solid var(--accent-color, #6366f1)" : "1px solid transparent",
                    transition: "background 0.15s ease",
                  }}
                >
                  <div
                    style={{
                      width: "30px",
                      height: "30px",
                      borderRadius: "50%",
                      background: "#334155",
                      overflow: "hidden",
                      flexShrink: 0,
                    }}
                  >
                    <SafeAvatar
                      src={c.avatar_url}
                      name={c.name}
                      size={32}
                    />
                  </div>
                  <span style={{ fontSize: "13px", fontWeight: "600", flex: 1 }}>{c.name}</span>
                </div>
              );
            })
          )}
        </div>

        {/* Note input */}
        <div style={{ marginBottom: "16px" }}>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Write a message... (optional)"
            maxLength={500}
            style={{
              width: "100%",
              padding: "9px 12px",
              borderRadius: "10px",
              border: "1px solid var(--border-color, #334155)",
              background: "var(--bg-input, #0f172a)",
              color: "#fff",
              fontSize: "13px",
            }}
          />
        </div>

        {/* Status / Error */}
        {success && (
          <div
            style={{
              padding: "8px 12px",
              borderRadius: "8px",
              background: "rgba(16, 185, 129, 0.2)",
              color: "#34d399",
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              marginBottom: "12px",
            }}
          >
            <CheckCircle size={15} /> Sent successfully!
          </div>
        )}

        {error && (
          <div
            style={{
              padding: "8px 12px",
              borderRadius: "8px",
              background: "rgba(239, 68, 68, 0.2)",
              color: "#f87171",
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              marginBottom: "12px",
            }}
          >
            <AlertCircle size={15} /> {error}
          </div>
        )}

        {/* Footer */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            style={{
              padding: "8px 14px",
              borderRadius: "8px",
              border: "1px solid var(--border-color, #334155)",
              background: "transparent",
              color: "#94a3b8",
              fontSize: "13px",
              fontWeight: "600",
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSend}
            disabled={submitting || !selectedUserId || success}
            style={{
              padding: "8px 18px",
              borderRadius: "8px",
              border: "none",
              background: "var(--accent-color, #6366f1)",
              color: "#fff",
              fontSize: "13px",
              fontWeight: "600",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              cursor: submitting || !selectedUserId || success ? "not-allowed" : "pointer",
              opacity: submitting || !selectedUserId || success ? 0.6 : 1,
            }}
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
