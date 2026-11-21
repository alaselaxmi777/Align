import { useState, useRef, useEffect, ChangeEvent, FormEvent } from "react";
import { X, Upload, Video, AlertCircle, CheckCircle, Lock, Globe, Loader2, RotateCw } from "lucide-react";
import { api } from "../lib/api";

interface CreateReelModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newReel: any) => void;
}

const CATEGORIES = [
  "Fort Trekking",
  "AgriTech",
  "Marathi Literature",
  "Kushti & Kabaddi",
  "Art & Culture",
  "Technology",
  "Travel",
  "Social",
];

export default function CreateReelModal({ isOpen, onClose, onSuccess }: CreateReelModalProps) {
  if (!isOpen) return null;

  const [file, setFile] = useState<File | null>(null);
  const [videoPreview, setVideoPreview] = useState<string | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [durationError, setDurationError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("Technology");
  const [caption, setCaption] = useState("");
  const [tags, setTags] = useState("");
  const [visibility, setVisibility] = useState<"public" | "connections_only">("public");

  const [submitting, setSubmitting] = useState(false);
  const [uploadState, setUploadState] = useState<"idle" | "uploading" | "transcoding" | "saving" | "error" | "success">("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, submitting]);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleCancelUpload = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setSubmitting(false);
    setUploadProgress(0);
    setStatusMessage(null);
    setUploadState("idle");
    setErrorMessage("Upload was cancelled.");
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    if (selected.size > 50 * 1024 * 1024) {
      setErrorMessage("File exceeds the 50MB limit. Please select a smaller video.");
      setFile(null);
      setVideoPreview(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setDurationError(null);
    setErrorMessage(null);
    setUploadState("idle");
    setFile(selected);

    const objectUrl = URL.createObjectURL(selected);
    setVideoPreview(objectUrl);

    // Client-side duration probe
    const tempVideo = document.createElement("video");
    tempVideo.preload = "metadata";
    tempVideo.src = objectUrl;
    tempVideo.onloadedmetadata = () => {
      const dur = tempVideo.duration;
      setDuration(dur);
      if (dur > 90.0) {
        setDurationError(`Video duration is ${Math.round(dur)}s. Reels cannot exceed 90 seconds.`);
      }
    };
    tempVideo.onerror = () => {
      setDurationError("Could not read video metadata. Please select a valid MP4/WebM video.");
    };
  };

  const handleSubmit = async (e?: FormEvent) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!file) {
      setErrorMessage("Please select a video file.");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setErrorMessage("Video file size exceeds 50MB limit.");
      return;
    }
    if (duration && duration > 90.0) {
      setErrorMessage("Reels cannot exceed 90 seconds.");
      return;
    }
    if (!title.trim()) {
      setErrorMessage("Please enter a title.");
      return;
    }

    setSubmitting(true);
    setUploadProgress(0);
    setErrorMessage(null);
    setUploadState("uploading");
    setStatusMessage("Uploading video...");

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      // 1. Upload and transcode with real progress tracking & cancellation support
      const transcodeResult = await api.uploadVideoVariant(
        file,
        true,
        (pct) => {
          setUploadProgress(pct);
          if (pct === 100) {
            setUploadState("transcoding");
            setStatusMessage("Transcoding video to H.264/AAC with +faststart...");
          }
        },
        controller.signal
      );

      setUploadState("saving");
      setStatusMessage("Saving reel details and computing multilingual semantic embedding...");

      // 2. Parse tags
      const tagList = tags
        .split(/[,\s#]+/)
        .map((t) => t.trim())
        .filter(Boolean);

      // 3. Create reel in DB
      const newReel = await api.createReel({
        title: title.trim(),
        category,
        video_url: transcodeResult.video_url,
        thumbnail_url: transcodeResult.thumbnail_url,
        duration_seconds: transcodeResult.duration_seconds,
        visibility,
        caption: caption.trim() || undefined,
        tags: tagList,
      });

      setUploadState("success");
      setStatusMessage("Reel published successfully!");
      setTimeout(() => {
        onSuccess(newReel);
        onClose();
      }, 700);
    } catch (err: any) {
      console.error("Reel creation error:", err);
      setUploadState("error");
      setStatusMessage(null); // Clear status message so "Transcoding..." cannot persist
      setErrorMessage(err.message || "Failed to upload and create reel.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 90,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
        background: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(8px)",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Create Community Reel"
        style={{
          width: "100%",
          maxWidth: "600px",
          maxHeight: "90vh",
          overflowY: "auto",
          background: "var(--bg-card, #1e293b)",
          color: "var(--text-primary, #ffffff)",
          borderRadius: "18px",
          border: "1px solid var(--border-color, #334155)",
          boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
          padding: "24px",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <div>
            <h2 style={{ fontSize: "20px", fontWeight: "700", margin: 0 }}>Create Community Reel</h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary, #94a3b8)", margin: "4px 0 0" }}>
              Share high-energy vertical video clips (max 90s, H.264 MP4).
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-secondary, #94a3b8)",
              cursor: submitting ? "not-allowed" : "pointer",
              padding: "6px",
            }}
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {/* File Selector / Preview */}
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "13px", fontWeight: "600", marginBottom: "8px" }}>
              Reel Video (9:16 vertical recommended, max 90s)
            </label>
            <input
              type="file"
              ref={fileInputRef}
              accept="video/mp4,video/webm,video/quicktime"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />

            {!videoPreview ? (
              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: "2px dashed var(--border-color, #475569)",
                  borderRadius: "14px",
                  padding: "32px 16px",
                  textAlign: "center",
                  cursor: "pointer",
                  background: "rgba(255,255,255,0.02)",
                  transition: "border-color 0.2s",
                }}
              >
                <Video size={40} style={{ color: "var(--accent-color, #6366f1)", marginBottom: "8px" }} />
                <p style={{ fontWeight: "600", margin: "0 0 4px" }}>Click to select video</p>
                <p style={{ fontSize: "12px", color: "var(--text-secondary, #94a3b8)", margin: 0 }}>
                  Supports MP4, WebM, MOV up to 100 MB
                </p>
              </div>
            ) : (
              <div
                style={{
                  position: "relative",
                  borderRadius: "14px",
                  overflow: "hidden",
                  background: "#000",
                  textAlign: "center",
                  maxHeight: "260px",
                }}
              >
                <video
                  src={videoPreview}
                  controls
                  style={{ maxHeight: "260px", width: "auto", margin: "0 auto" }}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    position: "absolute",
                    top: "10px",
                    right: "10px",
                    background: "rgba(0,0,0,0.7)",
                    color: "#fff",
                    border: "none",
                    borderRadius: "8px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    cursor: "pointer",
                  }}
                >
                  Change Video
                </button>
              </div>
            )}

            {duration !== null && (
              <div style={{ marginTop: "6px", fontSize: "12px", color: "var(--text-secondary, #94a3b8)" }}>
                Detected Duration: <strong>{duration.toFixed(1)}s</strong> / 90s
              </div>
            )}

            {durationError && (
              <div
                style={{
                  marginTop: "8px",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  color: "#ef4444",
                  fontSize: "13px",
                }}
              >
                <AlertCircle size={16} />
                <span>{durationError}</span>
              </div>
            )}
          </div>

          {/* Title */}
          <div style={{ marginBottom: "14px" }}>
            <label style={{ display: "block", fontSize: "13px", fontWeight: "600", marginBottom: "6px" }}>
              Title *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Exploring Rajgad Fort in heavy monsoon mist"
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: "10px",
                border: "1px solid var(--border-color, #475569)",
                background: "var(--bg-input, #0f172a)",
                color: "#fff",
                fontSize: "14px",
              }}
            />
          </div>

          {/* Category & Visibility Row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
            <div>
              <label style={{ display: "block", fontSize: "13px", fontWeight: "600", marginBottom: "6px" }}>
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "10px",
                  border: "1px solid var(--border-color, #475569)",
                  background: "var(--bg-input, #0f172a)",
                  color: "#fff",
                  fontSize: "14px",
                }}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "13px", fontWeight: "600", marginBottom: "6px" }}>
                Visibility
              </label>
              <select
                value={visibility}
                onChange={(e) => setVisibility(e.target.value as any)}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "10px",
                  border: "1px solid var(--border-color, #475569)",
                  background: "var(--bg-input, #0f172a)",
                  color: "#fff",
                  fontSize: "14px",
                }}
              >
                <option value="public">🌐 Public (All Users)</option>
                <option value="connections_only">🔒 Connections Only</option>
              </select>
            </div>
          </div>

          {/* Caption */}
          <div style={{ marginBottom: "14px" }}>
            <label style={{ display: "block", fontSize: "13px", fontWeight: "600", marginBottom: "6px" }}>
              Caption
            </label>
            <textarea
              rows={3}
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="What makes this clip special? Add context or backstory..."
              maxLength={2200}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: "10px",
                border: "1px solid var(--border-color, #475569)",
                background: "var(--bg-input, #0f172a)",
                color: "#fff",
                fontSize: "14px",
                resize: "vertical",
              }}
            />
          </div>

          {/* Hashtags */}
          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", fontSize: "13px", fontWeight: "600", marginBottom: "6px" }}>
              Tags (comma or space separated)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="Sahyadri, Trek, Monsoon, Maharashtra"
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: "10px",
                border: "1px solid var(--border-color, #475569)",
                background: "var(--bg-input, #0f172a)",
                color: "#fff",
                fontSize: "14px",
              }}
            />
          </div>

          {/* Status / Error feedback */}
          {submitting && (
            <div
              style={{
                marginBottom: "16px",
                padding: "14px",
                background: "rgba(99, 102, 241, 0.12)",
                borderRadius: "12px",
                border: "1px solid rgba(99, 102, 241, 0.25)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "8px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Loader2 size={15} className="animate-spin" style={{ color: "#818cf8" }} />
                  <span style={{ fontSize: "13px", fontWeight: "600", color: "#c7d2fe" }}>
                    {statusMessage || "Uploading..."}
                  </span>
                </div>
                <span style={{ fontSize: "13px", fontWeight: "700", color: "#a5b4fc" }}>
                  {uploadProgress}%
                </span>
              </div>
              <div
                style={{
                  width: "100%",
                  height: "8px",
                  background: "rgba(255, 255, 255, 0.1)",
                  borderRadius: "4px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${uploadProgress}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, #6366f1, #a855f7)",
                    transition: "width 0.2s ease",
                  }}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={handleCancelUpload}
                  style={{
                    background: "transparent",
                    border: "1px solid #ef4444",
                    color: "#f87171",
                    borderRadius: "6px",
                    padding: "4px 10px",
                    fontSize: "12px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  Cancel Upload
                </button>
              </div>
            </div>
          )}

          {!submitting && !errorMessage && statusMessage && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "10px",
                background: "rgba(99, 102, 241, 0.15)",
                color: "#a5b4fc",
                fontSize: "13px",
                marginBottom: "14px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <CheckCircle size={16} />
              <span>{statusMessage}</span>
            </div>
          )}

          {!submitting && errorMessage && (
            <div
              style={{
                padding: "12px 14px",
                borderRadius: "12px",
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                color: "#fca5a5",
                fontSize: "13px",
                marginBottom: "14px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <AlertCircle size={18} style={{ flexShrink: 0, color: "#f87171" }} />
                <span style={{ fontWeight: 500 }}>{errorMessage}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button
                  type="button"
                  onClick={() => handleSubmit()}
                  disabled={submitting || !file || !!durationError}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "#ef4444",
                    color: "#fff",
                    border: "none",
                    borderRadius: "6px",
                    padding: "6px 14px",
                    fontSize: "12px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  <RotateCw size={13} />
                  Retry Upload
                </button>
              </div>
            </div>
          )}

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              style={{
                padding: "10px 18px",
                borderRadius: "10px",
                border: "1px solid var(--border-color, #475569)",
                background: "transparent",
                color: "var(--text-secondary, #94a3b8)",
                fontSize: "14px",
                fontWeight: "600",
                cursor: submitting ? "not-allowed" : "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !file || !!durationError}
              style={{
                padding: "10px 22px",
                borderRadius: "10px",
                border: "none",
                background: "var(--accent-color, #6366f1)",
                color: "#fff",
                fontSize: "14px",
                fontWeight: "600",
                cursor: submitting || !file || !!durationError ? "not-allowed" : "pointer",
                opacity: submitting || !file || !!durationError ? 0.6 : 1,
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              {submitting && <Loader2 size={16} className="animate-spin" />}
              Publish Reel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
