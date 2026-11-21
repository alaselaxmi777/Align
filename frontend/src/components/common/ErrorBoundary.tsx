import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[ALIGN Uncaught Client Exception]", error, errorInfo);

    // Optional Sentry or client telemetry dispatch
    if (typeof window !== "undefined" && (window as any).Sentry) {
      try {
        (window as any).Sentry.captureException(error, { extra: errorInfo });
      } catch (sentryErr) {
        console.warn("Failed to dispatch to Sentry:", sentryErr);
      }
    }
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            background: "var(--bg, #0B0F14)",
            color: "var(--text, #F8FAFC)",
            fontFamily: "var(--font-body, system-ui, sans-serif)",
          }}
        >
          <div
            style={{
              maxWidth: "480px",
              width: "100%",
              padding: "32px",
              borderRadius: "20px",
              background: "var(--bg-card, #141B22)",
              border: "1px solid var(--border-color, rgba(255, 255, 255, 0.1))",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "50%",
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                display: "grid",
                placeItems: "center",
                margin: "0 auto 16px auto",
                color: "#EF4444",
              }}
            >
              <AlertTriangle size={28} />
            </div>

            <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "8px" }}>
              Something went wrong
            </h2>
            <p
              style={{
                fontSize: "14px",
                color: "var(--text-secondary, #94A3B8)",
                lineHeight: "1.6",
                marginBottom: "24px",
              }}
            >
              An unexpected error occurred while loading this view. You can reload the page or return
              to the home stream.
            </p>

            <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
              <button
                type="button"
                onClick={this.handleReset}
                style={{
                  padding: "10px 18px",
                  borderRadius: "10px",
                  border: "none",
                  background: "var(--primary-accent, #6366F1)",
                  color: "#FFFFFF",
                  fontSize: "13px",
                  fontWeight: "600",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <RefreshCw size={15} /> Reload App
              </button>
              <a
                href="/feed"
                style={{
                  padding: "10px 18px",
                  borderRadius: "10px",
                  border: "1px solid var(--border-color, #334155)",
                  background: "transparent",
                  color: "var(--text, #FFFFFF)",
                  fontSize: "13px",
                  fontWeight: "600",
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <Home size={15} /> Return to Feed
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
