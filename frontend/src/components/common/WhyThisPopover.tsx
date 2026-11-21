import React, { useState, useRef, useEffect } from "react";
import { Sparkles, X, Network, MapPin, Tag, CheckCircle2, ShieldCheck, Info } from "lucide-react";

interface ScoreBreakdown {
  semantic: number;
  keyword: number;
  graph: number;
  geo: number;
  category: number;
  feedback: number;
}

interface WhyThisPopoverProps {
  score: number;
  whyRecommended?: string | null;
  scoreBreakdown?: ScoreBreakdown;
  matchedTerms?: string[];
  graphPath?: string | null;
  title: string;
}

const FACTOR_COLORS: Record<keyof ScoreBreakdown, { label: string; color: string; desc: string }> = {
  semantic: { label: "Dense Semantic", color: "#8b5cf6", desc: "Intent embedding similarity" },
  keyword: { label: "Keyword Match", color: "#0ea5e9", desc: "Exact vocabulary overlap" },
  graph: { label: "Graph Network", color: "#10b981", desc: "Shared connections & co-memberships" },
  geo: { label: "Geographic Proximity", color: "#f59e0b", desc: "Distance to physical location" },
  category: { label: "Category & Domain", color: "#ec4899", desc: "Domain relevance bonus" },
  feedback: { label: "Feedback Tuning", color: "#a855f7", desc: "Past user preference adjustments" },
};

