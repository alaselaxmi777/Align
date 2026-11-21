import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { CheckCircle, AlertCircle, Info, AlertTriangle, X } from "lucide-react";

export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastContextValue {
  toast: {
    success: (message: string, duration?: number) => void;
    error: (message: string, duration?: number) => void;
    info: (message: string, duration?: number) => void;
    warning: (message: string, duration?: number) => void;
  };
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

/**
 * Global helper to trigger toasts from non-React contexts (e.g. API client, window error handlers).
 */
export function showToast(type: ToastType, message: string, duration = 4000): void {
  window.dispatchEvent(
    new CustomEvent("align-toast", {
      detail: { type, message, duration },
    })
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, message: string, duration: number = 4000) => {
      const id = `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      const newToast: ToastItem = { id, type, message, duration };

      setToasts((prev) => [...prev.slice(-4), newToast]); // Keep maximum 5 toasts

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  // Listen for global custom events
  useEffect(() => {
    const handleGlobalToast = (e: Event) => {
      const customEvent = e as CustomEvent<{ type: ToastType; message: string; duration?: number }>;
      if (customEvent.detail) {
        addToast(customEvent.detail.type, customEvent.detail.message, customEvent.detail.duration);
      }
    };

    window.addEventListener("align-toast", handleGlobalToast);
    return () => window.removeEventListener("align-toast", handleGlobalToast);
  }, [addToast]);

  const toastMethods = {
    success: (msg: string, duration?: number) => addToast("success", msg, duration),
    error: (msg: string, duration?: number) => addToast("error", msg, duration),
    info: (msg: string, duration?: number) => addToast("info", msg, duration),
    warning: (msg: string, duration?: number) => addToast("warning", msg, duration),
  };

  return (
    <ToastContext.Provider value={{ toast: toastMethods, removeToast }}>
      {children}
      {/* Toast Notification Container */}
      <div
        role="region"
        aria-live="polite"
        aria-label="Notifications"
        style={{
          position: "fixed",
          top: "20px",
          right: "20px",
          zIndex: 99999,
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          maxWidth: "420px",
          width: "calc(100vw - 40px)",
          pointerEvents: "none",
        }}
      >
        {toasts.map((t) => (
          <ToastCard key={t.id} item={t} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastCard({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  const getStyle = () => {
    switch (item.type) {
      case "success":
        return {
          bg: "#064e3b",
          border: "#059669",
          text: "#ecfdf5",
          icon: <CheckCircle size={18} color="#34d399" style={{ flexShrink: 0 }} />,
        };
      case "error":
        return {
          bg: "#450a0a",
          border: "#dc2626",
          text: "#fef2f2",
          icon: <AlertCircle size={18} color="#f87171" style={{ flexShrink: 0 }} />,
        };
      case "warning":
        return {
          bg: "#451a03",
          border: "#d97706",
          text: "#fffbeb",
          icon: <AlertTriangle size={18} color="#fbbf24" style={{ flexShrink: 0 }} />,
        };
      case "info":
      default:
        return {
          bg: "#1e1b4b",
          border: "#6366f1",
          text: "#eef2ff",
          icon: <Info size={18} color="#818cf8" style={{ flexShrink: 0 }} />,
        };
    }
  };

  const styleConfig = getStyle();

  return (
    <div
      role="alert"
      style={{
        pointerEvents: "auto",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: "12px",
        background: styleConfig.bg,
        border: `1px solid ${styleConfig.border}`,
        color: styleConfig.text,
        padding: "12px 16px",
        borderRadius: "12px",
        boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4)",
        fontSize: "13px",
        lineHeight: 1.45,
        animation: "slideInRight 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: "10px", flex: 1 }}>
        <div style={{ marginTop: "1px" }}>{styleConfig.icon}</div>
        <div style={{ wordBreak: "break-word", fontWeight: 500 }}>{item.message}</div>
      </div>
      <button
        onClick={onClose}
        aria-label="Close notification"
        style={{
          background: "transparent",
          border: "none",
          color: styleConfig.text,
          opacity: 0.7,
          cursor: "pointer",
          padding: "2px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <X size={15} />
      </button>
    </div>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    // Graceful fallback if invoked outside ToastProvider
    return {
      success: (msg: string) => showToast("success", msg),
      error: (msg: string) => showToast("error", msg),
      info: (msg: string) => showToast("info", msg),
      warning: (msg: string) => showToast("warning", msg),
    };
  }
  return context.toast;
}
