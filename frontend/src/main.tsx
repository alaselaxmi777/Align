import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { ThemeProvider } from "./lib/theme";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { showToast } from "./components/common/ToastContext";
import { formatApiError } from "./lib/errorUtils";
import "./index.css";
import "./styles.css";

// Global capture for unhandled async promise rejections
window.addEventListener("unhandledrejection", (event) => {
  console.error("Unhandled Promise Rejection:", event.reason);
  const msg = formatApiError(event.reason);
  // Avoid spamming if user navigated away or aborted
  if (msg && !msg.includes("aborted")) {
    showToast("error", msg);
  }
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