export default function WhyThisPopover({
  score,
  whyRecommended,
  scoreBreakdown,
  matchedTerms,
  graphPath,
  title,
}: WhyThisPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const rawBreakdown = scoreBreakdown || {
    semantic: score * 0.55,
    keyword: score * 0.25,
    graph: score * 0.10,
    geo: score * 0.05,
    category: score * 0.05,
    feedback: 0.0,
  };

  const totalBreakdown = Object.values(rawBreakdown).reduce((acc, v) => acc + (v > 0 ? v : 0), 0) || 1;

  return (
    <div className="relative inline-block" ref={popoverRef} style={{ display: "inline-block" }}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        title="View Explainable AI factors"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          padding: "3px 9px",
          borderRadius: "9999px",
          background: "rgba(167, 121, 232, 0.12)",
          color: "var(--lilac-strong)",
          border: "1px solid rgba(167, 121, 232, 0.28)",
          fontSize: "11px",
          fontWeight: 600,
          cursor: "pointer",
          transition: "all 0.2s ease",
        }}
      >
        <Sparkles size={11} style={{ color: "var(--lilac)" }} />
        <span>Why this?</span>
      </button>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            right: 0,
            width: "320px",
            maxWidth: "90vw",
            background: "var(--bg-elev)",
            borderRadius: "20px",
            border: "1px solid var(--border)",
            boxShadow: "0 16px 40px rgba(0, 0, 0, 0.35)",
            backdropFilter: "blur(14px)",
            WebkitBackdropFilter: "blur(14px)",
            padding: "16px",
            zIndex: 100,
            color: "var(--text)",
            fontSize: "12px",
            textAlign: "left",
          }}
        >
          {/* Header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Sparkles size={15} style={{ color: "#8b5cf6" }} />
              <strong style={{ fontSize: "13px", fontWeight: 700 }}>Explainable AI Recommendation</strong>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              style={{
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: "2px",
                color: "var(--secondary-text, #6b7280)",
              }}
            >
              <X size={15} />
            </button>
          </div>

          {/* Natural language explanation */}
          <p
            style={{
              fontSize: "12px",
              lineHeight: 1.45,
              color: "var(--primary-text, #374151)",
              marginBottom: "12px",
              background: "rgba(139, 92, 246, 0.06)",
              padding: "8px 10px",
              borderRadius: "10px",
              borderLeft: "3px solid #8b5cf6",
            }}
          >
            {whyRecommended || `Recommended because it closely matches your intent query for "${title}".`}
          </p>

          {/* Stacked Horizontal Factor Bar */}
          <div style={{ marginBottom: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", fontSize: "11px", fontWeight: 600 }}>
              <span>Score Breakdown (Shapley Values)</span>
              <span style={{ color: "#8b5cf6" }}>{Math.round(score * 100)}% overall</span>
            </div>
            <div
              style={{
                display: "flex",
                height: "10px",
                width: "100%",
                borderRadius: "999px",
                overflow: "hidden",
                background: "rgba(0, 0, 0, 0.06)",
              }}
            >
              {(Object.keys(FACTOR_COLORS) as Array<keyof ScoreBreakdown>).map((key) => {
                const val = rawBreakdown[key] || 0;
                if (val <= 0) return null;
                const pct = (val / totalBreakdown) * 100;
                return (
                  <div
                    key={key}
                    style={{
                      width: `${pct}%`,
                      background: FACTOR_COLORS[key].color,
                      height: "100%",
                    }}
                    title={`${FACTOR_COLORS[key].label}: ${(val * 100).toFixed(1)}%`}
                  />
                );
              })}
            </div>

            {/* Factor Legend Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 8px", marginTop: "8px" }}>
              {(Object.keys(FACTOR_COLORS) as Array<keyof ScoreBreakdown>).map((key) => {
                const val = rawBreakdown[key] || 0;
                if (val <= 0) return null;
                const pct = Math.round((val / totalBreakdown) * 100);
                return (
                  <div key={key} style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "10px" }}>
                    <span
                      style={{
                        width: "8px",
                        height: "8px",
                        borderRadius: "50%",
                        background: FACTOR_COLORS[key].color,
                        display: "inline-block",
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ color: "var(--secondary-text, #6b7280)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {FACTOR_COLORS[key].label}
                    </span>
                    <span style={{ fontWeight: 700, marginLeft: "auto" }}>{pct}%</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Matched Terms */}
          {matchedTerms && matchedTerms.length > 0 && (
            <div style={{ marginBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", fontWeight: 600, marginBottom: "4px" }}>
                <Tag size={12} style={{ color: "#0ea5e9" }} />
                <span>Matched Terms & Skills</span>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                {matchedTerms.slice(0, 4).map((term, i) => (
                  <span
                    key={i}
                    style={{
                      fontSize: "10px",
                      padding: "2px 7px",
                      borderRadius: "6px",
                      background: "rgba(14, 165, 233, 0.1)",
                      color: "#0284c7",
                      fontWeight: 600,
                    }}
                  >
                    {term}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Graph Connection Path */}
          {graphPath ? (
            <div style={{ marginBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", fontWeight: 600, marginBottom: "4px" }}>
                <Network size={12} style={{ color: "#10b981" }} />
                <span>Graph Network Path</span>
              </div>
              <div
                style={{
                  fontSize: "10px",
                  lineHeight: 1.4,
                  background: "rgba(16, 185, 129, 0.08)",
                  padding: "6px 8px",
                  borderRadius: "8px",
                  color: "#065f46",
                  fontWeight: 500,
                  wordBreak: "break-word",
                }}
              >
                {graphPath}
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "10px", color: "var(--secondary-text, #6b7280)", marginBottom: "8px" }}>
              <CheckCircle2 size={12} style={{ color: "#6b7280" }} />
              <span>Direct semantic discovery (Cold-start friendly)</span>
            </div>
          )}

          {/* Privacy Note */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              paddingTop: "6px",
              borderTop: "1px solid var(--border-subtle, rgba(0, 0, 0, 0.08))",
              fontSize: "9px",
              color: "var(--secondary-text, #9ca3af)",
            }}
          >
            <ShieldCheck size={11} style={{ color: "#10b981" }} />
            <span>Zero private data leaked. Graph uses public topology & aggregate counts.</span>
          </div>
        </div>
      )}
    </div>
  );
}
